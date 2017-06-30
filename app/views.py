# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render, HttpResponse
from StringIO import StringIO
from lxml import etree
from tempfile import NamedTemporaryFile
from datetime import datetime
import PyPDF2
import logging
import time
import pdb

logger = logging.getLogger(__name__)

try:
    from PyPDF2 import PdfFileWriter, PdfFileReader
    from PyPDF2.generic import DictionaryObject, DecodedStreamObject,\
        NameObject, createStringObject, ArrayObject
except ImportError:
    logger.debug('Cannot import PyPDF2')


ZUGFERD_LEVEL = 'comfort'
ZUGFERD_FILENAME = 'ZUGFeRD-invoice.xml'
STATE = 'open'
INVOICE = {
    'state': 'open',
    'number': '123456',
    'comment': 'I like Illya because he is perfect guy',
    'type': 'our_invoice'
}
root = None

def _add_date(node_name, date_datetime, parent_node, ns):
    date_node = etree.SubElement(parent_node, ns['ram'] + node_name)
    date_node_str = etree.SubElement(
        date_node, ns['udt'] + 'DateTimeString', format='102')
    date_node_str.text = date_datetime

def _add_address_block(self, partner, parent_node, ns):
    address = etree.SubElement(
        parent_node, ns['ram'] + 'PostalTradeAddress')
    if partner.zip:
        address_zip = etree.SubElement(
            address, ns['ram'] + 'PostcodeCode')
        address_zip.text = partner.zip
    if partner.street:
        address_street = etree.SubElement(
            address, ns['ram'] + 'LineOne')
        address_street.text = partner.street
        if partner.street2:
            address_street2 = etree.SubElement(
                address, ns['ram'] + 'LineTwo')
            address_street2.text = partner.street2
    if partner.city:
        address_city = etree.SubElement(
            address, ns['ram'] + 'CityName')
        address_city.text = partner.city
    if partner.country_id:
        address_country = etree.SubElement(
            address, ns['ram'] + 'CountryID')
        address_country.text = partner.country_id.code

