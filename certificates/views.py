
from django.shortcuts import render, redirect
from django.core.mail import EmailMessage
from django.http import HttpResponse
from .models import EmailNameData, Certificate, Coordinate
from .forms import UploadEmailFileForm, UploadCertificateForm
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PyPDF2 import PdfReader, PdfWriter
import io
import csv
import base64
import fitz  # PyMuPDF
import os
from django.conf import settings

def get_session_id(request):
    """Ensure a unique session ID exists for the user."""
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key


# Upload Email File
def upload_email_file(request):
    session_id = get_session_id(request)

    if request.method == 'POST':
        form = UploadEmailFileForm(request.POST, request.FILES)
        if form.is_valid():
            file = request.FILES['file']
            decoded_file = file.read().decode('utf-8').splitlines()
            reader = csv.reader(decoded_file)
            for row in reader:
                name, email = row
                EmailNameData.objects.create(name=name, email=email, session_id=session_id)
            return redirect('upload_certificate')
    else:
        form = UploadEmailFileForm()
    return render(request, 'upload_email_file.html', {'form': form})


# Upload Certificate
# def upload_certificate(request):
#     session_id = get_session_id(request)

#     if request.method == 'POST':
#         form = UploadCertificateForm(request.POST, request.FILES)
#         if form.is_valid():
#             file = request.FILES['file']
#             Certificate.objects.create(file=file.read(), session_id=session_id)
#             return redirect('set_coordinates')
#     else:
#         form = UploadCertificateForm()
#     return render(request, 'upload_certificate.html', {'form': form})
def upload_certificate(request):
    session_id = get_session_id(request)

    if request.method == 'POST':
        form = UploadCertificateForm(request.POST, request.FILES)
        if form.is_valid():
            file = request.FILES['file']
            # Save the raw binary data in the BinaryField
            Certificate.objects.create(file=file.read(), session_id=session_id)
            return redirect('set_coordinates')
    else:
        form = UploadCertificateForm()
    
    return render(request, 'upload_certificate.html', {'form': form})


# Set Coordinates
# def set_coordinates(request):
#     session_id = get_session_id(request)
#     certificate_image_data = None
#     certificate_width = 1000  # Default width
#     certificate_height = 1000  # Default height

#     try:
#         certificate = Certificate.objects.filter(session_id=session_id).latest('uploaded_at')

#         # Convert PDF to image
#         if certificate.file:
#             pdf_data = certificate.file
#             pdf_document = fitz.open(stream=pdf_data, filetype="pdf")
#             page = pdf_document[0]
#             pix = page.get_pixmap()
#             image_data = pix.tobytes("png")
#             certificate_image_data = base64.b64encode(image_data).decode('utf-8')

#             certificate_width = pix.width
#             certificate_height = pix.height
#     except Certificate.DoesNotExist:
#         return redirect('error_page')

#     if request.method == 'POST':
#         try:
#             x = request.POST.get('x')
#             y = request.POST.get('y')
#             font_size = request.POST.get('fontSize')
#             font_color = request.POST.get('fontColor')

#             Coordinate.objects.create(
#                 x=float(x),
#                 y=float(y),
#                 font_size=int(font_size),
#                 font_color=font_color,
#                 certificate=certificate,
#                 session_id=session_id
#             )
#             return redirect('send_emails')
#         except Exception as e:
#             print(f"Error saving data: {e}")

#     return render(request, 'set_coordinates.html', {
#         'certificate_image_data': certificate_image_data,
#         'certificate_width': certificate_width,
#         'certificate_height': certificate_height
#     })

import base64
import fitz  # PyMuPDF

