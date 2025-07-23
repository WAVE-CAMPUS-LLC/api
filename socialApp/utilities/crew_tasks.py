import openai
from urllib.request import urlopen
from django.core.files.base import ContentFile
from socialApp.models import Crew
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

openai.api_key = settings.COLLEGE_OPENAI_API_KEY


def generate_crew_image_prompt(crew):
    return (
        f"Stylized crew profile image for a college group named '{crew.name}'. "
        f"Theme: {crew.bio or 'college social group, community, parties, good vibes'}. "
        "Modern, fun, minimalistic vector art, with a friendly vibe."
    )


def generate_crew_image(crew_id):
    crew = Crew.objects.get(crewId=crew_id)

    prompt = generate_crew_image_prompt(crew)

    try:
        response = openai.images.generate(
            prompt=prompt, n=1, size="512x512", response_format="url"
        )
        if not response.data or not hasattr(response.data[0], "url"):
            print("No image data returned from OpenAI.")
            return None
        image_url = response.data[0].url
        if not image_url:
            print("Image URL is empty or None.")
            return None
        image_data = urlopen(image_url).read()
        crew.crew_image.save(f"{crew.name}.png", ContentFile(image_data))
        crew.save()
    except Exception as e:
        logger.error(f"Error generating crew image: {e}")
        return None
