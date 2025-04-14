import qrcode
from io import BytesIO 

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