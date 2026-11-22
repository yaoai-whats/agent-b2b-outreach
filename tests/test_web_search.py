"""Tests for scripts/web_search.py provider adapters.

The provider functions are pure request/response mapping around one
HTTP helper, so these tests stub that helper and pin: each provider's
endpoint, auth header, request body, and how its response shape is
normalised to {title, url, snippet}; the configured-key priority
order; and the keyless Keenable fallback that runs before the
FALLBACK exit when no key is configured at all.

Run from the repository root:
    python3 -m unittest discover -s tests
"""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "scripts"))

import web_search  # noqa: E402

KEY_ENVS = [env for env, _name, _fn in web_search.PROVIDERS]


class ProviderCase(unittest.TestCase):
    def setUp(self):
        self.calls = []

    def stub_post(self, response):
        def fake_post(url, payload, headers, timeout=30):
            self.calls.append((url, payload, headers))
            return response
        return fake_post

    def run_search(self, env_value, response):
        env = {name: "" for name in KEY_ENVS}
        env.update(env_value)
        with mock.patch.dict(os.environ, env, clear=False):
            for name in KEY_ENVS:
                if not env[name]:
                    os.environ.pop(name, None)
            with mock.patch.object(web_search, "_post",
                                   self.stub_post(response)):
                return web_search.do_search("florist wholesale Berlin", 5,
                                            "", "")


class TestKeenable(ProviderCase):
    def test_keyed_request_and_mapping(self):
        out = self.run_search(
            {"KEENABLE_API_KEY": "keen_test"},
            {"results": [{"title": "T", "url": "https://x.example",
                          "snippet": "S", "description": "D"}]})
        url, payload, headers = self.calls[0]
        self.assertEqual(url, "https://api.keenable.ai/v1/search")
        self.assertEqual(headers.get("X-API-Key"), "keen_test")
        self.assertEqual(payload, {"query": "florist wholesale Berlin",
                                   "max_results": 5})
        self.assertEqual(out["provider"], "keenable")
        self.assertEqual(out["results"],
                         [{"title": "T", "url": "https://x.example",
                           "snippet": "S"}])

    def test_description_used_when_snippet_missing(self):
        out = self.run_search(
            {"KEENABLE_API_KEY": "keen_test"},
            {"results": [{"title": "T", "url": "https://x.example",
                          "description": "D"}]})
        self.assertEqual(out["results"][0]["snippet"], "D")


class TestExa(ProviderCase):
    def test_keyed_request_and_mapping(self):
        out = self.run_search(
            {"EXA_API_KEY": "exa_test"},
            {"results": [{"title": "T", "url": "https://x.example",
                          "highlights": ["part one", "part two"]}]})
        url, payload, headers = self.calls[0]
        self.assertEqual(url, "https://api.exa.ai/search")
        self.assertEqual(headers.get("x-api-key"), "exa_test")
        self.assertEqual(payload["numResults"], 5)
        self.assertEqual(out["provider"], "exa")
        self.assertEqual(out["results"][0]["snippet"], "part one part two")


class TestLinkup(ProviderCase):
    def test_keyed_request_and_mapping(self):
        out = self.run_search(
            {"LINKUP_API_KEY": "linkup_test"},
            {"results": [
                {"name": "T", "url": "https://x.example", "content": "C",
                 "type": "text"},
                {"name": "I", "url": "https://img.example", "content": "",
                 "type": "image"}]})
        url, payload, headers = self.calls[0]
        self.assertEqual(url, "https://api.linkup.so/v1/search")
        self.assertEqual(headers.get("Authorization"), "Bearer linkup_test")
        self.assertEqual(payload["outputType"], "searchResults")
        self.assertEqual(out["provider"], "linkup")
        self.assertEqual(out["results"],
                         [{"title": "T", "url": "https://x.example",
                           "snippet": "C"}])


class TestPriorityAndFallback(ProviderCase):
    def test_serper_still_wins_over_new_providers(self):
        out = self.run_search(
            {"SERPER_API_KEY": "s", "KEENABLE_API_KEY": "k",
             "EXA_API_KEY": "e"},
            {"organic": [{"title": "T", "link": "https://x.example",
                          "snippet": "S"}]})
        self.assertEqual(out["provider"], "serper")
        self.assertEqual(self.calls[0][0], "https://google.serper.dev/search")

    def test_keyless_keenable_when_no_key_configured(self):
        out = self.run_search(
            {},
            {"results": [{"title": "T", "url": "https://x.example",
                          "snippet": "S"}]})
        url, _payload, headers = self.calls[0]
        self.assertEqual(url, "https://api.keenable.ai/v1/search/public")
        self.assertIn("X-Keenable-Title", headers)
        self.assertEqual(out["provider"], "keenable-keyless")
        self.assertIn("note", out)

    def test_fallback_exit_when_keyless_also_fails(self):
        import urllib.error
        def boom(url, payload, headers, timeout=30):
            raise urllib.error.URLError("down")
        env = {name: "" for name in KEY_ENVS}
        with mock.patch.dict(os.environ, env, clear=False):
            for name in KEY_ENVS:
                os.environ.pop(name, None)
            with mock.patch.object(web_search, "_post", boom):
                with self.assertRaises(SystemExit) as ctx:
                    web_search.do_search("q", 5, "", "")
        self.assertEqual(ctx.exception.code, 3)


if __name__ == "__main__":
    unittest.main()
