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

logger = logging.getLogger(__name__)

try:
    from PyPDF2 import PdfFileWriter, PdfFileReader
    from PyPDF2.generic import DictionaryObject, DecodedStreamObject,\
        NameObject, createStringObject, ArrayObject
except ImportError:
    logger.debug('Cannot import PyPDF2')

# dummy data
ZUGFERD_LEVEL = 'comfort'
ZUGFERD_FILENAME = 'ZUGFeRD-invoice.xml'
STATE = 'open'
INVOICE = {
    'state': 'open',
    'number': '123456',
    'comment': 'I like Illya because he is perfect guy',
    'type': 'our_invoice',
    'company_id': {
        'name': 'IT Light',
        'vat': '19',
        'partner_id': {
            'zip': '66032',
            'street': 'street A',
            'street2': 'Tower',
            'country_id': 'US',
            'city': 'New York'
        }
    },
    'partner_id': {
        'zip': '66032',
        'street': 'street A',
        'street2': 'Tower',
        'country_id': 'US',
        'city': 'New York'
    },
    'commercial_partner_id': {
        'ref': 'comercial_partner_id_reference',
        'name': 'Big Company',
        'vat': '28'
    },
    'partner_bank_id': {
        'bank_account_link': 'fixed',
        'fixed_journal_id': {
            'bank_account_id': '123457'
        }
    },
    'currency_id': {
        'name': 'eur',
        'decimal_places': 3
    },
    'tax_line_ids': [
        {
            'tax_id': {
                'unece_type_code': '',
                'unece_categ_code': '',
                'amount_type': 'kg'
            },
            'amount': 1,
            'base': 1
        },
        {
            'tax_id': {
                'unece_type_code': '',
                'unece_categ_code': '',
                'amount_type': 'kg'
            },
            'amount': 1,
            'base': 1
        }
    ],
    'payment_mode_id': {
        'note': 'infomation about payment mode',
        'payment_method_id': {
            'unece_code': '',
            'name': ''
        }
    },
    'payment_term_id': {
        'name': 'paypal'
    },
    'fiscal_position_id': {
        'note': 'information about fiscal postion'
    },
    'date_due': '2017213',
    'amount_untaxed': 235,
    'amount_tax': 120,
    'amount_total': 375,
    'residual': 56
}

# root of xml document
root = None

def _add_date(node_name, date_datetime, parent_node, ns):
    date_node = etree.SubElement(parent_node, ns['ram'] + node_name)
    date_node_str = etree.SubElement(
        date_node, ns['udt'] + 'DateTimeString', format='102')
    date_node_str.text = date_datetime

def _add_address_block(partner, parent_node, ns):
    print "*** Partner ****: ", partner
    address = etree.SubElement(
        parent_node, ns['ram'] + 'PostalTradeAddress')
    if partner['zip']:
        address_zip = etree.SubElement(
            address, ns['ram'] + 'PostcodeCode')
        address_zip.text = partner['zip']
    if partner['street']:
        address_street = etree.SubElement(
            address, ns['ram'] + 'LineOne')
        address_street.text = partner['street']
        if partner['street2']:
            address_street2 = etree.SubElement(
                address, ns['ram'] + 'LineTwo')
            address_street2.text = partner['street2']
    if partner['city']:
        address_city = etree.SubElement(
            address, ns['ram'] + 'CityName')
        address_city.text = partner['city']
    if partner['country_id']:
        address_country = etree.SubElement(
            address, ns['ram'] + 'CountryID')
        address_country.text = partner['country_id']

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
    # INVOICE['_add_trade_contact_block(
    #    INVOICE['user_id.partner_id or company.partner_id, seller, ns)
    _add_address_block(company['partner_id'], seller, ns)
    if company['vat']:
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
    # if INVOICE['commercial_partner_id != INVOICE['partner_id:
    #    INVOICE['_add_trade_contact_block(
    #        INVOICE['partner_id, buyer, ns)
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

