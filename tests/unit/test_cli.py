import unittest
from unittest.mock import patch, MagicMock
from firefly_cli import cli

class TestCli(unittest.TestCase):
    @patch("firefly_cli.cli.config.load")
    @patch("firefly_cli.cli.Client")
    def test_dispatches_account_list(self, Client, load):
        load.return_value = {"url": "https://f", "token": "t"}
        Client.return_value.request.return_value = {"data": []}
        rc = cli.main(["account", "list"])
        self.assertEqual(rc, 0)

    @patch("firefly_cli.cli.config.load")
    def test_config_error_returns_nonzero(self, load):
        from firefly_cli.errors import ConfigError
        load.side_effect = ConfigError("no config")
        rc = cli.main(["account", "list"])
        self.assertEqual(rc, 1)

    def test_auth_set_does_not_require_config(self):
        # auth set must run even with no config/client
        with patch("firefly_cli.cli.config.write") as w:
            w.return_value = "/tmp/x"
            rc = cli.main(["auth", "set", "--url", "https://f", "--token", "t"])
        self.assertEqual(rc, 0)
