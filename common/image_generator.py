import os
import base64
import requests
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DEFAULT_BASE_URL = os.getenv("LLM_BASE_URL", "http://127.0.0.1:8045")
DEFAULT_API_KEY = os.getenv("LLM_API_KEY", "")
_DEFAULT_CLIENT = None


def _normalize_base_url(base_url):
    normalized = (base_url or DEFAULT_BASE_URL or "").strip().rstrip("/")
    if not normalized:
        normalized = "http://127.0.0.1:8045"
    if not normalized.endswith("/v1"):
        normalized = f"{normalized}/v1"
    return normalized


def _normalize_api_key(api_key):
    key = (api_key if api_key is not None else DEFAULT_API_KEY or "").strip()
    return key or "EMPTY_API_KEY"


def _build_openai_client(base_url=None, api_key=None):
    return OpenAI(
        api_key=_normalize_api_key(api_key),
        base_url=_normalize_base_url(base_url),
    )


def _get_default_client():
    global _DEFAULT_CLIENT
    if _DEFAULT_CLIENT is None:
        _DEFAULT_CLIENT = _build_openai_client()
    return _DEFAULT_CLIENT


def generate_image_from_text(
    prompt: str,
    output_path: str,
    model: str = "gemini-3-pro-image",
    size: str = "1024x1792",
    quality: str = "hd",
    client=None,
):
    """
    Generate an image using the OpenAI-compatible API and save it to the output path.

    Args:
        prompt: The image generation prompt.
        output_path: Full path to save the generated image.
        model: Model name to use (default: gemini-3-pro-image).
        size: Image size (default: 1024x1792 for 9:16).
        quality: Image quality (default: hd for high quality).

    Returns:
        bool: True if successful, False otherwise.
    """
    print(f"🎨 Generating image with prompt: {prompt[:50]}...")
    client = client or _get_default_client()
    try:
        response = client.images.generate(
            model=model,
            prompt=prompt,
            n=1,
            size=size,
            quality=quality,
            output_format="png",
            response_format="b64_json"
        )

        # Save image
        if hasattr(response, 'data') and len(response.data) > 0:
            item = response.data[0]
            output_dir = os.path.dirname(output_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)

            # Handle b64_json
            if hasattr(item, 'b64_json') and item.b64_json:
                image_data = base64.b64decode(item.b64_json)
                with open(output_path, "wb") as f:
                    f.write(image_data)
                print(f"✅ Image saved to: {output_path}")
                return True

            # Handle url
            elif hasattr(item, 'url') and item.url:
                img_res = requests.get(item.url, timeout=60)
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
