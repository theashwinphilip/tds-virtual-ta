from PIL import Image
import base64
import io
import pytesseract

def extract_text_from_image(base64_image):
    try:
        image_data = base64.b64decode(base64_image)
        image = Image.open(io.BytesIO(image_data))
        text = pytesseract.image_to_string(image)
        return text.strip()
    except Exception as e:
        print(f"Error processing image: {e}")
        return ""