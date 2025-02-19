import os
import io
import base64
import logging
import fitz
import pandas as pd
import csv
from io import StringIO
from django.shortcuts import render, redirect
from django.core.mail import EmailMessage
from django.http import HttpResponse
from django.conf import settings
from django.db import transaction
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from .models import EmailNameData, Certificate, Coordinate
from .forms import UploadEmailFileForm, UploadCertificateForm

# Configure Logger
logger = logging.getLogger(__name__)

def get_session_id(request):
    """Ensure a unique session ID exists for the user."""
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key

# 📩 Upload Email File
def upload_email_file(request):
    session_id = get_session_id(request)

    if request.method == 'POST':
        form = UploadEmailFileForm(request.POST, request.FILES)
        if form.is_valid():
            file = request.FILES['file']
            decoded_file = None

            if file.name.endswith(('.xls', '.xlsx', '.xlsm')):
                csv_data = StringIO()
                pd.read_excel(file).to_csv(csv_data, index=False)
                csv_data.seek(0)
                decoded_file = csv_data.getvalue().splitlines()
            else:
                decoded_file = file.read().decode('utf-8').splitlines()

            rows = [
                EmailNameData(name=row[0], email=row[1], session_id=session_id)
                for row in csv.reader(decoded_file)
                if not EmailNameData.objects.filter(email=row[1], session_id=session_id).exists()
            ]

            if rows:
                EmailNameData.objects.bulk_create(rows)

            return redirect('upload_certificate')  # 🔄 Redirect to Upload Certificate

    else:
        form = UploadEmailFileForm()

    return render(request, 'upload_email_file.html', {'form': form})

# 📜 Upload Certificate
def upload_certificate(request):
    session_id = get_session_id(request)

    if request.method == 'POST':
        form = UploadCertificateForm(request.POST, request.FILES)
        if form.is_valid():
            Certificate.objects.create(file=request.FILES['file'].read(), session_id=session_id)
            return redirect('set_coordinates')  # 🔄 Redirect to Set Coordinates

    else:
        form = UploadCertificateForm()

    return render(request, 'upload_certificate.html', {'form': form})

# 📍 Set Coordinates
def set_coordinates(request):
    session_id = get_session_id(request)

    try:
        certificate = Certificate.objects.filter(session_id=session_id).latest('uploaded_at')
        pdf_document = fitz.open(stream=bytes(certificate.file), filetype="pdf")
        page = pdf_document[0]
        pix = page.get_pixmap()
        image_data = base64.b64encode(pix.tobytes("png")).decode('utf-8')

        if request.method == 'POST':
            x, y = float(request.POST.get('x')), float(request.POST.get('y')) - 9
            font_size = int(request.POST.get('fontSize'))
            font_color = request.POST.get('fontColor')

            with transaction.atomic():
                Coordinate.objects.create(
                    x=x, y=y, font_size=font_size, font_color=font_color,
                    certificate=certificate, session_id=session_id
                )

            return redirect('send_emails')  # 🔄 Redirect to Send Emails

        return render(request, 'set_coordinates.html', {
            'certificate_image_data': image_data,
            'certificate_width': pix.width,
            'certificate_height': pix.height
        })

    except Certificate.DoesNotExist:
        return HttpResponse("Certificate not found.", status=404)
    except Exception as e:
        logger.error(f"Error processing certificate: {e}")
        return HttpResponse("Error processing certificate.", status=500)

# ✉️ Send Emails
def send_email_batch(recipients, certificate_binary, coordinate):
    """Send a batch of emails with personalized certificates."""
    logger.info(f"Starting email batch for {len(recipients)} recipients.")

    for recipient in recipients:
        try:
            clean_email = recipient.email.strip()
            if not clean_email:
                logger.warning(f"Skipping empty email for {recipient.name}")
                continue
            print(f"Adding name to certificate: {recipient.name} at ({coordinate.x}, {coordinate.y})")
            logger.info(f"Adding name to certificate: {recipient.name} at ({coordinate.x}, {coordinate.y})")

            # Generate personalized certificate
            modified_certificate = add_name_to_certificate(
                certificate_binary, recipient.name, coordinate.x, coordinate.y, coordinate.font_size, coordinate.font_color
            )

            email = EmailMessage(
                subject="Your Personalized Certificate is Ready!",
                body=f"Hi {recipient.name},\n\nYour certificate is ready!",
                from_email=settings.EMAIL_HOST_USER,
                to=[clean_email],
            )
            email.attach('certificate.pdf', modified_certificate, 'application/pdf')

            response = email.send(fail_silently=False)
            if response == 0:
                logger.error(f"Email not sent to {clean_email}")

        except Exception as e:
            logger.error(f"Error sending email to {recipient.email}: {str(e)}")

    logger.info("Email batch process completed.")

def send_emails(request):
    """Fetch emails, generate certificates, and send emails."""
    session_id = get_session_id(request)

    try:
        certificate = Certificate.objects.filter(session_id=session_id).latest('uploaded_at')
        coordinate = Coordinate.objects.filter(session_id=session_id).first()
        recipients = EmailNameData.objects.filter(session_id=session_id)

        if not coordinate or not recipients.exists():
            return HttpResponse("Missing coordinates or recipients.", status=404)

        certificate_binary = bytes(certificate.file)
        send_email_batch(recipients, certificate_binary, coordinate)

        return redirect('success')  # 🔄 Redirect to Success Page

    except Exception as e:
        logger.error(f"Error in send_emails: {str(e)}")
        return HttpResponse("Internal server error.", status=500)

# ✏️ Add Name to Certificate
def add_name_to_certificate(certificate_binary, name, x, y, font_size, font_color):
    """Overlay name on a certificate and return the modified PDF."""
    try:
        font_path = os.path.join(settings.BASE_DIR, "static", "fonts", "MonteCarlo-Regular.ttf")
        font_name = "Helvetica" if not os.path.exists(font_path) else "MonteCarlo"

        pdfmetrics.registerFont(TTFont(font_name, font_path if os.path.exists(font_path) else "Helvetica"))

        reader = PdfReader(io.BytesIO(certificate_binary))
        writer = PdfWriter()
        first_page = reader.pages[0]
        page_width = float(first_page.mediabox.width)
        page_height = float(first_page.mediabox.height)

        r, g, b = [int(font_color[i:i+2], 16) / 255 for i in (1, 3, 5)]

        # Create new PDF with name overlay
        packet = io.BytesIO()
        can = canvas.Canvas(packet, pagesize=(page_width, page_height))
        can.setFont(font_name, font_size)
        can.setFillColorRGB(r, g, b)

        y_inverted = page_height - y
        can.drawString(x, y_inverted, name)
        can.save()

        # Merge the overlay
        packet.seek(0)
        overlay_pdf = PdfReader(packet)
        first_page.merge_page(overlay_pdf.pages[0])
        writer.add_page(first_page)

        output = io.BytesIO()
        writer.write(output)
        return output.getvalue()

    except Exception as e:
        logger.error(f"Error adding name to certificate: {e}")
        raise

# ✅ Success View
def success_view(request):
    session_id = get_session_id(request)
    EmailNameData.objects.filter(session_id=session_id).delete()
    Coordinate.objects.filter(session_id=session_id).delete()
    Certificate.objects.filter(session_id=session_id).delete()
    return render(request, 'success.html')
