import os
import json
import re
from openai import OpenAI

client = OpenAI(api_key=os.getenv("COLLEGE_OPENAI_API_KEY"))


def call_walle_ai(domain: str) -> dict:
    prompt = f"""
        You are WALLE, an AI agent designed to help a social campus app discover colleges based on their email domain.

        Given the domain "{domain}", respond with a JSON containing:
        - name: Full official college name
        - address: Full mailing address
        - city: City where it is located
        - state: State abbreviation (e.g., TN, CA)
        - zip: ZIP code
        - country: Just return "USA"
        - motto: A short motto if available
        - website: The main college website
        - logo_url: Direct URL to the college's official logo image (PNG/JPG format)
        - campus_image_url: Direct URL to a beautiful campus photo showing buildings, quad, or iconic campus scenery

        For the logo_url, try to find the official college logo from their website. Look for URLs that contain terms like "logo", "seal", "emblem" in common formats (.png, .jpg, .jpeg, .svg).

        For the campus_image_url, find a high-quality campus photo showing the campus buildings, quad, library, or other iconic campus scenery. Look for URLs in the college's media gallery, about pages, or marketing materials.

        If you're unsure, guess based on common naming conventions.

        ONLY return a valid JSON object like:
        {{
        "name": "Tennessee State University",
        "address": "3500 John A Merritt Blvd",
        "city": "Nashville",
        "state": "TN",
        "zip": "37209",
        "country": "USA",
        "motto": "Think. Work. Serve.",
        "website": "https://www.tnstate.edu",
        "logo_url": "https://www.tnstate.edu/assets/images/tsu-logo.png",
        "campus_image_url": "https://www.tnstate.edu/assets/images/campus-aerial-view.jpg"
        }}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
        )
        content = response.choices[0].message.content
        print(f"🎓 WALLE AI response: {content}")

        if not content:
            raise ValueError("Empty response from OpenAI")

        try:
            data = json.loads(content.strip())
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if match:
                data = json.loads(match.group())
            else:
                raise ValueError("Could not parse JSON from response")

        required_keys = [
            "name",
            "address",
            "city",
            "state",
            "zip",
            "country",
            "motto",
            "website",
            "logo_url",
            "campus_image_url",
        ]
        if not all(key in data for key in required_keys):
            raise ValueError("Missing keys in OpenAI response")

        print(f"🎓 WALLE AI response: {data}")

        return data

    except Exception as e:
        print(f"❌ Error calling WALLE AI: {e}")
        raise e
