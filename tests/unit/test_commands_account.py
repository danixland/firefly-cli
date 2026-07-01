import unittest
from unittest.mock import MagicMock
from firefly_cli.commands import account as acct
from firefly_cli.context import Context
from firefly_cli.errors import FireflyError

def make_ctx():
    client = MagicMock()
    resolver = MagicMock()
    return Context(client=client, resolver=resolver, human=False), client, resolver

class TestAccountCmd(unittest.TestCase):
    def test_list_passes_type_filter(self):
        ctx, client, _ = make_ctx()
        client.request.return_value = {"data": []}
        args = MagicMock(type="asset")
        acct.cmd_list(args, ctx)
        client.request.assert_called_once_with(
            "GET", "/api/v1/accounts", params={"type": "asset"})

    def test_balance_resolves_name_and_returns_balance(self):
        ctx, client, resolver = make_ctx()
        resolver.account.return_value = {"id": "3", "name": "Checking",
                                         "current_balance": "100.00"}
        args = MagicMock(account="Checking", at=None)
        rc = acct.cmd_balance(args, ctx)
        resolver.account.assert_called_once_with("Checking")
        client.request.assert_not_called()  # current balance from resolver, no extra call
        self.assertEqual(rc, 0)

    def test_balance_at_date_fetches_dated_account(self):
        ctx, client, resolver = make_ctx()
        resolver.account.return_value = {"id": "3", "name": "Checking",
                                         "current_balance": "100.00"}
        client.request.return_value = {"data": {"id": "3", "attributes": {
            "name": "Checking", "current_balance": "42.00"}}}
        args = MagicMock(account="Checking", at="2026-05-31")
        rc = acct.cmd_balance(args, ctx)
        self.assertEqual(rc, 0)
        method, path = client.request.call_args[0][:2]
        self.assertEqual((method, path), ("GET", "/api/v1/accounts/3"))
        self.assertEqual(client.request.call_args[1]["params"], {"date": "2026-05-31"})

class TestAccountCreate(unittest.TestCase):
    def _args(self, **kw):
        base = dict(name=None, type=None, opening_balance=None, currency=None,
                    if_not_exists=False)
        base.update(kw)
        m = MagicMock()
        m.configure_mock(**base)  # 'name' is reserved in MagicMock ctor, not configure_mock
        return m

    def test_asset_posts_with_default_role(self):
        ctx, client, _ = make_ctx()
        client.request.return_value = {"data": {"id": "9", "attributes": {}}}
        rc = acct.cmd_create(self._args(name="Savings", type="asset"), ctx)
        self.assertEqual(rc, 0)
        method, path = client.request.call_args[0][:2]
        body = client.request.call_args[1]["body"]
        self.assertEqual((method, path), ("POST", "/api/v1/accounts"))
        self.assertEqual(body["name"], "Savings")
        self.assertEqual(body["type"], "asset")
        self.assertEqual(body["account_role"], "defaultAsset")

    def test_expense_has_no_role(self):
        ctx, client, _ = make_ctx()
        client.request.return_value = {"data": {"id": "9", "attributes": {}}}
        acct.cmd_create(self._args(name="Rent", type="expense"), ctx)
        body = client.request.call_args[1]["body"]
        self.assertNotIn("account_role", body)

    def test_opening_balance_adds_date(self):
        ctx, client, _ = make_ctx()
        client.request.return_value = {"data": {"id": "9", "attributes": {}}}
        acct.cmd_create(
            self._args(name="Savings", type="asset", opening_balance="500"), ctx)
        body = client.request.call_args[1]["body"]
        self.assertEqual(body["opening_balance"], "500")
        self.assertIn("opening_balance_date", body)  # required_with by Firefly

    def test_currency_passed_through(self):
        ctx, client, _ = make_ctx()
        client.request.return_value = {"data": {"id": "9", "attributes": {}}}
        acct.cmd_create(
            self._args(name="Savings", type="asset", currency="EUR"), ctx)
        self.assertEqual(client.request.call_args[1]["body"]["currency_code"], "EUR")

    def test_bad_type_is_hard_error_no_request(self):
        ctx, client, _ = make_ctx()
        with self.assertRaises(FireflyError):
            acct.cmd_create(self._args(name="X", type="bogus"), ctx)
        client.request.assert_not_called()

    def test_if_not_exists_returns_existing_no_post(self):
        ctx, client, resolver = make_ctx()
        resolver.account.return_value = {"id": "5", "name": "Savings",
                                         "type": "asset"}
        rc = acct.cmd_create(
            self._args(name="Savings", type="asset", if_not_exists=True), ctx)
        self.assertEqual(rc, 0)
        resolver.account.assert_called_once_with("Savings")
        client.request.assert_not_called()  # existed -> no create

    def test_if_not_exists_creates_when_missing(self):
        from firefly_cli.errors import ResolutionError
        ctx, client, resolver = make_ctx()
        resolver.account.side_effect = ResolutionError('No account named "Savings"')
        client.request.return_value = {"data": {"id": "9", "attributes": {}}}
        rc = acct.cmd_create(
            self._args(name="Savings", type="asset", if_not_exists=True), ctx)
        self.assertEqual(rc, 0)
        method, path = client.request.call_args[0][:2]
        self.assertEqual((method, path), ("POST", "/api/v1/accounts"))

    def test_if_not_exists_emits_existed_flag(self):
        import io, json
        from contextlib import redirect_stdout
        ctx, client, resolver = make_ctx()
        resolver.account.return_value = {"id": "5", "name": "Savings"}
        buf = io.StringIO()
        with redirect_stdout(buf):
            acct.cmd_create(
                self._args(name="Savings", type="asset", if_not_exists=True), ctx)
        self.assertEqual(json.loads(buf.getvalue()),
                         {"id": "5", "name": "Savings", "existed": True})
