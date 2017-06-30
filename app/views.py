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

    xml_string = etree.tostring(
        root, pretty_print=True, encoding='UTF-8', xml_declaration=True)
    
    print "&&&&& XML :   ", xml_string

    trade_transaction = etree.SubElement(
        root, ns['rsm'] + 'SpecifiedSupplyChainTradeTransaction')

    # self._add_trade_agreement_block(trade_transaction, ns)
    # self._add_trade_delivery_block(trade_transaction, ns)
    # self._add_trade_settlement_block(trade_transaction, sign, ns)

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
