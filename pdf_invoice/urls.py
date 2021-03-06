"""pdf_invoice URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url
from django.contrib import admin
from app.views import show_xml, regular_pdf_invoice_to_facturx_invoice, create_pdf, show_pdf, print_pdf

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'show_xml', show_xml, name="show_xml"),
    url(r'regular_pdf_invoice_to_facturx_invoice', regular_pdf_invoice_to_facturx_invoice, name="regular_pdf_invoice_to_facturx_invoice"),
    url(r'print_pdf', print_pdf, name="print_pdf"),
    url(r'create_pdf', create_pdf, name="create_pdf"),
    url(r'show_pdf/(?P<file_name>[\w.w+]+)', show_pdf, name="show_pdf")
]