def _add_trade_settlement_block(trade_transaction, sign, ns):
    inv_currency_name = INVOICE['currency_id']['name']
    prec = INVOICE['currency_id']['decimal_places']
    trade_settlement = etree.SubElement(
        trade_transaction,
        ns['ram'] + 'ApplicableSupplyChainTradeSettlement')
    payment_ref = etree.SubElement(
        trade_settlement, ns['ram'] + 'PaymentReference')
    payment_ref.text = INVOICE['number'] or INVOICE['state']
    invoice_currency = etree.SubElement(
        trade_settlement, ns['ram'] + 'InvoiceCurrencyCode')
    invoice_currency.text = inv_currency_name
    if (
            INVOICE['payment_mode_id'] and
            not INVOICE['payment_mode_id']['payment_method_id']['unece_code']):
        try:
            raise Exception("Missing UNECE code on payment export type '%s'" % INVOICE['payment_mode_id']['payment_method_id']['name'])
        except Exception as error:
            print('caught this error: ' + repr(error))

    if (
            INVOICE['type'] == 'out_invoice' or
            (INVOICE['payment_mode_id'] and
                INVOICE['payment_mode_id']['payment_method_id']['unece_code']
                not in [31, 42])):
        _add_trade_settlement_payment_means_block(trade_settlement, sign, ns)
    tax_basis_total = 0.0
    if INVOICE['tax_line_ids']:
        for tline in INVOICE['tax_line_ids']:
            tax = tline['tax_id']
            if not tax['unece_type_code']:
                try:
                    raise Exception("Missing UNECE Tax Type on tax '%s'" % tax['name'])
                except Exception as error:
                    print('caught this error: ' + repr(error))

            if not tax['unece_categ_code']:
                try:
                    raise Exception("Missing UNECE Tax Category on tax '%s'" % tax['name'])
                except Exception as error:
                    print('caught this error: ' + repr(error))
                
            trade_tax = etree.SubElement(
                trade_settlement, ns['ram'] + 'ApplicableTradeTax')
            amount = etree.SubElement(
                trade_tax, ns['ram'] + 'CalculatedAmount',
                currencyID=inv_currency_name)
            amount.text = unicode(tline['amount'] * sign)
            tax_type = etree.SubElement(
                trade_tax, ns['ram'] + 'TypeCode')
            tax_type.text = tax['unece_categ_code']

            # if (
            #         tax.unece_categ_code != 'S' and
            #         float_is_zero(tax.amount, precision_digits=prec) and
            #         INVOICE['fiscal_position_id'] and
            #         INVOICE['fiscal_position_id']['note']):
            #     exemption_reason = etree.SubElement(
            #         trade_tax, ns['ram'] + 'ExemptionReason')
            #     exemption_reason.text = with_context(
            #         lang=INVOICE['partner_id']['lang'] or 'en_US').\
            #         fiscal_position_id['note']

            base = etree.SubElement(
                trade_tax,
                ns['ram'] + 'BasisAmount', currencyID=inv_currency_name)
            base.text = unicode(tline['base'] * sign)
            tax_basis_total += tline['base']
            tax_categ_code = etree.SubElement(
                trade_tax, ns['ram'] + 'CategoryCode')
            tax_categ_code.text = tax['unece_categ_code']
            if tax['amount_type'] == 'percent':
                percent = etree.SubElement(
                    trade_tax, ns['ram'] + 'ApplicablePercent')
                percent.text = unicode(tax.amount)
    trade_payment_term = etree.SubElement(
        trade_settlement, ns['ram'] + 'SpecifiedTradePaymentTerms')
    trade_payment_term_desc = etree.SubElement(
        trade_payment_term, ns['ram'] + 'Description')
    # The 'Description' field of SpecifiedTradePaymentTerms
    # is a required field, so we must always give a value
    if INVOICE['payment_term_id']:
        trade_payment_term_desc.text = INVOICE['payment_term_id']['name']
    else:
        trade_payment_term_desc.text = 'No specific payment term selected'

    if INVOICE['date_due']:
        date_due_dt = INVOICE['date_due']
        _add_date('DueDateDateTime', date_due_dt, trade_payment_term, ns)

    sums = etree.SubElement(
        trade_settlement,
        ns['ram'] + 'SpecifiedTradeSettlementMonetarySummation')
    line_total = etree.SubElement(
        sums, ns['ram'] + 'LineTotalAmount', currencyID=inv_currency_name)
    line_total.text = '%0.*f' % (prec, INVOICE['amount_untaxed'] * sign)
    charge_total = etree.SubElement(
        sums, ns['ram'] + 'ChargeTotalAmount',
        currencyID=inv_currency_name)
    charge_total.text = '0.00'
    allowance_total = etree.SubElement(
        sums, ns['ram'] + 'AllowanceTotalAmount',
        currencyID=inv_currency_name)
    allowance_total.text = '0.00'
    tax_basis_total_amt = etree.SubElement(
        sums, ns['ram'] + 'TaxBasisTotalAmount',
        currencyID=inv_currency_name)
    tax_basis_total_amt.text = '%0.*f' % (prec, tax_basis_total * sign)
    tax_total = etree.SubElement(
        sums, ns['ram'] + 'TaxTotalAmount', currencyID=inv_currency_name)
    tax_total.text = '%0.*f' % (prec, INVOICE['amount_tax'] * sign)
    total = etree.SubElement(
        sums, ns['ram'] + 'GrandTotalAmount', currencyID=inv_currency_name)
    total.text = '%0.*f' % (prec, INVOICE['amount_total'] * sign)
    prepaid = etree.SubElement(
        sums, ns['ram'] + 'TotalPrepaidAmount',
        currencyID=inv_currency_name)
    residual = etree.SubElement(
        sums, ns['ram'] + 'DuePayableAmount', currencyID=inv_currency_name)
    prepaid.text = '%0.*f' % (
        prec, (INVOICE['amount_total'] - INVOICE['residual']) * sign)
    residual.text = '%0.*f' % (prec, INVOICE['residual'] * sign)

