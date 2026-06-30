import unittest
from unittest.mock import MagicMock
from firefly_cli.commands import account as acct
from firefly_cli.context import Context

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
        args = MagicMock(account="Checking")
        rc = acct.cmd_balance(args, ctx)
        resolver.account.assert_called_once_with("Checking")
        self.assertEqual(rc, 0)