def set_coordinates(request):
    session_id = get_session_id(request)
    certificate_image_data = None
    certificate_width = 1000  # Default width
    certificate_height = 1000  # Default height

    try:
        # Fetch the latest certificate for the session
        certificate = Certificate.objects.filter(session_id=session_id).latest('uploaded_at')
        print(type(certificate.file))  # Should print <class 'memoryview'>
        # Convert PDF to image
        if certificate.file:
            pdf_data = bytes(certificate.file)  # Convert memoryview to bytes
            pdf_document = fitz.open(stream=pdf_data, filetype="pdf")  # Pass binary data to fitz.open
            page = pdf_document[0]
            pix = page.get_pixmap()
            image_data = pix.tobytes("png")
            certificate_image_data = base64.b64encode(image_data).decode('utf-8')

            certificate_width = pix.width
            certificate_height = pix.height
    except Certificate.DoesNotExist:
        return redirect('error_page')
    except Exception as e:
        print(f"Error processing certificate: {e}")
        return redirect('error_page')  # Optionally handle errors gracefully

    if request.method == 'POST':
        try:
            # Extract POST data
            x = request.POST.get('x')
            y = request.POST.get('y')
            font_size = request.POST.get('fontSize')
            font_color = request.POST.get('fontColor')

            # Save coordinates to the database
            Coordinate.objects.create(
                x=float(x),
                y=float(y),
                font_size=int(font_size),
                font_color=font_color,
                certificate=certificate,
                session_id=session_id
            )
            return redirect('send_emails')
        except Exception as e:
            print(f"Error saving data: {e}")

    return render(request, 'set_coordinates.html', {
        'certificate_image_data': certificate_image_data,
        'certificate_width': certificate_width,
        'certificate_height': certificate_height
    })



def hex_to_rgb(hex_color):
    """
    Converts a hex color string to an RGB tuple.

    Args:
        hex_color (str): Color in hex format (e.g., "#ffbb00").

    Returns:
        tuple: A tuple representing the RGB values (r, g, b).

    Raises:
        ValueError: If the hex_color is not a valid 6-character hex code.
    """
    if not isinstance(hex_color, str):
        raise ValueError("Hex color must be a string.")
    
    hex_color = hex_color.lstrip('#')  # Remove the '#' character if present

    if len(hex_color) != 6 or not all(c in "0123456789abcdefABCDEF" for c in hex_color):
        raise ValueError("Invalid hex color format. Ensure it is a 6-character hex code, e.g., '#ffbb00'.")
    
    r = int(hex_color[0:2], 16)  # Red
    g = int(hex_color[2:4], 16)  # Green
    b = int(hex_color[4:6], 16)  # Blue

    return (r, g, b)

def add_name_to_certificate(certificate_binary, name, x, y, font_size, font_color, font_name="MonteCarlo"):
    """
    Adds a name to a certificate at specified coordinates, with given font size and color.
    """
    try:
        print(f"Adding name '{name}' at coordinates X: {x}, Y: {y} using font '{font_name}', size {font_size}, color {font_color}.")

        # Define font path
        # BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        # font_path = os.path.join(BASE_DIR, "fonts", "MonteCarlo-Regular.ttf")
        # font_path = r"C:\Users\RAFAY\Desktop\email sender\certificate_app\fonts\MonteCarlo-Regular.ttf"

        # Register font or fallback to default
        # font_path = get_font_from_db(1)
        
        # font_path = load_static_font()
        font_path = os.path.join(settings.BASE_DIR, "static", "fonts", "MonteCarlo-Regular.ttf")

        if os.path.exists(font_path):
            pdfmetrics.registerFont(TTFont(font_name, font_path))
            print(f"Font '{font_name}' registered successfully.")
        else:
            print(f"Font file not found: {font_path}. Using default font 'Helvetica'.")
            font_name = "Helvetica"

        # Load the certificate PDF
        reader = PdfReader(io.BytesIO(certificate_binary))
        writer = PdfWriter()

        # Get page dimensions
        first_page = reader.pages[0]
        page_width = float(first_page.mediabox.width)
        page_height = float(first_page.mediabox.height)
        print(f"Page dimensions: Width={page_width}, Height={page_height}.")

        # Adjust y-coordinate
        y_inverted = page_height - y
        print(f"Calculated inverted Y-coordinate: {y_inverted}.")

        # Create temporary PDF overlay
        packet = io.BytesIO()
        can = canvas.Canvas(packet, pagesize=(page_width, page_height))
        
        # Set font, size, and color
        can.setFont(font_name, font_size)
        scaled_color = tuple(c / 255 for c in font_color)
        can.setFillColorRGB(*scaled_color)
        can.drawString(x, y_inverted, name)
        can.save()
        packet.seek(0)


        # Merge overlay with original PDF
        overlay_pdf = PdfReader(packet)
        for page in reader.pages:
            page.merge_page(overlay_pdf.pages[0])  # Merge once per page
            writer.add_page(page)

        # Save and return modified PDF
        output = io.BytesIO()
        writer.write(output)
        print("Name added to the certificate successfully.")
        return output.getvalue()

    except Exception as e:
        print(f"Error while adding name to certificate: {e}")
        raise


# Send Emails
# def send_emails(request):
#     session_id = get_session_id(request)