def _add_trade_settlement_payment_means_block(trade_settlement, sign, ns):
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

    # mapping for namespaces for xml
    # inspired from https://github.com/OCA/edi/blob/10.0/account_invoice_factur-x/models/account_invoice.py
    nsmap = {
        'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
        'rsm': 'urn:ferd:CrossIndustryDocument:invoice:1p0',
        'ram': 'urn:un:unece:uncefact:data:standard:'
                'ReusableAggregateBusinessInformationEntity:12',
        'udt': 'urn:un:unece:uncefact:data:'
                'standard:UnqualifiedDataType:15',
        }

    # values for namespaces for xml
    # inspired from https://github.com/OCA/edi/blob/10.0/account_invoice_factur-x/models/account_invoice.py
    ns = {
        'rsm': '{urn:ferd:CrossIndustryDocument:invoice:1p0}',
        'ram': '{urn:un:unece:uncefact:data:standard:'
                'ReusableAggregateBusinessInformationEntity:12}',
        'udt': '{urn:un:unece:uncefact:data:standard:'
                'UnqualifiedDataType:15}',
        }
    
    # variable for type to check if it is "invoice" or "refund"
    # if type is invoice, then 1 or -1
    sign = 1
    
    # 2.pdf is sample Zugrefd pdf file  
    pdf_file = open('2.pdf', 'rb')
    read_pdf = PdfFileReader(pdf_file)
    # get the toal number of pages
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
    #     INVOICE['_add_invoice_line_block(
    #         trade_transaction, iline, line_number, sign, ns)

    # xml_string = etree.tostring(
    #     root, pretty_print=True, encoding='UTF-8', xml_declaration=True)
    # # INVOICE['_check_xml_schema(
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
