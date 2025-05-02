import qrcode
from io import BytesIO 
from getEAP_TLS.models import WifiUser
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

def generate_qr_code(data: str) -> BytesIO:
    """
    Generates a QR code for the given data and returns it as a BytesIO object.
    
    Args:
        data (str): The data to encode in the QR code.
    
    Returns:
        BytesIO: A binary stream containing the QR code image in PNG format.
    """
    qr = qrcode.QRCode(version=3, box_size=20, border=10, error_correction=qrcode.constants.ERROR_CORRECT_H)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Save the image to a BytesIO buffer
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)  # Reset the buffer pointer to the beginning
    return buffer


def send_mail(user: WifiUser):
    from getEAP_TLS.api.rest_api import user_qr_url, user_url # Import here to avoid circular import
    html_content = render_to_string(
        "getEAP_TLS/email/register_email.html",
        context={
            "location": user.wifiLocation.name, 
            "qr_code_url": user_qr_url(user.user_uuid),
            "pass_url": user_url(user.user_uuid)      
        },
    )
    mail = EmailMultiAlternatives(
        subject="Your registration for the event: " + user.wifiLocation.name,
        body="",
        from_email=None, 
        to=[user.email],
    )
    mail.attach_alternative(html_content, "text/html")
    mail.send()