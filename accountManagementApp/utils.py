import os
import random
from PIL import Image, ImageDraw, ImageFont
from django.core.files.base import ContentFile
from io import BytesIO
from django.conf import settings


def generate_profile_picture(initials):
    imgSize = (200, 200)

    colors = [
        "#77DD77", "#87CEEB", "#98FF98", "#C8A2C8", 
        "#B0E0E6", "#D3D3D3", "#AFEEEE", "#D8BFD8"
    ]

    img = Image.new("RGB", imgSize, random.choice(colors))
    d = ImageDraw.Draw(img)
    font_size = 120

    try:
        font = ImageFont.truetype(os.path.join(settings.BASE_DIR, "static/fonts/Wanted/WantedSans-Bold-BF65baf135d5a25.otf"), font_size)
    except IOError:
        font = ImageFont.load_default()
        
    # Use a tuple for the position, with the text and font as additional arguments
    text_bbox = d.textbbox((0, 0), initials, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    
    # Calculate x and y position for centering the text
    text_x = (imgSize[0] - text_width) / 2 + 5
    text_y = (imgSize[1] - text_height) / 2 - 30
    d.text((text_x, text_y), initials, fill="white", font=font)
    
    temp_image = BytesIO()
    img.save(temp_image, format="PNG")
    temp_image.seek(0)
    
    return ContentFile(temp_image.read(), f"{initials}_profile.png")
