import os
import base64
import requests
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(
    api_key=os.getenv("LLM_API_KEY"),
    base_url=os.getenv("LLM_BASE_URL")
)

def generate_image_from_text(prompt: str, output_path: str, model: str = "NanoBanana Pro", size: str = "1024x1792"):
    """
    Generate an image using the OpenAI-compatible API and save it to the output path.

    Args:
        prompt: The image generation prompt.
        output_path: Full path to save the generated image.
        model: Model name to use (default: NanoBanana Pro).
        size: Image size (default: 1024x1792 for 9:16).

    Returns:
        bool: True if successful, False otherwise.
    """
    print(f"🎨 Generating image with prompt: {prompt[:50]}...")
    try:
        response = client.images.generate(
            model=model,
            prompt=prompt,
            n=1,
            size=size,
            response_format="b64_json"
        )

        # Save image
        if hasattr(response, 'data') and len(response.data) > 0:
            item = response.data[0]

            # Handle b64_json
            if hasattr(item, 'b64_json') and item.b64_json:
                image_data = base64.b64decode(item.b64_json)
                with open(output_path, "wb") as f:
                    f.write(image_data)
                print(f"✅ Image saved to: {output_path}")
                return True

            # Handle url
            elif hasattr(item, 'url') and item.url:
                img_res = requests.get(item.url)
                if img_res.status_code == 200:
                    with open(output_path, "wb") as f:
                        f.write(img_res.content)
                    print(f"✅ Image downloaded to: {output_path}")
                    return True
                else:
                    print(f"❌ Failed to download image from URL: {item.url}")

        print("❌ No image data received in response")
        return False

    except Exception as e:
        print(f"❌ Image generation failed: {e}")
        return False
