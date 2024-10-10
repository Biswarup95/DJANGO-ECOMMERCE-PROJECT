from io import BytesIO
from django.template.loader import get_template
import xhtml2pdf.pisa as pisa
import uuid
from django.conf import settings
from pathlib import Path

def save_pdf(params: dict):
    template = get_template("pdfs/invoice.html")
    html = template.render(params)
    response = BytesIO()
    pdf = pisa.CreatePDF(BytesIO(html.encode('UTF-8')), dest=response)
    file_name = str(uuid.uuid4()) + ".pdf"
    pdf_path = Path(settings.BASE_DIR) / f"public/static/{file_name}"

    try:
        with open(pdf_path, 'wb') as output:
            output.write(response.getvalue())
    except Exception as e:
        print(e)

    if pdf.err:
        return '', False

    return file_name, True
