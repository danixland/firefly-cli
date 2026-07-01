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
                         tags=None, type=None, dry_run=False, skip_dupes=False)
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
                         desc="pay", date=None, category=None, tags=None,
                         type=None, dry_run=False, skip_dupes=False)
        tx.cmd_add(args, ctx)
        self.assertEqual(client.request.call_args[1]["body"]["transactions"][0]["type"],
                         "deposit")

    def test_explicit_type_overrides_inference(self):
        ctx, client, resolver = make_ctx()
        resolver.account.side_effect = lambda n: {"id": "1", "type": "asset", "name": n}
        client.request.return_value = {"data": {"id": "1", "attributes": {}}}
        args = MagicMock(amount="5", source="A", dest="B", desc=None, date=None,
                         category=None, tags="food,fun", type="transfer",
                         dry_run=False, skip_dupes=False)
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
                         category="Brand New Cat", tags=None, type="withdrawal",
                         dry_run=False, skip_dupes=False)
        tx.cmd_add(args, ctx)
        split = client.request.call_args[1]["body"]["transactions"][0]
        self.assertEqual(split["category_name"], "Brand New Cat")

    def test_dry_run_resolves_but_does_not_post(self):
        ctx, client, resolver = make_ctx()
        resolver.account.side_effect = lambda n: {"id": "1", "type": "asset", "name": n}
        args = MagicMock(amount="5", source="A", dest="B", desc="x", date="2026-06-01",
                         category=None, tags=None, type="withdrawal", dry_run=True, skip_dupes=False)
        rc = tx.cmd_add(args, ctx)
        self.assertEqual(rc, 0)
        client.request.assert_not_called()  # accounts resolved, nothing written
        self.assertEqual(resolver.account.call_count, 2)

    def test_dry_run_missing_account_is_hard_error(self):
        from firefly_cli.errors import ResolutionError
        ctx, client, resolver = make_ctx()
        resolver.account.side_effect = ResolutionError('No account named "B"')
        args = MagicMock(amount="5", source="A", dest="B", desc=None, date=None,
                         category=None, tags=None, type="withdrawal", dry_run=True, skip_dupes=False)
        with self.assertRaises(ResolutionError):
            tx.cmd_add(args, ctx)
        client.request.assert_not_called()
        resolver.category.assert_not_called()

    def test_skip_dupes_skips_when_match_exists(self):
        ctx, client, resolver = make_ctx()
        resolver.account.side_effect = lambda n: {
            "A": {"id": "1", "name": "A", "type": "asset"},
            "B": {"id": "2", "name": "B", "type": "expense"},
        }[n]
        # search finds an existing tx -> skip, no POST
        client.request.return_value = {"data": [
            {"id": "441", "attributes": {}}]}
        args = MagicMock(amount="9.99", source="A", dest="B", desc="x",
                         date="2026-06-10", category=None, tags=None,
                         type=None, dry_run=False, skip_dupes=True)
        rc = tx.cmd_add(args, ctx)
        self.assertEqual(rc, 0)
        # exactly one call, the GET search; no POST
        self.assertEqual(client.request.call_count, 1)
        method, path = client.request.call_args[0][:2]
        self.assertEqual(method, "GET")
        q = client.request.call_args[1]["params"]["query"]
        self.assertIn("amount_is:9.99", q)
        self.assertIn("date_on:2026-06-10", q)
        self.assertIn("source_account_is:", q)
        self.assertIn("destination_account_is:", q)

    def test_skip_dupes_writes_when_no_match(self):
        ctx, client, resolver = make_ctx()
        resolver.account.side_effect = lambda n: {
            "A": {"id": "1", "name": "A", "type": "asset"},
            "B": {"id": "2", "name": "B", "type": "expense"},
        }[n]
        # first call = search (empty), second = POST
        client.request.side_effect = [
            {"data": []},
            {"data": {"id": "99", "attributes": {}}},
        ]
        args = MagicMock(amount="9.99", source="A", dest="B", desc="x",
                         date="2026-06-10", category=None, tags=None,
                         type=None, dry_run=False, skip_dupes=True)
        rc = tx.cmd_add(args, ctx)
        self.assertEqual(rc, 0)
        self.assertEqual(client.request.call_count, 2)
        self.assertEqual(client.request.call_args[0][:2],
                         ("POST", "/api/v1/transactions"))

    def test_dry_run_beats_skip_dupes_no_search(self):
        ctx, client, resolver = make_ctx()
        resolver.account.side_effect = lambda n: {"id": "1", "type": "asset", "name": n}
        args = MagicMock(amount="5", source="A", dest="B", desc=None, date="2026-06-01",
                         category=None, tags=None, type="withdrawal",
                         dry_run=True, skip_dupes=True)
        rc = tx.cmd_add(args, ctx)
        self.assertEqual(rc, 0)
        client.request.assert_not_called()  # dry-run wins: no search, no write

