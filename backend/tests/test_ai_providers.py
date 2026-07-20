import os
import unittest

from backend.ai_providers import resolve_provider, build_llm_request


class AiProviderTests(unittest.TestCase):
    def test_prefers_gemini_when_env_key_is_present(self):
        os.environ["GEMINI_API_KEY"] = "test-key"
        provider = resolve_provider(use_gemini=False, gemini_api_key=None, openai_api_key=None)
        self.assertEqual(provider, "gemini")

    def test_uses_openai_when_gemini_is_not_configured(self):
        os.environ.pop("GEMINI_API_KEY", None)
        provider = resolve_provider(use_gemini=False, gemini_api_key=None, openai_api_key="openai-key")
        self.assertEqual(provider, "openai")

    def test_builds_gemini_request_payload(self):
        request = build_llm_request(
            provider="gemini",
            model="gemini-2.0-flash",
            api_key="gemini-key",
            api_base="https://generativelanguage.googleapis.com/v1beta",
            temperature=0.8,
            system_prompt="system",
            user_message="user",
        )
        self.assertEqual(request["url"], "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=gemini-key")
        self.assertIn("contents", request["json"])
        self.assertEqual(request["json"]["generationConfig"]["temperature"], 0.8)


if __name__ == "__main__":
    unittest.main()
