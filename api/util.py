import pandas as pd 
from sqlalchemy.sql import func
from . import db, mail
from .models import *
import pdfkit, datetime, PyPDF2, io
from flask import render_template, make_response


#Not in use for now
def get_zones():
    df = pd.read_excel('api/static/data.xlsx', sheet_name='Zones')
    a = df['ZONES'].tolist()

    return a

#Not in use for now
def get_counties():
    df = pd.read_excel('api/static/data.xlsx', sheet_name='Counties')
    counties = df['County'].tolist()
    return counties

#Not in use for now
def get_categories():
    df = pd.read_excel('api/static/data.xlsx', sheet_name='Categories')
    a = df['CATEGORIES'].tolist()
    return a

#Not in use for now
def get_status():
    df = pd.read_excel('api/static/data.xlsx', sheet_name='Status')
    a = df['STATUS'].tolist()
    return a

def get_data():
    def data(a, b):
        df = pd.read_excel('api/static/data.xlsx', sheet_name=a)
        c = df[b].tolist()
        return c
    data1 = {"Counties":data('Counties', 'County'), "Categories":data('Categories', 'CATEGORIES'), "Status":data('Status', 'STATUS'), "Zones":data('Zones', 'ZONES')}

    return data1

#Not in use for now - To be used while calculating cost for supply
def get_county():
    df = pd.read_excel('api/static/data.xlsx', sheet_name= "Counties")
    a = df.to_dict('records')
    return a

def updateJobValue(id):
    # job_query = Job.query.filter_by(id = id)
    supplies = Supply.query.filter_by(job_id = id)
    # print(supplies)
    # value = db.select(db.func.sum(supplies.total))
    sum_query = db.select(db.func.sum(Supply.total)).where(Supply.job_id == id)
    value = db.engine.execute(sum_query).first()[0]
    # print(value)
    # print(job_schema.dump(job_query))
    # job_query = Job.query.filter_by(id = id).first()
    # job_query.value = value
    # db.session.commit()
    # print(job_schema.dump(job_query))

    return value

    # query = db.select([db.func.sum(payment_table.c.amount)])

def printPdf_normal_css_import(context):
    css = 'api/static/styles_print.css'
    # css = 'styles_print.css'
    config = pdfkit.configuration(wkhtmltopdf="C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe")
    html_string = render_template('print.html', **context)
    pdf = pdfkit.from_string(html_string, False, configuration=config, css = css)
    # In the above we incorporate the css as shown, it can be left blank and incoporated inside the html
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=output.pdf'
    return response



def printPdf2(context, a):
    #Since we are using wkhtmltopdf we the css that we are to incorporate is to use webkit rendering engine
    context['type'] = a[0]
    x = datetime.datetime.now()
    context["date"] = x.strftime(" %d/%m/%Y")
    print(context)
    # To incorporate the css
    options = {
        'quiet': '',
        'enable-local-file-access': '',
        'page-size': 'Letter',
        'orientation': 'Portrait',
        'margin-top': '0.75in',
        'margin-right': '0.75in',
        'margin-bottom': '0.75in',
        'margin-left': '0.75in',
        'no-outline': None,
        'encoding': 'UTF-8',
        'custom-header': [
            ('Accept-Encoding', 'gzip')
        ],
        'user-style-sheet': 'api/static/stylesWebkit.css'
    }

    # pdfkit.from_string(html_string, 'out.pdf', options=options)
    config = pdfkit.configuration(wkhtmltopdf="C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe")
    html_string = render_template('print.html', **context)
    pdf = pdfkit.from_string(html_string, False, configuration=config, options=options)
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=output.pdf'
    return response

def createNotes(job):
    notes = Note.query.order_by(Note.id.desc())
    x = datetime.datetime.now()
    y = x.strftime("/%m/%Y")

    def create(y,sub):
        n = Note(
            deliveryNo = f"Del{y}-{sub}",
            invoiceNo = f"Inv{y}-{sub}", 
            receiptNo = f"Rec{y}-{sub}", 
            job_id = job.id
        ) 

        db.session.add(n)
        db.session.commit()

    if notes.count() > 0:
        if Note.query.filter_by(job_id = job.id).first() is None:
            last = notes.first()
            sub1 = last.deliveryNo[3:-2]
            if y == sub1:
                sub2 = int(last.deliveryNo[-1]) + 1
                create(y, sub2)
            else:
                sub2 = 1
                create(y, sub2)
    else:
        create(y, 1)




def merge_pdfs(pdfs):
    merged_pdf = io.BytesIO()
    merger = PyPDF2.PdfMerger()

    for pdf in pdfs:
        merger.append(pdf)

    merger.write(merged_pdf)
    merged_pdf.seek(0)
    return merged_pdf

def printPdf(context, a):
    pdfs = []
    x = datetime.datetime.now()
    context["date"] = x.strftime(" %d/%m/%Y")
    # To incorporate the css
    options = {
        'quiet': '',
        'enable-local-file-access': '',
        'page-size': 'Letter',
        'orientation': 'Portrait',
        'margin-top': '0.75in',
        'margin-right': '0.75in',
        'margin-bottom': '0.75in',
        'margin-left': '0.75in',
        'no-outline': None,
        'encoding': 'UTF-8',
        'custom-header': [
            ('Accept-Encoding', 'gzip')
        ],
        'user-style-sheet': 'api/static/stylesWebkit.css'
    }

    config = pdfkit.configuration(wkhtmltopdf="C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe")
    
    for item in a:
        # Generate the PDF
        context['type'] = item
        html_string = render_template('print.html', **context)
        pdf = pdfkit.from_string(html_string, False, configuration=config, options=options)
        pdfs.append(io.BytesIO(pdf))
    
    merged_pdf = merge_pdfs(pdfs)
    pdf_name = ""
    if len(a)> 1:
        pdf_name = "Invoice_Delivery"
    else:
        if context["type"]["title"] == "Receipt":
            pdf_name = "Receipt"
        else:
            pdf_name = "RFQ"

    response = make_response(merged_pdf.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename={pdf_name}:{context["job"]["code"]}.pdf'
    
    return response
