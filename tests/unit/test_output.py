import io, json, unittest
from contextlib import redirect_stdout
from firefly_cli.output import unwrap, emit

class TestOutput(unittest.TestCase):
    def test_unwrap_list_returns_clean_objects(self):
        resp = {"data": [
            {"id": "1", "type": "accounts", "attributes": {"name": "Checking"}},
            {"id": "2", "type": "accounts", "attributes": {"name": "Savings"}},
        ]}
        self.assertEqual(unwrap(resp),
            [{"id": "1", "name": "Checking"}, {"id": "2", "name": "Savings"}])

    def test_unwrap_single_object(self):
        resp = {"data": {"id": "5", "type": "accounts",
                         "attributes": {"name": "Wallet"}}}
        self.assertEqual(unwrap(resp), {"id": "5", "name": "Wallet"})

    def test_emit_json_default(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            emit([{"id": "1", "name": "x"}], human=False)
        self.assertEqual(json.loads(buf.getvalue()), [{"id": "1", "name": "x"}])

    def test_emit_human_table_contains_values(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            emit([{"id": "1", "name": "Checking"}], human=True)
        out = buf.getvalue()
        self.assertIn("Checking", out)
        self.assertIn("id", out)

    def test_emit_human_drops_nested_columns(self):
        # dict/list-valued fields would dump unreadable blobs; they must be cut.
        buf = io.StringIO()
        with redirect_stdout(buf):
            emit([{"id": "1", "name": "x", "junk": {"a": 1}, "tags": [1, 2]}],
                 human=True)
        out = buf.getvalue()
        self.assertIn("name", out)
        self.assertNotIn("junk", out)
        self.assertNotIn("tags", out)

    def test_emit_human_transaction_flattens_splits(self):
        # The useful fields live in the nested `transactions` split list, and the
        # raw 12-decimal amount should be trimmed to 2 dp.
        tx = {"id": "77", "transactions": [{
            "type": "withdrawal", "date": "2026-06-28T00:00:00+02:00",
            "amount": "7.400000000000", "currency_code": "EUR",
            "description": "McDonald", "source_name": "BBVA",
            "destination_name": "McDonald's", "category_name": "Food"}]}
        buf = io.StringIO()
        with redirect_stdout(buf):
            emit([tx], human=True)
        out = buf.getvalue()
        self.assertIn("28/06/2026", out)        # Italian date, no time/zone
        self.assertIn("7.40", out)              # amount trimmed to 2 dp
        self.assertNotIn("7.400000", out)
        self.assertIn("McDonald's", out)        # destination surfaced
        self.assertIn("Food", out)
        self.assertNotIn("import_hash", out)    # raw blob not dumped

    def test_emit_color_only_on_tty(self):
        tx = {"id": "1", "transactions": [{"type": "withdrawal",
              "date": "2026-06-28", "amount": "1", "currency_code": "EUR",
              "description": "x", "source_name": "a", "destination_name": "b",
              "category_name": "c"}]}
        plain = io.StringIO()
        emit([tx], human=True, stream=plain)
        self.assertNotIn("\033[", plain.getvalue())  # piped: no ANSI

        class TTY(io.StringIO):
            def isatty(self):
                return True
        tty = TTY()
        emit([tx], human=True, stream=tty)
        self.assertIn("\033[31m", tty.getvalue())    # tty: withdrawal is red

    def _emit(self, row):
        buf = io.StringIO()
        emit([row], human=True, stream=buf)
        return buf.getvalue()

    def test_view_account_shows_balance_drops_plumbing(self):
        # account_role signature -> the account view.
        out = self._emit({"id": "6", "name": "BBVA", "type": "asset",
                          "account_role": "defaultAsset",
                          "current_balance": "1590.92", "currency_code": "EUR",
                          "active": True, "iban": "IT68...", "notes": "secret"})
        self.assertIn("BBVA", out)
        self.assertIn("1590.92", out)
        self.assertIn("currency_code", out)
        self.assertNotIn("iban", out)        # plumbing column dropped
        self.assertNotIn("secret", out)

    def test_view_tag(self):
        out = self._emit({"id": "9", "tag": "2026", "description": "yr",
                          "zoom_level": None, "latitude": None})
        self.assertIn("2026", out)
        self.assertIn("description", out)
        self.assertNotIn("zoom_level", out)

    def test_view_account_balance(self):
        # The balance handler emits id+name+current_balance (no account_role).
        out = self._emit({"id": "6", "name": "BBVA",
                          "current_balance": "1590.92"})
        self.assertIn("current_balance", out)
        self.assertIn("1590.92", out)

    def test_view_category_name_only(self):
        out = self._emit({"id": "2", "name": "Food", "spent": [],
                          "primary_currency_code": "EUR", "notes": "junk"})
        self.assertIn("Food", out)
        self.assertNotIn("primary_currency_code", out)
        self.assertNotIn("spent", out)
