import unittest
from unittest.mock import MagicMock
from firefly_cli.commands import transaction as tx
from firefly_cli.context import Context

def make_ctx():
    client = MagicMock()
    resolver = MagicMock()
    return Context(client=client, resolver=resolver, human=False), client, resolver

class TestTxAdd(unittest.TestCase):
    def test_infers_withdrawal_from_asset_to_expense(self):
        ctx, client, resolver = make_ctx()
        resolver.account.side_effect = lambda n: {
            "Checking": {"id": "1", "name": "Checking", "type": "asset"},
            "Groceries": {"id": "2", "name": "Groceries", "type": "expense"},
        }[n]
        client.request.return_value = {"data": {"id": "55", "type": "transactions",
                                                "attributes": {}}}
        args = MagicMock(amount="42.50", source="Checking", dest="Groceries",
                         desc="food", date="2026-06-30", category=None,
                         tags=None, type=None)
        rc = tx.cmd_add(args, ctx)
        self.assertEqual(rc, 0)
        method, path = client.request.call_args[0][:2]
        body = client.request.call_args[1]["body"]
        split = body["transactions"][0]
        self.assertEqual((method, path), ("POST", "/api/v1/transactions"))
        self.assertEqual(split["type"], "withdrawal")
        self.assertEqual(split["source_id"], "1")
        self.assertEqual(split["destination_id"], "2")
        self.assertEqual(split["amount"], "42.50")

    def test_infers_deposit_revenue_to_asset(self):
        ctx, client, resolver = make_ctx()
        resolver.account.side_effect = lambda n: {
            "Salary": {"id": "7", "name": "Salary", "type": "revenue"},
            "Checking": {"id": "1", "name": "Checking", "type": "asset"},
        }[n]
        client.request.return_value = {"data": {"id": "1", "attributes": {}}}
        args = MagicMock(amount="1000", source="Salary", dest="Checking",
                         desc="pay", date=None, category=None, tags=None, type=None)
        tx.cmd_add(args, ctx)
        self.assertEqual(client.request.call_args[1]["body"]["transactions"][0]["type"],
                         "deposit")

    def test_explicit_type_overrides_inference(self):
        ctx, client, resolver = make_ctx()
        resolver.account.side_effect = lambda n: {"id": "1", "type": "asset", "name": n}
        client.request.return_value = {"data": {"id": "1", "attributes": {}}}
        args = MagicMock(amount="5", source="A", dest="B", desc=None, date=None,
                         category=None, tags="food,fun", type="transfer")
        tx.cmd_add(args, ctx)
        split = client.request.call_args[1]["body"]["transactions"][0]
        self.assertEqual(split["type"], "transfer")
        self.assertEqual(split["tags"], ["food", "fun"])

    def test_category_passed_raw_not_resolved(self):
        # Category name goes straight to Firefly (auto-creates); resolver untouched.
        ctx, client, resolver = make_ctx()
        resolver.account.side_effect = lambda n: {"id": "1", "type": "asset", "name": n}
        client.request.return_value = {"data": {"id": "1", "attributes": {}}}
        args = MagicMock(amount="5", source="A", dest="B", desc=None, date=None,
                         category="Brand New Cat", tags=None, type="withdrawal")
        tx.cmd_add(args, ctx)
        split = client.request.call_args[1]["body"]["transactions"][0]
        self.assertEqual(split["category_name"], "Brand New Cat")
        resolver.category.assert_not_called()

class TestTxList(unittest.TestCase):
    def test_list_passes_date_params(self):
        ctx, client, _ = make_ctx()
        client.request.return_value = {"data": []}
        args = MagicMock(since="2026-06-01", until="2026-06-30",
                         account=None, limit=10)
        tx.cmd_list(args, ctx)
        params = client.request.call_args[1]["params"]
        self.assertEqual(params["start"], "2026-06-01")
        self.assertEqual(params["end"], "2026-06-30")
        self.assertEqual(params["limit"], 10)
