from celery import shared_task
from django.core.mail import EmailMessage

@shared_task
def send_certificate_email(recipient_name, recipient_email, pdf_data):
    email = EmailMessage(
        "🎉 Your Certificate is Ready!",
        f"Hi {recipient_name},\n\nYour certificate is attached.",
        'noreply@example.com',
        [recipient_email]
    )
    email.attach('certificate.pdf', pdf_data, 'application/pdf')
    email.send()
