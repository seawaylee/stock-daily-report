import base64
import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from common import image_generator


class _FakeClient:
    def __init__(self, response):
        self.images = SimpleNamespace(generate=lambda **kwargs: response)


class TestImageGenerator(unittest.TestCase):
    def test_normalize_base_url_appends_v1_when_missing(self):
        url = image_generator._normalize_base_url("http://127.0.0.1:8045")
        self.assertEqual(url, "http://127.0.0.1:8045/v1")

    def test_normalize_base_url_keeps_single_v1(self):
        url = image_generator._normalize_base_url("http://127.0.0.1:8045/v1/")
        self.assertEqual(url, "http://127.0.0.1:8045/v1")

    def test_build_openai_client_uses_placeholder_api_key_when_empty(self):
        with patch("common.image_generator.OpenAI") as mocked_openai:
            image_generator._build_openai_client(base_url="http://127.0.0.1:8045", api_key=" ")

        mocked_openai.assert_called_once_with(
            api_key="EMPTY_API_KEY",
            base_url="http://127.0.0.1:8045/v1",
        )

    def test_generate_image_saves_b64_image_data(self):
        content = b"png-bytes"
        b64 = base64.b64encode(content).decode("utf-8")
        response = SimpleNamespace(data=[SimpleNamespace(b64_json=b64, url=None)])
        client = _FakeClient(response)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = os.path.join(temp_dir, "nested", "img.png")
            ok = image_generator.generate_image_from_text(
                prompt="test",
                output_path=output_path,
                model="gpt-image",
                client=client,
            )
            self.assertTrue(ok)
            with open(output_path, "rb") as f:
                self.assertEqual(f.read(), content)

    def test_generate_image_supports_relative_output_path_without_directory(self):
        content = b"png-bytes"
        b64 = base64.b64encode(content).decode("utf-8")
        response = SimpleNamespace(data=[SimpleNamespace(b64_json=b64, url=None)])
        client = _FakeClient(response)

        old_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                os.chdir(temp_dir)
                ok = image_generator.generate_image_from_text(
                    prompt="test",
                    output_path="img.png",
                    model="gpt-image",
                    client=client,
                )
                self.assertTrue(ok)
                with open("img.png", "rb") as f:
                    self.assertEqual(f.read(), content)
            finally:
                os.chdir(old_cwd)


if __name__ == "__main__":
    unittest.main()
