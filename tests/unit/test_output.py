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