#     try:
#         certificate = Certificate.objects.filter(session_id=session_id).latest('uploaded_at')
#         coordinate = certificate.coordinates.filter(session_id=session_id).first()

#         if not coordinate:
#             return redirect('error_page')

#         recipients = EmailNameData.objects.filter(session_id=session_id)
#         # print(f"[recipient.id] : {[recipient.id]}")
#         for recipient in recipients:
#             font_color_rgb = hex_to_rgb(coordinate.font_color)
#             modified_pdf_data = add_name_to_certificate(
#                 certificate_binary=certificate.file,
#                 name=recipient.name,
#                 x=coordinate.x,
#                 y=coordinate.y,
#                 font_size=coordinate.font_size,
#                 font_color=font_color_rgb
#             )
#             email = EmailMessage(
#                 'Your Certificate',
#                 'Please find your personalized certificate attached.',
#                 'noreply@example.com',
#                 [recipient.email]
#             )
#             email.attach('certificate.pdf', modified_pdf_data, 'application/pdf')
#             email.send()

#         return redirect('success')
#     except Exception as e:
#         print(f"Error while sending emails: {e}")
#         return redirect('error_page')


def send_emails(request):
    session_id = get_session_id(request)

    try:
        # Fetch the latest certificate for the session
        certificate = Certificate.objects.filter(session_id=session_id).latest('uploaded_at')
        coordinate = certificate.coordinates.filter(session_id=session_id).first()

        if not coordinate:
            return redirect('error_page')

        # Fetch all recipients for the session
        recipients = EmailNameData.objects.filter(session_id=session_id)

        for recipient in recipients:
            # Convert font color to RGB and add the name to the certificate
            font_color_rgb = hex_to_rgb(coordinate.font_color)
            modified_pdf_data = add_name_to_certificate(
                certificate_binary=certificate.file,
                name=recipient.name,
                x=coordinate.x,
                y=coordinate.y,
                font_size=coordinate.font_size,
                font_color=font_color_rgb
            )

            # Email subject
            subject = "🎉 Your Personalized Certificate is Ready! 🎓"

            # Email body (simplified without URL)
            message = f"""
            Hi {recipient.name},

            Congratulations! 🎊 Your personalized certificate is ready. 

            We've attached your certificate to this email for your convenience.  
            We're proud of your achievement and wish you continued success in the future! 🌟

            Best regards,  
            Muhammad Rafay Anwar  
            """

            # Email setup
            email = EmailMessage(
                subject,
                message,
                'noreply@example.com',  # Sender's email
                [recipient.email]       # Recipient's email
            )

            # Attach the personalized certificate
            email.attach('certificate.pdf', modified_pdf_data, 'application/pdf')

            # Send the email
            email.send()

        return redirect('success')
    except Exception as e:
        print(f"Error while sending emails: {e}")
        return redirect('error_page')


# Success View
def success_view(request):
    session_id = get_session_id(request)

    try:
        EmailNameData.objects.filter(session_id=session_id).delete()
        Coordinate.objects.filter(session_id=session_id).delete()
        Certificate.objects.filter(session_id=session_id).delete()
    except Exception as e:
        print(f"Error occurred: {e}")

    return render(request, 'success.html')


# from django.shortcuts import get_object_or_404
# from django.http import HttpResponse
# from .models import Font

# def download_font(request, font_id):
#     font = get_object_or_404(Font, id=font_id)
#     response = HttpResponse(font.font_data, content_type='application/octet-stream')
#     response['Content-Disposition'] = f'attachment; filename="{font.name}.ttf"'
#     return response


# def get_font_from_db(font_id):
#     # Font object retrieve karein
#     font = get_object_or_404(Font, id=font_id)

#     # Temporary file path banayein
#     temp_font_path = "temp_font.ttf"

#     # Binary data ko temporary file mein write karein
#     with open(temp_font_path, "wb") as temp_file:
#         temp_file.write(font.font_data)
#     print(f"font name : {font.name}")
#     # Temporary file ka path return karein
#     return temp_font_path


# from PIL import ImageFont

# def load_static_font():
#     # Static fonts folder ka path set karein
#     font_path = os.path.join(settings.BASE_DIR, "static", "fonts", "MonteCarlo-Regular.ttf")

#     # Font load karein using PIL
#     try:
#         font = ImageFont.truetype(font_path, size=24)
#         print("Font loaded successfully!")
#         return font
#     except Exception as e:
#         print(f"Error loading font: {e}")
#         return None