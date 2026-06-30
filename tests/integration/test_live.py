# Copyright (C) 2026 Danilo M. <danix@danix.xyz>  GPL-2.0-only
import os, unittest
from firefly_cli.client import Client
from firefly_cli.resolver import Resolver
from firefly_cli.output import unwrap

URL = os.environ.get("FIREFLY_TEST_URL")
TOKEN = os.environ.get("FIREFLY_TEST_TOKEN")

@unittest.skipUnless(URL and TOKEN,
    "set FIREFLY_TEST_URL and FIREFLY_TEST_TOKEN to run live tests")
class TestLive(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = Client(URL, TOKEN)
        cls.resolver = Resolver(cls.client)

    def test_about_shape(self):
        resp = self.client.request("GET", "/api/v1/about")
        self.assertIn("version", resp["data"])

    def test_accounts_envelope_and_balance_field(self):
        resp = self.client.request("GET", "/api/v1/accounts",
                                   params={"type": "asset", "limit": 5})
        self.assertIn("data", resp)
        accs = unwrap(resp)
        if accs:
            # Confirm the balance field name assumed by the design.
            self.assertIn("current_balance", accs[0],
                "balance field name differs; update account balance cmd + unit test")

    def test_create_then_delete_transaction(self):
        # Needs an asset account and an expense account on the TEST account.
        accs = unwrap(self.client.request("GET", "/api/v1/accounts",
                                          params={"type": "asset", "limit": 2}))
        if len(accs) < 1:
            self.skipTest("test account has no asset account")
        exp = unwrap(self.client.request("GET", "/api/v1/accounts",
                                         params={"type": "expense", "limit": 1}))
        if not exp:
            self.skipTest("test account has no expense account")
        body = {"transactions": [{
            "type": "withdrawal",
            "date": "2026-06-30",
            "amount": "0.01",
            "description": "firefly-cli integration test",
            "source_id": accs[0]["id"],
            "destination_id": exp[0]["id"],
        }]}
        created = self.client.request("POST", "/api/v1/transactions", body=body)
        tx_id = created["data"]["id"]
        try:
            got = self.client.request("GET", f"/api/v1/transactions/{tx_id}")
            self.assertEqual(got["data"]["id"], tx_id)
        finally:
            self.client.request("DELETE", f"/api/v1/transactions/{tx_id}")
