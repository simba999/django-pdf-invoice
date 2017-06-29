# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render, HttpResponse
from StringIO import StringIO
from lxml import etree
from tempfile import NamedTemporaryFile
from datetime import datetime
import logging
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

# Create your views here.
def generate_zugferd_xml(request):
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
    pdb.set_trace()
    root = etree.Element(ns['rsm'] + 'CrossIndustryDocument', nsmap=nsmap)

    # self._add_document_context_block(root, nsmap, ns)
    # self._add_header_block(root, ns)

    trade_transaction = etree.SubElement(
        root, ns['rsm'] + 'SpecifiedSupplyChainTradeTransaction')

    # self._add_trade_agreement_block(trade_transaction, ns)
    # self._add_trade_delivery_block(trade_transaction, ns)
    # self._add_trade_settlement_block(trade_transaction, sign, ns)

    line_number = 0
    for iline in self.invoice_line_ids:
        line_number += 1
        self._add_invoice_line_block(
            trade_transaction, iline, line_number, sign, ns)

    xml_string = etree.tostring(
        root, pretty_print=True, encoding='UTF-8', xml_declaration=True)
    # self._check_xml_schema(
    #     xml_string, 'account_invoice_factur-x/data/ZUGFeRD1p0.xsd')
    logger.debug(
        'ZUGFeRD XML file generated for invoice ID')
    logger.debug(xml_string)
    return xml_string
    return HttpResponse("ok")
