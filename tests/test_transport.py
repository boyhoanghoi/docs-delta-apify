"""Deterministic regressions for transport trust boundaries; no network access."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import unittest
from unittest.mock import AsyncMock

from docsdelta.config import RunConfig
from docsdelta.transport import FetchError, Page, SafeHttpClient, validate_url


class TransportBoundaryTests(unittest.TestCase):
    def test_noncanonical_numeric_hosts_cannot_skip_public_resolver(self):
        # aiohttp treats digit-and-dot names as IP literals and skips the custom
        # resolver; the OS accepts leading-zero/octal IPv4 forms as loopback.
        for host in (
            "0177.0.0.1", "127.000.000.001", "127.0.0.01",
            "192.168.001.001", "169.254.169.0254", "0.0.0.00",
        ):
            with self.subTest(host=host), self.assertRaises(FetchError):
                validate_url("http://" + host + "/")


class RobotsBoundaryTests(unittest.IsolatedAsyncioTestCase):
    async def test_plain_robots_rules_apply_even_with_wrong_html_mime(self):
        config = RunConfig.from_dict({"urls": ["https://business.example"]})
        client = SafeHttpClient(config)
        client.fetch = AsyncMock(return_value=Page(
            "https://business.example/robots.txt",
            "User-agent: *\nDisallow: /private\n",
            200,
            "text/html; charset=utf-8",
        ))
        self.assertFalse(await client.allowed("https://business.example/private"))
        self.assertTrue(await client.allowed("https://business.example/contact"))


class FakeContent:
    def __init__(self, body):
        self.body = body

    async def iter_chunked(self, size):
        yield self.body


class FakeResponse:
    def __init__(self, url, status=200, *, headers=None, body=b"<title>Business</title>"):
        self.url = url
        self.status = status
        self.headers = {"Content-Type": "text/html", **(headers or {})}
        self.charset = "utf-8"
        self.content = FakeContent(body)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


class FakeSession:
    def __init__(self, responses):
        self.responses = responses
        self.requested = []

    def get(self, url, **kwargs):
        self.requested.append(url)
        return self.responses[url]


class RedirectBoundaryTests(unittest.IsolatedAsyncioTestCase):
    def client(self, responses):
        config = RunConfig.from_dict({"urls": ["https://business.example"]})
        client = SafeHttpClient(config)
        client.session = FakeSession(responses)
        client._pace = AsyncMock()
        client.allowed = AsyncMock(return_value=True)
        return client

    async def test_private_literal_redirect_is_rejected_before_next_request(self):
        source = "https://business.example/"
        client = self.client({
            source: FakeResponse(source, 302, headers={"Location": "http://127.000.000.001/"}),
        })
        with self.assertRaises(FetchError):
            await client.fetch(source)
        self.assertEqual(client.session.requested, [source])

    async def test_contact_redirect_outside_scope_is_rejected_before_next_request(self):
        source = "https://business.example/contact"
        client = self.client({
            source: FakeResponse(source, 302, headers={"Location": "https://different.example/contact"}),
        })
        with self.assertRaises(FetchError):
            await client.fetch(source, scope_url="https://business.example/")
        self.assertEqual(client.session.requested, [source])

    async def test_robots_checked_again_on_each_permitted_redirect(self):
        source = "https://business.example/contact"
        final = "https://www.business.example/contact-us"
        client = self.client({
            source: FakeResponse(source, 302, headers={"Location": final}),
            final: FakeResponse(final),
        })
        page = await client.fetch(source, scope_url="https://business.example/")
        self.assertEqual(page.url, final)
        self.assertEqual(client.session.requested, [source, final])
        self.assertEqual([call.args[0] for call in client.allowed.await_args_list], [source, final])


if __name__ == "__main__":
    unittest.main()
