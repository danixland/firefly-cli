import unittest
from unittest.mock import MagicMock
from firefly_cli.resolver import Resolver
from firefly_cli.errors import ResolutionError

def client_returning(items):
    c = MagicMock()
    c.request.return_value = {
        "data": [
            {"id": i["id"], "type": "accounts", "attributes": i["attrs"]}
            for i in items
        ]
    }
    return c

class TestResolver(unittest.TestCase):
    def test_resolves_unique_account_name(self):
        c = client_returning([
            {"id": "3", "attrs": {"name": "Checking", "type": "asset"}},
            {"id": "4", "attrs": {"name": "Savings", "type": "asset"}},
        ])
        r = Resolver(c)
        acc = r.account("checking")  # case-insensitive
        self.assertEqual(acc["id"], "3")
        self.assertEqual(acc["type"], "asset")

    def test_no_match_raises_with_candidates(self):
        c = client_returning([{"id": "3", "attrs": {"name": "Checking", "type": "asset"}}])
        r = Resolver(c)
        with self.assertRaises(ResolutionError) as ctx:
            r.account("Nope")
        self.assertIn("Checking", str(ctx.exception))

    def test_ambiguous_match_raises(self):
        c = client_returning([
            {"id": "3", "attrs": {"name": "Cash", "type": "asset"}},
            {"id": "9", "attrs": {"name": "Cash", "type": "asset"}},
        ])
        r = Resolver(c)
        with self.assertRaises(ResolutionError) as ctx:
            r.account("Cash")
        self.assertIn("3", str(ctx.exception))
        self.assertIn("9", str(ctx.exception))