def _add_trade_agreement_block(trade_transaction, ns):
    trade_agreement = etree.SubElement(
        trade_transaction,
        ns['ram'] + 'ApplicableSupplyChainTradeAgreement')
    company = INVOICE['company_id']
    seller = etree.SubElement(
        trade_agreement, ns['ram'] + 'SellerTradeParty')
    seller_name = etree.SubElement(
        seller, ns['ram'] + 'Name')
    seller_name.text = company['name']
    # Only with EXTENDED profile
    # self._add_trade_contact_block(
    #    self.user_id.partner_id or company.partner_id, seller, ns)
    _add_address_block(company['partner_id'], seller, ns)
    if company.vat:
        seller_tax_reg = etree.SubElement(
            seller, ns['ram'] + 'SpecifiedTaxRegistration')
        seller_tax_reg_id = etree.SubElement(
            seller_tax_reg, ns['ram'] + 'ID', schemeID='VA')
        seller_tax_reg_id.text = company['vat']
    buyer = etree.SubElement(
        trade_agreement, ns['ram'] + 'BuyerTradeParty')
    if INVOICE['commercial_partner_id']['ref']:
        buyer_id = etree.SubElement(
            buyer, ns['ram'] + 'ID')
        buyer_id.text = INVOICE['commercial_partner_id']['ref']
    buyer_name = etree.SubElement(
        buyer, ns['ram'] + 'Name')
    buyer_name.text = INVOICE['commercial_partner_id']['name']
    # Only with EXTENDED profile
    # if self.commercial_partner_id != self.partner_id:
    #    self._add_trade_contact_block(
    #        self.partner_id, buyer, ns)
    _add_address_block(INVOICE['partner_id'], buyer, ns)
    if INVOICE['commercial_partner_id']['vat']:
        buyer_tax_reg = etree.SubElement(
            buyer, ns['ram'] + 'SpecifiedTaxRegistration')
        buyer_tax_reg_id = etree.SubElement(
            buyer_tax_reg, ns['ram'] + 'ID', schemeID='VA')
        buyer_tax_reg_id.text = INVOICE['commercial_partner_id']['vat']

    def _add_trade_delivery_block(trade_transaction, ns):
        trade_agreement = etree.SubElement(
            trade_transaction,
            ns['ram'] + 'ApplicableSupplyChainTradeDelivery')
        return trade_agreement

    def _add_trade_settlement_payment_means_block(request, trade_settlement, sign, ns):
        payment_means = etree.SubElement(
            trade_settlement,
            ns['ram'] + 'SpecifiedTradeSettlementPaymentMeans')
        payment_means_code = etree.SubElement(
            payment_means, ns['ram'] + 'TypeCode')
        payment_means_info = etree.SubElement(
            payment_means, ns['ram'] + 'Information')
        if INVOICE['payment_mode_id']:
            payment_means_code.text = INVOICE['payment_mode_id']['payment_method_id']['unece_code']
            payment_means_info.text = INVOICE['payment_mode_id']['note'] or INVOICE['payment_mode_id']['name']
        else:
            payment_means_code.text = '31'  # 31 = Wire transfer
            payment_means_info.text = 'Wire transfer'
            logger.warning(
                'Missing payment mode on invoice ID %d. '
                'Using 31 (wire transfer) as UNECE code as fallback '
                'for payment mean',
                INVOICE['id'])
        if payment_means_code.text in ['31', '42']:
            partner_bank = INVOICE['partner_bank_id']
            if (
                    not partner_bank and
                    INVOICE['partner_bank_id'] and
                    INVOICE['partner_bank_id']['bank_account_link'] == 'fixed' and
                    INVOICE['partner_bank_id']['fixed_journal_id']):
                partner_bank = INVOICE['partner_bank_id']['fixed_journal_id']['bank_account_id']
            if partner_bank and partner_bank.acc_type == 'iban':
                payment_means_bank_account = etree.SubElement(
                    payment_means,
                    ns['ram'] + 'PayeePartyCreditorFinancialAccount')
                iban = etree.SubElement(
                    payment_means_bank_account, ns['ram'] + 'IBANID')
                iban.text = partner_bank.sanitized_acc_number
                if partner_bank.bank_bic:
                    payment_means_bank = etree.SubElement(
                        payment_means,
                        ns['ram'] +
                        'PayeeSpecifiedCreditorFinancialInstitution')
                    payment_means_bic = etree.SubElement(
                        payment_means_bank, ns['ram'] + 'BICID')
                    payment_means_bic.text = partner_bank.bank_bic
                    if partner_bank.bank_name:
                        bank_name = etree.SubElement(
                            payment_means_bank, ns['ram'] + 'Name')
                        bank_name.text = partner_bank.bank_name

def _add_document_context_block(root, nsmap, ns):
    doc_ctx = etree.SubElement(
        root, ns['rsm'] + 'SpecifiedExchangedDocumentContext')
    if INVOICE['state'] not in ('open', 'paid'):
        test_indic = etree.SubElement(doc_ctx, ns['ram'] + 'TestIndicator')
        indic = etree.SubElement(test_indic, ns['udt'] + 'Indicator')
        indic.text = 'true'
    ctx_param = etree.SubElement(
        doc_ctx, ns['ram'] + 'GuidelineSpecifiedDocumentContextParameter')
    ctx_param_id = etree.SubElement(ctx_param, ns['ram'] + 'ID')
    ctx_param_id.text = '%s:%s' % (nsmap['rsm'], ZUGFERD_LEVEL)

