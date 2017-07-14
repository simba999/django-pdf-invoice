from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from invoice.models import Invoice
from invoice.pdf import draw_pdf
from invoice.utils import pdf_response

from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Table
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm

try:
    from django.utils import importlib
except ImportError:
    import importlib

from invoice.conf import settings
from django.http import HttpResponse
from datetime import datetime
import pdb


def pdf_view(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    pdb_set_trace()
    return pdf_response(draw_pdf, invoice.file_name(), invoice)

def pdf_user_view(request, invoice_id):
    invoice = get_object_or_404(Invoice, invoice_id=invoice_id, user=request.user)
    return pdf_response(draw_pdf, invoice.file_name(), invoice)

class invoice:
    class address:
        contact_name = 'Papierflieger-Vertriebs-GmbH'
        address_one = 'Rabattstr. 25'
        address_two = ''
        county = 'Papierfeld'
        town = 'Osterhausen'
        postcode = 'DE-34567'
        class country:
            name = 'Germany'
    
    invoice_id = 1
    invoice_date = datetime.now()
    currency = 'EUR'

    class user:
        username = 'User1'

ITEM = [
    {
        'quantity': 12,
        'description': 'Best Cup',
        'unit_price': 2.5,
        'total': 25
    },
    {
        'quantity': 50,
        'description': 'Best Cup',
        'unit_price': 2.0,
        'total': 100
    }
]

# inv_module = importlib.import_module(settings.INV_MODULE)
# header_func = inv_module.draw_header
# address_func = inv_module.draw_address
# footer_func = inv_module.draw_footer

def format_currency(amount, currency):
    if currency:
        return u"{1} {0:.2f} {1}".format(amount, currency)

    return u"%s %.2f %s" % (
        '\u20ac35', u'EUR'
    )

def to_pdf(buffer):
    """ Draws the invoice """
    canvas = Canvas(buffer, pagesize=A4)
    canvas.translate(0, 29.7 * cm)
    canvas.setFont('Helvetica', 10)

    canvas.saveState()
    # header_func(canvas)
    canvas.restoreState()

    canvas.saveState()
    # footer_func(canvas)
    canvas.restoreState()

    canvas.saveState()
    # address_func(canvas)
    canvas.restoreState()

    # Client address
    textobject = canvas.beginText(1.5 * cm, -2.5 * cm)
    if invoice.address.contact_name:
        textobject.textLine(invoice.address.contact_name)
    textobject.textLine(invoice.address.address_one)
    if invoice.address.address_two:
        textobject.textLine(invoice.address.address_two)
    textobject.textLine(invoice.address.town)
    if invoice.address.county:
        textobject.textLine(invoice.address.county)
    textobject.textLine(invoice.address.postcode)
    textobject.textLine(invoice.address.country.name)
    canvas.drawText(textobject)

    # Info
    textobject = canvas.beginText(1.5 * cm, -6.75 * cm)
    textobject.textLine(u'Invoice ID: %s' % invoice.invoice_id)
    textobject.textLine(u'Invoice Date: %s' % invoice.invoice_date.strftime('%d %b %Y'))
    textobject.textLine(u'Client: %s' % invoice.user.username)
    canvas.drawText(textobject)

    # Items
    data = [[u'Quantity', u'Description', u'Amount', u'Total'], ]
    for item in ITEM:
        data.append([
            item['quantity'],
            item['description'],
            format_currency(item['unit_price'], invoice.currency),
            format_currency(item['total'], invoice.currency)
        ])
    data.append([u'', u'', u'Total:', format_currency(12312, invoice.currency)])
    table = Table(data, colWidths=[2 * cm, 11 * cm, 3 * cm, 3 * cm])
    table.setStyle([
        ('FONT', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (-1, -1), (0.2, 0.2, 0.2)),
        ('GRID', (0, 0), (-1, -2), 1, (0.7, 0.7, 0.7)),
        ('GRID', (-2, -1), (-1, -1), 1, (0.7, 0.7, 0.7)),
        ('ALIGN', (-2, 0), (-1, -1), 'RIGHT'),
        ('BACKGROUND', (0, 0), (-1, 0), (0.8, 0.8, 0.8)),
    ])
    tw, th, = table.wrapOn(canvas, 15 * cm, 19 * cm)
    table.drawOn(canvas, 1 * cm, -8 * cm - th)

    canvas.showPage()
    canvas.save()

def print_pdf(request):
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = "attachment; filename=\"%s\"" % 'IT_invoice.pdf'
    to_pdf(response)
    return response
