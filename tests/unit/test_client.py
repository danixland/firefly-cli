import json, unittest
from unittest.mock import patch, MagicMock
from io import BytesIO
import urllib.error
from firefly_cli.client import Client
from firefly_cli.errors import ApiError

def fake_response(payload, status=200):
    r = MagicMock()
    r.read.return_value = json.dumps(payload).encode()
    r.status = status
    r.__enter__.return_value = r
    r.__exit__.return_value = False
    return r

class TestClient(unittest.TestCase):
    def setUp(self):
        self.c = Client("https://f.example", "tok")

    @patch("firefly_cli.client.urllib.request.urlopen")
    def test_get_builds_url_and_headers(self, urlopen):
        urlopen.return_value = fake_response({"data": []})
        out = self.c.request("GET", "/api/v1/accounts", params={"type": "asset"})
        req = urlopen.call_args[0][0]
        self.assertEqual(req.full_url, "https://f.example/api/v1/accounts?type=asset")
        self.assertEqual(req.get_header("Authorization"), "Bearer tok")
        self.assertEqual(req.get_header("Accept"), "application/vnd.api+json")
        self.assertEqual(out, {"data": []})

    @patch("firefly_cli.client.urllib.request.urlopen")
    def test_post_sends_json_body(self, urlopen):
        urlopen.return_value = fake_response({"data": {"id": "9"}})
        self.c.request("POST", "/api/v1/transactions", body={"x": 1})
        req = urlopen.call_args[0][0]
        self.assertEqual(req.get_method(), "POST")
        self.assertEqual(json.loads(req.data), {"x": 1})
        self.assertEqual(req.get_header("Content-type"), "application/json")

    @patch("firefly_cli.client.urllib.request.urlopen")
    def test_http_error_becomes_apierror(self, urlopen):
        body = json.dumps({"message": "boom"}).encode()
        urlopen.side_effect = urllib.error.HTTPError(
            "u", 422, "Unprocessable", {}, BytesIO(body))
        with self.assertRaises(ApiError) as ctx:
            self.c.request("GET", "/api/v1/accounts")
        self.assertEqual(ctx.exception.status, 422)
        self.assertEqual(ctx.exception.body["message"], "boom")
