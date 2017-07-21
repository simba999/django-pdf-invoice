Fist of all, please install python packages
python install -r requirements.txt

Then, run the app
python manage.py runserver

To create invoice pdf file, type following url
http://localhost:8000/create_pdf/output_file_name

To embedded xml into pdf file,
http://localhost:8000/regular_pdf_invoice_to_facturx_invoice


############### Process of Zugeferd e-invoice ############
1. create pdf 1.7 file
2. convert pdf into PDF/A-3
3. add embedded xml into PDF/A compliance

############### References #################
1. create pdf invoice
http://www.pdflib.com/pdflib-cookbook/pdfa/zugferd-invoice/

2. add embedded xml into pdf
http://www.pdflib.com/pdflib-cookbook/pdfa/zugferd-add-xml-to-pdfa/

3.PyPDF2 documentation

############### ISSUES #####################
I have used PyPDF2 for creating pdf invoice, but it is not perfect.
It may be helpful to use PDFlib


############### Soluion ####################
1. created pdf file is not validated for PDF/A-3.
you can check PDF validation here: https://www.pdf-online.com/osa/validate.aspx

Solution:
1. check validate issues
2. PDFlib can handle all of the issues

I think if we solve teh PDF validation issue, then Zugferd involice validation can be done.