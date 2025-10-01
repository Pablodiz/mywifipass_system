import qrcode
import threading
import base64
from io import BytesIO 
from mywifipass.models import WifiUser
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


def generate_qr_code_base64(data: str) -> str:
    """
    Generates a QR code and returns it as a base64 data URI for inline email embedding.
    
    Args:
        data (str): The data to encode in the QR code.
    
    Returns:
        str: Base64 data URI that can be used directly in <img src="...">
    """
    qr_buffer = generate_qr_code(data)
    qr_buffer.seek(0)
    base64_data = base64.b64encode(qr_buffer.read()).decode('utf-8')
    return f"data:image/png;base64,{base64_data}"


def send_mail(user: WifiUser, update: bool = False) -> None:
    from mywifipass.api.urls import user_qr_url, email_url # Import here to avoid circular import
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.image import MIMEImage
    import smtplib
    from django.conf import settings
    
    # Generate QR code for inline embedding (like company logos)
    qr_data = email_url(user)
    qr_buffer = generate_qr_code(qr_data)
    qr_base64 = generate_qr_code_base64(qr_data)
    
    # Use Content-ID for inline attachment (like email signatures)
    html_content = render_to_string(
        "mywifipass/email/register_email.html",
        context={
            "location": user.wifiLocation, 
            "qr_code_url": "cid:qr_wifi_pass",  # Content-ID reference (like logos)
            "qr_code_base64": qr_base64,        # Base64 as backup
            "pass_url": email_url(user),
            "has_inline_qr": True               # Flag for inline QR
        },
    )

    subject_text = "Your registration for the event: " + user.wifiLocation.name
    if update:
        subject_text = "Your registration has been updated for the event: " + user.wifiLocation.name

    # Create proper multipart/related message (like email signatures with logos)
    msg = MIMEMultipart('related')  # 'related' is key for inline attachments
    msg['Subject'] = subject_text
    msg['From'] = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@mywifipass.com')
    msg['To'] = user.email
    
    # Create text version for clients that don't support HTML
    text_body = f"""
Tu pase WiFi para {user.wifiLocation.name}

Enlace directo: {email_url(user)}

Descarga la app MyWifiPass para usar este código.
El código QR también está adjunto a este email.
"""
    
    # Create HTML version with inline image
    msg_alternative = MIMEMultipart('alternative')
    msg_alternative.attach(MIMEText(text_body, 'plain', 'utf-8'))
    msg_alternative.attach(MIMEText(html_content, 'html', 'utf-8'))
    msg.attach(msg_alternative)
    
    # Add QR code as inline attachment (Content-ID method)
    qr_buffer.seek(0)
    qr_image = MIMEImage(qr_buffer.read(), 'png')
    qr_image.add_header('Content-ID', '<qr_wifi_pass>')  # This is the magic!
    qr_image.add_header('Content-Disposition', 'inline', filename='qr_code.png')
    msg.attach(qr_image)
    
    # Send using Django's email backend
    def do_send_mail(): 
        try:
            # Use Django's backend to send the raw MIME message
            from django.core.mail import get_connection
            connection = get_connection()
            
            # Send the raw message
            connection.open()
            connection.connection.send_message(msg)
            connection.close()
            
            print(f"Email sent successfully to {user.email} with inline QR")
            
        except Exception as e:
            print(f"Failed to send email with inline QR: {e}")
            # Fallback to simple Django email
            try:
                fallback_mail = EmailMultiAlternatives(
                    subject=subject_text,
                    body=text_body,
                    from_email=None,
                    to=[user.email],
                )
                fallback_html = html_content.replace('cid:qr_wifi_pass', qr_base64)
                fallback_mail.attach_alternative(fallback_html, "text/html")
                fallback_mail.send(fail_silently=True)
                print(f"Fallback email sent to {user.email}")
            except Exception as e2:
                print(f"Fallback email also failed: {e2}")
    
    thread = threading.Thread(target=do_send_mail)
    thread.start()