def _add_header_block(root, ns):
        header_doc = etree.SubElement(
            root, ns['rsm'] + 'HeaderExchangedDocument')
        header_doc_id = etree.SubElement(header_doc, ns['ram'] + 'ID')
        if INVOICE['state'] in ('open', 'paid'):
            header_doc_id.text = INVOICE['number']
        else:
            header_doc_id.text = INVOICE['state']
        header_doc_name = etree.SubElement(header_doc, ns['ram'] + 'Name')
        if INVOICE['type'] == 'out_refund':
            header_doc_name.text = 'Refund'
        else:
            header_doc_name.text = 'Invoice'
        header_doc_typecode = etree.SubElement(
            header_doc, ns['ram'] + 'TypeCode')
        header_doc_typecode.text = '380'
        date_invoice_dt = time.strftime("%Y%m%d")
        _add_date('IssueDateTime', date_invoice_dt, header_doc, ns)
        if INVOICE['comment']:
            note = etree.SubElement(header_doc, ns['ram'] + 'IncludedNote')
            content_note = etree.SubElement(note, ns['ram'] + 'Content')
            content_note.text = INVOICE['comment']

# Create your views here.
def generate_zugferd_xml(request):
    """
        Generate zugferd_xml file
    """
    nsmap = {
        'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
        'rsm': 'urn:ferd:CrossIndustryDocument:invoice:1p0',
        'ram': 'urn:un:unece:uncefact:data:standard:'
                'ReusableAggregateBusinessInformationEntity:12',
        'udt': 'urn:un:unece:uncefact:data:'
                'standard:UnqualifiedDataType:15',
        }
    ns = {
        'rsm': '{urn:ferd:CrossIndustryDocument:invoice:1p0}',
        'ram': '{urn:un:unece:uncefact:data:standard:'
                'ReusableAggregateBusinessInformationEntity:12}',
        'udt': '{urn:un:unece:uncefact:data:standard:'
                'UnqualifiedDataType:15}',
        }
    
    sign = 1

    pdf_file = open('2.pdf', 'rb')
    read_pdf = PdfFileReader(pdf_file)
    number_of_pages = read_pdf.getNumPages()
    
    root = etree.Element(ns['rsm'] + 'CrossIndustryDocument', nsmap=nsmap)
    
    _add_document_context_block(root, nsmap, ns)
    _add_header_block(root, ns)

    trade_transaction = etree.SubElement(
        root, ns['rsm'] + 'SpecifiedSupplyChainTradeTransaction')

    _add_trade_agreement_block(trade_transaction, ns)
    _add_trade_delivery_block(trade_transaction, ns)
    _add_trade_settlement_block(trade_transaction, sign, ns)

    # print dummy data
    xml_string = etree.tostring(
        root, pretty_print=True, encoding='UTF-8', xml_declaration=True)
    print "&&&&& XML :   ", xml_string

    # line_number = 0
    # for iline in number_of_pages:
    #     line_number += 1
    #     self._add_invoice_line_block(
    #         trade_transaction, iline, line_number, sign, ns)

    # xml_string = etree.tostring(
    #     root, pretty_print=True, encoding='UTF-8', xml_declaration=True)
    # # self._check_xml_schema(
    # #     xml_string, 'account_invoice_factur-x/data/ZUGFeRD1p0.xsd')
    # logger.debug(
    #     'ZUGFeRD XML file generated for invoice ID')
    # logger.debug(xml_string)
    # return xml_string
    return HttpResponse("ok")

def pdf_is_zugfered(request, filename):
    """
        check if the pdf file is ZUGFeRE format
    """
    pdf_file = open(filename, 'rb')
    with open(filename, 'rb') as fp:
        pdf_content = fp.read()

    read_pdf = PdfFileReader(pdf_file)
    number_of_pages = read_pdf.getNumPages()
    
    pdb.set_trace()
    is_zugferd = False
    try:
        
        fd = StringIO(pdf_content)
        pdf = PdfFileReader(fd)
        pdf_root = pdf.trailer['/Root']
        logger.debug('pdf_root=%s', pdf_root)
        embeddedfiles = pdf_root['/Names']['/EmbeddedFiles']['/Names']
        print "Embeded Files:  ", embeddedfiles
        root = etree.Element(ns['rsm'] + 'CrossIndustryDocument', nsmap=nsmap)
        for embeddedfile in embeddedfiles:
            if embeddedfile == ZUGFERD_FILENAME:
                is_zugferd = True
                return is_zugferd
                break
    except:
        pass

    return is_zugferd
