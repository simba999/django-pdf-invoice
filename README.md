Fist of all, please install python packages
python install -r requirements.txt

Then, run the app
python manage.py runserver

To create invoice pdf file, type following url
http://localhost:8000/create_pdf/output_file_name

To embedded xml into pdf file,
http://localhost:8000/regular_pdf_invoice_to_facturx_invoice

