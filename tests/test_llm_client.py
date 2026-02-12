import json
import unittest
from unittest.mock import Mock, patch

import requests

from common import llm_client


def _http_error_response(status_code):
    response = Mock()
    response.status_code = status_code
    return requests.HTTPError(f"{status_code} Client Error", response=response)


def _success_response(content):
    response = Mock()
    response.raise_for_status.return_value = None
    chunk = json.dumps(
        {"choices": [{"delta": {"content": content}}]},
        ensure_ascii=False,
    )
    response.iter_lines.return_value = [
        f"data: {chunk}",
        "data: [DONE]",
    ]
    response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": content
                }
            }
        ]
    }
    return response


def _error_response(status_code):
    response = Mock()
    response.raise_for_status.side_effect = _http_error_response(status_code)
    response.json.return_value = {"error": {"message": "error"}}
    return response


class TestLlmClient(unittest.TestCase):
    def test_request_payload_does_not_include_max_tokens(self):
        with patch("common.llm_client.requests.post", return_value=_success_response("ok")) as mocked_post:
            result = llm_client.chat_completion("hi", model="gpt")

        self.assertEqual(result, "ok")
        payload = mocked_post.call_args.kwargs["json"]
        self.assertNotIn("max_tokens", payload)
        self.assertTrue(payload["stream"])

    def test_stream_response_combines_delta_content(self):
        response = Mock()
        response.raise_for_status.return_value = None
        response.iter_lines.return_value = [
            'data: {"choices":[{"delta":{"content":"hel"}}]}',
            'data: {"choices":[{"delta":{"content":"lo"}}]}',
            'data: {"choices":[{"delta":{"content":" world"}}]}',
            "data: [DONE]",
        ]
        with patch("common.llm_client.requests.post", return_value=response):
            result = llm_client.chat_completion("hi")

        self.assertEqual(result, "hello world")

    def test_always_uses_fixed_gpt_5_1_low_by_default(self):
        with patch("common.llm_client.requests.post", return_value=_success_response("ok")) as mocked_post:
            result = llm_client.chat_completion("hi")

        self.assertEqual(result, "ok")
        payload = mocked_post.call_args.kwargs["json"]
        self.assertEqual(payload["model"], "gpt-5.1 low")

    def test_ignores_model_argument_and_still_uses_fixed_model(self):
        with patch("common.llm_client.requests.post", return_value=_success_response("ok")) as mocked_post:
            result = llm_client.chat_completion("hi", model="gemini-3-pro-high")

        self.assertEqual(result, "ok")
        payload = mocked_post.call_args.kwargs["json"]
        self.assertEqual(payload["model"], "gpt-5.1 low")

    def test_does_not_fallback_on_error(self):
        primary_fail = _error_response(404)
        fallback_success = _success_response("should-not-be-used")

        with patch("common.llm_client.requests.post", side_effect=[primary_fail, fallback_success]) as mocked_post:
            result = llm_client.chat_completion("hi")

        self.assertIsNone(result)
        self.assertEqual(mocked_post.call_count, 1)

    def test_omits_authorization_header_when_api_key_empty(self):
        with patch.object(llm_client, "DEFAULT_API_KEY", ""):
            with patch("common.llm_client.requests.post", return_value=_success_response("ok")) as mocked_post:
                result = llm_client.chat_completion("hi", model="gpt")

        self.assertEqual(result, "ok")
        headers = mocked_post.call_args.kwargs["headers"]
        self.assertNotIn("Authorization", headers)

    def test_handles_base_url_with_v1_suffix(self):
        with patch.object(llm_client, "DEFAULT_BASE_URL", "http://127.0.0.1:8045/v1"):
            with patch("common.llm_client.requests.post", return_value=_success_response("ok")) as mocked_post:
                result = llm_client.chat_completion("hi", model="gpt")

        self.assertEqual(result, "ok")
        called_url = mocked_post.call_args.args[0]
        self.assertEqual(called_url, "http://127.0.0.1:8045/v1/chat/completions")


if __name__ == "__main__":
    unittest.main()