class TestTxEdit(unittest.TestCase):
    def test_edit_sends_only_provided_fields(self):
        ctx, client, resolver = make_ctx()
        client.request.return_value = {"data": {"id": "9", "attributes": {}}}
        args = MagicMock(id="9", amount="12.00", date=None, desc="fixed",
                         source=None, dest=None, category=None, tags=None, type=None)
        rc = tx.cmd_edit(args, ctx)
        self.assertEqual(rc, 0)
        method, path = client.request.call_args[0][:2]
        split = client.request.call_args[1]["body"]["transactions"][0]
        self.assertEqual((method, path), ("PUT", "/api/v1/transactions/9"))
        self.assertEqual(split, {"amount": "12.00", "description": "fixed"})
        resolver.account.assert_not_called()

    def test_edit_resolves_accounts_when_given(self):
        ctx, client, resolver = make_ctx()
        resolver.account.side_effect = lambda n: {
            "BBVA": {"id": "3", "name": "BBVA", "type": "asset"},
            "Medio": {"id": "4", "name": "Medio", "type": "asset"},
        }[n]
        client.request.return_value = {"data": {"id": "9", "attributes": {}}}
        args = MagicMock(id="9", amount=None, date=None, desc=None,
                         source="BBVA", dest="Medio", category=None, tags=None, type=None)
        tx.cmd_edit(args, ctx)
        split = client.request.call_args[1]["body"]["transactions"][0]
        self.assertEqual(split, {"source_id": "3", "destination_id": "4"})

    def test_edit_category_raw_and_tags_split(self):
        ctx, client, resolver = make_ctx()
        client.request.return_value = {"data": {"id": "9", "attributes": {}}}
        args = MagicMock(id="9", amount=None, date=None, desc=None, source=None,
                         dest=None, category="Cat", tags="a, b", type="transfer")
        tx.cmd_edit(args, ctx)
        split = client.request.call_args[1]["body"]["transactions"][0]
        self.assertEqual(split,
                         {"category_name": "Cat", "tags": ["a", "b"], "type": "transfer"})
        resolver.category.assert_not_called()

    def test_edit_with_no_fields_errors(self):
        from firefly_cli.errors import FireflyError
        ctx, client, _ = make_ctx()
        args = MagicMock(id="9", amount=None, date=None, desc=None, source=None,
                         dest=None, category=None, tags=None, type=None)
        with self.assertRaises(FireflyError):
            tx.cmd_edit(args, ctx)
        client.request.assert_not_called()


class TestTxDelete(unittest.TestCase):
    def test_delete_requires_yes(self):
        from firefly_cli.errors import FireflyError
        ctx, client, _ = make_ctx()
        args = MagicMock(id="9", yes=False)
        with self.assertRaises(FireflyError):
            tx.cmd_delete(args, ctx)
        client.request.assert_not_called()

    def test_delete_with_yes(self):
        ctx, client, _ = make_ctx()
        client.request.return_value = {}
        args = MagicMock(id="9", yes=True)
        rc = tx.cmd_delete(args, ctx)
        self.assertEqual(rc, 0)
        method, path = client.request.call_args[0][:2]
        self.assertEqual((method, path), ("DELETE", "/api/v1/transactions/9"))


class TestTxList(unittest.TestCase):
    def test_list_passes_date_params(self):
        ctx, client, _ = make_ctx()
        client.request.return_value = {"data": []}
        args = MagicMock(since="2026-06-01", until="2026-06-30",
                         account=None, limit=10, all=False)
        tx.cmd_list(args, ctx)
        params = client.request.call_args[1]["params"]
        self.assertEqual(params["start"], "2026-06-01")
        self.assertEqual(params["end"], "2026-06-30")
        self.assertEqual(params["limit"], 10)

    def test_list_warns_when_truncated(self):
        import io
        from contextlib import redirect_stderr
        ctx, client, _ = make_ctx()
        client.request.return_value = {
            "data": [{"id": str(i)} for i in range(20)],
            "meta": {"pagination": {"total": 90, "count": 20,
                                    "current_page": 1, "total_pages": 5}},
        }
        args = MagicMock(since=None, until=None, account=None, limit=20, all=False)
        buf = io.StringIO()
        with redirect_stderr(buf):
            tx.cmd_list(args, ctx)
        self.assertIn("showing 20 of 90", buf.getvalue())
        self.assertEqual(client.request.call_count, 1)

    def test_list_no_warn_when_complete(self):
        import io
        from contextlib import redirect_stderr
        ctx, client, _ = make_ctx()
        client.request.return_value = {
            "data": [{"id": "1"}],
            "meta": {"pagination": {"total": 1, "count": 1,
                                    "current_page": 1, "total_pages": 1}},
        }
        args = MagicMock(since=None, until=None, account=None, limit=20, all=False)
        buf = io.StringIO()
        with redirect_stderr(buf):
            tx.cmd_list(args, ctx)
        self.assertEqual(buf.getvalue(), "")

    def test_list_all_paginates(self):
        ctx, client, _ = make_ctx()
        def page(method, path, params=None, body=None):
            p = params["page"]
            return {
                "data": [{"id": f"{p}-{i}"} for i in range(2)],
                "meta": {"pagination": {"total": 4, "count": 2,
                                        "current_page": p, "total_pages": 2}},
            }
        client.request.side_effect = page
        args = MagicMock(since=None, until=None, account=None, limit=2, all=True)
        rc = tx.cmd_list(args, ctx)
        self.assertEqual(rc, 0)
        self.assertEqual(client.request.call_count, 2)
