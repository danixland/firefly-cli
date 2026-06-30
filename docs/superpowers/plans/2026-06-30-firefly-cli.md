# firefly-cli Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A Python-package CLI (`firefly`) that lets an LLM agent and the user record and query a Firefly III instance over its REST API.

**Architecture:** A `firefly_cli` package with shared primitives (config, HTTP client, name resolver, output) and a self-registering command registry. Each command group is one module in `firefly_cli/commands/`; dropping a module in adds commands with no other edits. JSON output by default, `--human` for tables.

**Tech Stack:** Python 3.11+ standard library only (`urllib.request`, `json`, `tomllib`, `argparse`, `unittest`). No third-party runtime deps. License GPLv2-only.

---

## Reference facts (verified against the cloned firefly-iii codebase, read-only)

- API base path: `/api/v1`. About endpoint: `GET /api/v1/about` returns `{"data":{"version":...,"api_version":...}}`.
- Auth: `Authorization: Bearer <PAT>`. Accept header `application/vnd.api+json`.
- Account types (enum string values): `Asset account`, `Expense account`,
  `Revenue account`, `Liability credit account`, `Loan`, `Mortgage`, `Debt`,
  `Cash account`, etc. The API `accounts` list accepts a `type` query filter
  with short names: `asset`, `expense`, `revenue`, `liability`, etc.
- Account resource fields include: `id`, `name`, `type`, `current_balance`,
  `currency_code`. (AccountTransformer, verified.)
- Transaction store body shape:
  `{"transactions":[{ "type", "date", "amount", "description",
  "source_id", "destination_id", "category_name", "tags": [...] }]}`.
  Source/destination accept `_id` or `_name`; we send `_id` (resolved). Fields
  verified in StoreRequest rules.
- Transaction reads use TransactionGroupTransformer (a group wraps one or more
  splits). List/collection responses are Fractal-serialized:
  `{"data":[...], "meta":{"pagination":{...}}, "links":{...}}`.

**Executor note:** the exact list envelope and the precise `current_balance`
field name are confirmed live by the integration tests in Task 11. Until then,
unit tests use the documented shapes above. If a live shape differs, update the
unwrap logic and its unit test together.

---

## File Structure

- `firefly_cli/__init__.py` — version, package marker.
- `firefly_cli/config.py` — load (env over TOML file), template-write.
- `firefly_cli/client.py` — `Client` with `request()`, auth headers, error surfacing.
- `firefly_cli/errors.py` — exception types shared across modules.
- `firefly_cli/output.py` — `emit()` JSON/human, `unwrap()` envelope helper.
- `firefly_cli/resolver.py` — `Resolver` name→id with ambiguity errors.
- `firefly_cli/registry.py` — command registry (decorator + list).
- `firefly_cli/cli.py` — builds argparse from registry, `main()`, builds `Context`.
- `firefly_cli/context.py` — `Context` dataclass bundling config/client/resolver + flags.
- `firefly_cli/commands/__init__.py` — imports each command module so they register.
- `firefly_cli/commands/auth.py`, `account.py`, `transaction.py`, `category.py`, `tag.py`.
- `firefly_cli/__main__.py` — `python -m firefly_cli`.
- `tests/unit/test_*.py` — mocked, always run.
- `tests/integration/test_live.py` — gated by `FIREFLY_TEST_URL`/`FIREFLY_TEST_TOKEN`.
- `pyproject.toml`, `LICENSE`, `README.md`, `CLAUDE.md`.

---

## Task 1: Project scaffold, license, CLAUDE.md

**Files:**
- Create: `pyproject.toml`, `LICENSE`, `README.md`, `CLAUDE.md`,
  `firefly_cli/__init__.py`, `firefly_cli/__main__.py`, `.gitignore`

- [ ] **Step 1: Fetch GPLv2 license text**

Run:
```bash
curl -fsSL https://www.gnu.org/licenses/old-licenses/gpl-2.0.txt -o LICENSE
head -2 LICENSE
```
Expected: prints the GPLv2 preamble lines. If offline, executor must obtain the
official text before committing.

- [ ] **Step 2: Write `pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=61"]
build-backend = "setuptools.build_meta"

[project]
name = "firefly-cli"
version = "0.1.0"
description = "CLI tool for agent interaction with Firefly III"
requires-python = ">=3.11"
license = { text = "GPL-2.0-only" }
authors = [{ name = "Danilo M.", email = "danix@danix.xyz" }]
dependencies = []

[project.scripts]
firefly = "firefly_cli.cli:main"

[tool.setuptools.packages.find]
include = ["firefly_cli*"]
```

- [ ] **Step 3: Write `firefly_cli/__init__.py`**

```python
# firefly-cli — CLI for Firefly III
# Copyright (C) 2026 Danilo M. <danix@danix.xyz>
# Licensed under the GNU General Public License v2.0 only.

__version__ = "0.1.0"
```

- [ ] **Step 4: Write `firefly_cli/__main__.py`**

```python
# Copyright (C) 2026 Danilo M. <danix@danix.xyz>  GPL-2.0-only
from firefly_cli.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Write `.gitignore`**

```
__pycache__/
*.pyc
*.egg-info/
build/
dist/
.venv/
```

- [ ] **Step 6: Write `README.md`** (sections: what it is, install
  `pip install -e .`, config via `firefly auth set` or env vars, command list
  placeholder pointing at `firefly --help`, License = GPLv2-only).

- [ ] **Step 7: Write `CLAUDE.md`** — see Appendix A at the end of this plan for
  full content. Copy it verbatim.

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml LICENSE README.md CLAUDE.md firefly_cli/__init__.py firefly_cli/__main__.py .gitignore
git commit -S -m "chore: project scaffold, GPLv2 license, CLAUDE.md"
```

---

## Task 2: Errors module

**Files:**
- Create: `firefly_cli/errors.py`
- Test: `tests/unit/test_errors.py`

- [ ] **Step 1: Write the failing test**

```python
import unittest
from firefly_cli.errors import FireflyError, ConfigError, ApiError, ResolutionError

class TestErrors(unittest.TestCase):
    def test_subclassing(self):
        for cls in (ConfigError, ApiError, ResolutionError):
            self.assertTrue(issubclass(cls, FireflyError))

    def test_api_error_carries_status_and_body(self):
        e = ApiError(422, {"message": "bad"})
        self.assertEqual(e.status, 422)
        self.assertEqual(e.body, {"message": "bad"})
        self.assertIn("422", str(e))

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test, verify it fails**

Run: `python -m unittest tests.unit.test_errors -v`
Expected: FAIL, `ModuleNotFoundError: firefly_cli.errors`.

- [ ] **Step 3: Write `firefly_cli/errors.py`**

```python
# Copyright (C) 2026 Danilo M. <danix@danix.xyz>  GPL-2.0-only

class FireflyError(Exception):
    """Base for all firefly-cli errors."""

class ConfigError(FireflyError):
    """Missing or invalid configuration."""

class ResolutionError(FireflyError):
    """A name could not be resolved to a single id."""

class ApiError(FireflyError):
    """Firefly returned a non-2xx response."""
    def __init__(self, status, body):
        self.status = status
        self.body = body
        msg = body.get("message") if isinstance(body, dict) else body
        super().__init__(f"API error {status}: {msg}")
```

- [ ] **Step 4: Run test, verify it passes**

Run: `python -m unittest tests.unit.test_errors -v`
Expected: PASS (add empty `tests/__init__.py`, `tests/unit/__init__.py` if needed).

- [ ] **Step 5: Commit**

```bash
git add firefly_cli/errors.py tests/
git commit -S -m "feat: error types"
```

---

## Task 3: Config (env over TOML file, template write)

**Files:**
- Create: `firefly_cli/config.py`
- Test: `tests/unit/test_config.py`

- [ ] **Step 1: Write the failing test**

```python
import os, tempfile, unittest
from pathlib import Path
from firefly_cli import config
from firefly_cli.errors import ConfigError

class TestConfig(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = Path(self.dir.name) / "config.toml"
    def tearDown(self):
        self.dir.cleanup()
        for k in ("FIREFLY_URL", "FIREFLY_TOKEN"):
            os.environ.pop(k, None)

    def test_write_then_read_roundtrip(self):
        config.write("https://f.example/", "tok123", path=self.path)
        cfg = config.load(path=self.path, env={})
        self.assertEqual(cfg["url"], "https://f.example")  # trailing slash trimmed
        self.assertEqual(cfg["token"], "tok123")

    def test_env_overrides_file(self):
        config.write("https://file/", "filetok", path=self.path)
        cfg = config.load(path=self.path,
                          env={"FIREFLY_URL": "https://env", "FIREFLY_TOKEN": "envtok"})
        self.assertEqual(cfg["url"], "https://env")
        self.assertEqual(cfg["token"], "envtok")

    def test_missing_everything_raises_configerror(self):
        with self.assertRaises(ConfigError):
            config.load(path=self.path, env={})

    def test_env_only_no_file(self):
        cfg = config.load(path=self.path,
                          env={"FIREFLY_URL": "https://env/", "FIREFLY_TOKEN": "t"})
        self.assertEqual(cfg["url"], "https://env")
```

- [ ] **Step 2: Run test, verify it fails**

Run: `python -m unittest tests.unit.test_config -v`
Expected: FAIL, no module/attr.

- [ ] **Step 3: Write `firefly_cli/config.py`**

```python
# Copyright (C) 2026 Danilo M. <danix@danix.xyz>  GPL-2.0-only
import os
import tomllib
from pathlib import Path
from firefly_cli.errors import ConfigError

DEFAULT_PATH = Path(os.path.expanduser("~/.config/firefly-cli/config.toml"))

def load(path=DEFAULT_PATH, env=None):
    env = os.environ if env is None else env
    url = env.get("FIREFLY_URL")
    token = env.get("FIREFLY_TOKEN")
    if not (url and token) and Path(path).exists():
        with open(path, "rb") as fh:
            data = tomllib.load(fh)
        url = url or data.get("url")
        token = token or data.get("token")
    if not url or not token:
        raise ConfigError(
            "No Firefly III config found. Run `firefly auth set` "
            "or set FIREFLY_URL and FIREFLY_TOKEN."
        )
    return {"url": url.rstrip("/"), "token": token}

def write(url, token, path=DEFAULT_PATH):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # tomllib cannot write; template the 2-key file (deps stay at zero).
    content = (
        f'url = "{url.rstrip("/")}"\n'
        f'token = "{token}"\n'
    )
    path.write_text(content)
    path.chmod(0o600)
    return path
```

- [ ] **Step 4: Run test, verify it passes**

Run: `python -m unittest tests.unit.test_config -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add firefly_cli/config.py tests/unit/test_config.py
git commit -S -m "feat: config load/write with env override"
```

---

## Task 4: HTTP client

**Files:**
- Create: `firefly_cli/client.py`
- Test: `tests/unit/test_client.py`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test, verify it fails**

Run: `python -m unittest tests.unit.test_client -v`
Expected: FAIL, no module.

- [ ] **Step 3: Write `firefly_cli/client.py`**

```python
# Copyright (C) 2026 Danilo M. <danix@danix.xyz>  GPL-2.0-only
import json
import urllib.request
import urllib.parse
import urllib.error
from firefly_cli.errors import ApiError

class Client:
    def __init__(self, url, token, timeout=30):
        self.url = url.rstrip("/")
        self.token = token
        self.timeout = timeout

    def request(self, method, path, params=None, body=None):
        full = self.url + path
        if params:
            full += "?" + urllib.parse.urlencode(params)
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(full, data=data, method=method)
        req.add_header("Authorization", f"Bearer {self.token}")
        req.add_header("Accept", "application/vnd.api+json")
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            raw = e.read().decode()
            try:
                parsed = json.loads(raw)
            except ValueError:
                parsed = {"message": raw or e.reason}
            raise ApiError(e.code, parsed) from None
```

- [ ] **Step 4: Run test, verify it passes**

Run: `python -m unittest tests.unit.test_client -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add firefly_cli/client.py tests/unit/test_client.py
git commit -S -m "feat: HTTP client with auth and error surfacing"
```

---

## Task 5: Output (emit + unwrap)

**Files:**
- Create: `firefly_cli/output.py`
- Test: `tests/unit/test_output.py`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test, verify it fails**

Run: `python -m unittest tests.unit.test_output -v`
Expected: FAIL, no module.

- [ ] **Step 3: Write `firefly_cli/output.py`**

```python
# Copyright (C) 2026 Danilo M. <danix@danix.xyz>  GPL-2.0-only
import json
import sys

def unwrap(resp):
    """Flatten Firefly's JSON:API envelope to plain id+attributes objects."""
    def flat(item):
        out = {"id": item.get("id")}
        out.update(item.get("attributes", {}))
        return out
    data = resp.get("data", resp)
    if isinstance(data, list):
        return [flat(i) for i in data]
    if isinstance(data, dict) and "attributes" in data:
        return flat(data)
    return data

def emit(data, human=False, stream=None):
    stream = stream or sys.stdout
    if not human:
        json.dump(data, stream, indent=2, default=str)
        stream.write("\n")
        return
    rows = data if isinstance(data, list) else [data]
    if not rows:
        stream.write("(no results)\n")
        return
    cols = list(rows[0].keys())
    widths = {c: max(len(c), *(len(str(r.get(c, ""))) for r in rows)) for c in cols}
    stream.write("  ".join(c.ljust(widths[c]) for c in cols) + "\n")
    for r in rows:
        stream.write("  ".join(str(r.get(c, "")).ljust(widths[c]) for c in cols) + "\n")

def emit_error(message, stream=None):
    stream = stream or sys.stderr
    json.dump({"error": message}, stream)
    stream.write("\n")
```

- [ ] **Step 4: Run test, verify it passes**

Run: `python -m unittest tests.unit.test_output -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add firefly_cli/output.py tests/unit/test_output.py
git commit -S -m "feat: output emit and envelope unwrap"
```

---

## Task 6: Registry + Context

**Files:**
- Create: `firefly_cli/registry.py`, `firefly_cli/context.py`
- Test: `tests/unit/test_registry.py`

- [ ] **Step 1: Write the failing test**

```python
import unittest
from firefly_cli import registry

class TestRegistry(unittest.TestCase):
    def setUp(self):
        registry._COMMANDS.clear()

    def test_command_decorator_registers(self):
        @registry.command("tx add", help="add a tx")
        def handler(args, ctx):
            return 0
        cmds = registry.all_commands()
        self.assertEqual(len(cmds), 1)
        self.assertEqual(cmds[0].name, "tx add")
        self.assertIs(cmds[0].handler, handler)

    def test_add_arguments_callback_stored(self):
        def args_cb(p):
            p.add_argument("name")
        @registry.command("account get", args=args_cb)
        def handler(args, ctx):
            return 0
        self.assertIs(registry.all_commands()[0].args, args_cb)
```

- [ ] **Step 2: Run test, verify it fails**

Run: `python -m unittest tests.unit.test_registry -v`
Expected: FAIL, no module.

- [ ] **Step 3: Write `firefly_cli/registry.py`**

```python
# Copyright (C) 2026 Danilo M. <danix@danix.xyz>  GPL-2.0-only
from dataclasses import dataclass
from typing import Callable, Optional

@dataclass
class Command:
    name: str            # e.g. "tx add"
    handler: Callable     # fn(args, ctx) -> int
    help: str = ""
    args: Optional[Callable] = None   # fn(argparse_subparser) -> None

_COMMANDS = []

def command(name, help="", args=None):
    def deco(fn):
        _COMMANDS.append(Command(name=name, handler=fn, help=help, args=args))
        return fn
    return deco

def all_commands():
    return list(_COMMANDS)
```

- [ ] **Step 4: Write `firefly_cli/context.py`**

```python
# Copyright (C) 2026 Danilo M. <danix@danix.xyz>  GPL-2.0-only
from dataclasses import dataclass

@dataclass
class Context:
    client: object        # firefly_cli.client.Client
    resolver: object      # firefly_cli.resolver.Resolver
    human: bool = False
```

- [ ] **Step 5: Run test, verify it passes**

Run: `python -m unittest tests.unit.test_registry -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add firefly_cli/registry.py firefly_cli/context.py tests/unit/test_registry.py
git commit -S -m "feat: command registry and context"
```

---

## Task 7: Resolver (name -> id)

**Files:**
- Create: `firefly_cli/resolver.py`
- Test: `tests/unit/test_resolver.py`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test, verify it fails**

Run: `python -m unittest tests.unit.test_resolver -v`
Expected: FAIL, no module.

- [ ] **Step 3: Write `firefly_cli/resolver.py`**

```python
# Copyright (C) 2026 Danilo M. <danix@danix.xyz>  GPL-2.0-only
from firefly_cli.errors import ResolutionError

class Resolver:
    def __init__(self, client):
        self.client = client

    def _list(self, path):
        resp = self.client.request("GET", path, params={"limit": 1000})
        out = []
        for item in resp.get("data", []):
            attrs = item.get("attributes", {})
            out.append({"id": item.get("id"), **attrs})
        return out

    def _match(self, kind, items, name):
        hits = [i for i in items if str(i.get("name", "")).lower() == name.lower()]
        if len(hits) == 1:
            return hits[0]
        names = ", ".join(f'{i.get("name")}(id={i.get("id")})' for i in items)
        if not hits:
            raise ResolutionError(
                f'No {kind} named "{name}". Available: {names or "(none)"}')
        raise ResolutionError(
            f'Ambiguous {kind} "{name}" matches ids '
            + ", ".join(i["id"] for i in hits))

    def account(self, name):
        return self._match("account", self._list("/api/v1/accounts"), name)

    def tag(self, name):
        return self._match("tag", self._list("/api/v1/tags"), name)

    def category(self, name):
        return self._match("category", self._list("/api/v1/categories"), name)
```

- [ ] **Step 4: Run test, verify it passes**

Run: `python -m unittest tests.unit.test_resolver -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add firefly_cli/resolver.py tests/unit/test_resolver.py
git commit -S -m "feat: name-to-id resolver with loud ambiguity errors"
```

---

## Task 8: account + category + tag + auth commands

**Files:**
- Create: `firefly_cli/commands/__init__.py`, `firefly_cli/commands/account.py`,
  `firefly_cli/commands/category.py`, `firefly_cli/commands/tag.py`,
  `firefly_cli/commands/auth.py`
- Test: `tests/unit/test_commands_account.py`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test, verify it fails**

Run: `python -m unittest tests.unit.test_commands_account -v`
Expected: FAIL, no module.

- [ ] **Step 3: Write `firefly_cli/commands/account.py`**

```python
# Copyright (C) 2026 Danilo M. <danix@danix.xyz>  GPL-2.0-only
from firefly_cli import registry, output

def _list_args(p):
    p.add_argument("--type", help="filter: asset, expense, revenue, liability, ...")

@registry.command("account list", help="list accounts", args=_list_args)
def cmd_list(args, ctx):
    params = {"type": args.type} if getattr(args, "type", None) else None
    resp = ctx.client.request("GET", "/api/v1/accounts", params=params)
    output.emit(output.unwrap(resp), human=ctx.human)
    return 0

def _name_arg(p):
    p.add_argument("account", help="account name or id")

@registry.command("account get", help="show one account", args=_name_arg)
def cmd_get(args, ctx):
    acc = ctx.resolver.account(args.account)
    output.emit(acc, human=ctx.human)
    return 0

@registry.command("account balance", help="show account balance", args=_name_arg)
def cmd_balance(args, ctx):
    acc = ctx.resolver.account(args.account)
    output.emit({"id": acc["id"], "name": acc.get("name"),
                 "current_balance": acc.get("current_balance")}, human=ctx.human)
    return 0
```

- [ ] **Step 4: Write `firefly_cli/commands/category.py`**

```python
# Copyright (C) 2026 Danilo M. <danix@danix.xyz>  GPL-2.0-only
from firefly_cli import registry, output

@registry.command("category list", help="list categories")
def cmd_list(args, ctx):
    resp = ctx.client.request("GET", "/api/v1/categories")
    output.emit(output.unwrap(resp), human=ctx.human)
    return 0
```

- [ ] **Step 5: Write `firefly_cli/commands/tag.py`**

```python
# Copyright (C) 2026 Danilo M. <danix@danix.xyz>  GPL-2.0-only
from firefly_cli import registry, output

@registry.command("tag list", help="list tags")
def cmd_list(args, ctx):
    resp = ctx.client.request("GET", "/api/v1/tags")
    output.emit(output.unwrap(resp), human=ctx.human)
    return 0
```

- [ ] **Step 6: Write `firefly_cli/commands/auth.py`**

```python
# Copyright (C) 2026 Danilo M. <danix@danix.xyz>  GPL-2.0-only
import getpass
from firefly_cli import registry, output, config

def _set_args(p):
    p.add_argument("--url", help="Firefly III base URL")
    p.add_argument("--token", help="Personal Access Token")

@registry.command("auth set", help="write url+token to config", args=_set_args)
def cmd_set(args, ctx):
    url = args.url or input("Firefly III URL: ").strip()
    token = args.token or getpass.getpass("Personal Access Token: ").strip()
    path = config.write(url, token)
    output.emit({"written": str(path)}, human=ctx.human)
    return 0

@registry.command("auth test", help="verify connectivity and token")
def cmd_test(args, ctx):
    resp = ctx.client.request("GET", "/api/v1/about")
    output.emit(resp.get("data", resp), human=ctx.human)
    return 0
```

- [ ] **Step 7: Write `firefly_cli/commands/__init__.py`** (import to self-register)

```python
# Copyright (C) 2026 Danilo M. <danix@danix.xyz>  GPL-2.0-only
# Importing each module runs its @registry.command decorators.
from firefly_cli.commands import auth, account, category, tag, transaction  # noqa: F401
```

Note: `transaction` is created in Task 9. Until then, temporarily drop
`transaction` from this import OR create Task 9 first. Executor: do Task 9
before running the full CLI in Task 10; this unit test imports only `account`.

- [ ] **Step 8: Run test, verify it passes**

Run: `python -m unittest tests.unit.test_commands_account -v`
Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add firefly_cli/commands/ tests/unit/test_commands_account.py
git commit -S -m "feat: account, category, tag, auth commands"
```

---

## Task 9: transaction commands (add/list/get/search)

**Files:**
- Create: `firefly_cli/commands/transaction.py`
- Test: `tests/unit/test_commands_transaction.py`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test, verify it fails**

Run: `python -m unittest tests.unit.test_commands_transaction -v`
Expected: FAIL, no module.

- [ ] **Step 3: Write `firefly_cli/commands/transaction.py`**

```python
# Copyright (C) 2026 Danilo M. <danix@danix.xyz>  GPL-2.0-only
from firefly_cli import registry, output

# Inference table keyed by (source_type, destination_type) -> firefly tx type.
def _infer_type(src_type, dst_type):
    s, d = (src_type or "").lower(), (dst_type or "").lower()
    if s == "asset" and d == "asset":
        return "transfer"
    if s in ("revenue",) and d == "asset":
        return "deposit"
    if s == "asset" and d in ("expense",):
        return "withdrawal"
    # Fallback: asset source -> withdrawal, asset dest -> deposit.
    if s == "asset":
        return "withdrawal"
    if d == "asset":
        return "deposit"
    raise ValueError(
        f"Cannot infer transaction type from {src_type!r}->{dst_type!r}; "
        "pass --type withdrawal|deposit|transfer.")

def _add_args(p):
    p.add_argument("amount")
    p.add_argument("--from", dest="source", required=True, help="source account")
    p.add_argument("--to", dest="dest", required=True, help="destination account")
    p.add_argument("--desc", default=None)
    p.add_argument("--date", default=None, help="YYYY-MM-DD (default today)")
    p.add_argument("--category", default=None)
    p.add_argument("--tags", default=None, help="comma-separated")
    p.add_argument("--type", default=None,
                   help="withdrawal|deposit|transfer (overrides inference)")

@registry.command("tx add", help="record a transaction", args=_add_args)
def cmd_add(args, ctx):
    src = ctx.resolver.account(args.source)
    dst = ctx.resolver.account(args.dest)
    ttype = args.type or _infer_type(src.get("type"), dst.get("type"))
    from datetime import date as _date
    split = {
        "type": ttype,
        "date": args.date or _date.today().isoformat(),
        "amount": str(args.amount),
        "description": args.desc or "",
        "source_id": src["id"],
        "destination_id": dst["id"],
    }
    if args.category:
        split["category_name"] = ctx.resolver.category(args.category).get("name", args.category)
    if args.tags:
        split["tags"] = [t.strip() for t in args.tags.split(",") if t.strip()]
    resp = ctx.client.request("POST", "/api/v1/transactions",
                              body={"transactions": [split]})
    output.emit(output.unwrap(resp), human=ctx.human)
    return 0

def _list_args(p):
    p.add_argument("--since", default=None, help="start date YYYY-MM-DD")
    p.add_argument("--until", default=None, help="end date YYYY-MM-DD")
    p.add_argument("--account", default=None, help="filter by account name")
    p.add_argument("--limit", type=int, default=20)

@registry.command("tx list", help="list transactions", args=_list_args)
def cmd_list(args, ctx):
    if args.account:
        acc = ctx.resolver.account(args.account)
        path = f"/api/v1/accounts/{acc['id']}/transactions"
    else:
        path = "/api/v1/transactions"
    params = {"limit": args.limit}
    if args.since:
        params["start"] = args.since
    if args.until:
        params["end"] = args.until
    resp = ctx.client.request("GET", path, params=params)
    output.emit(output.unwrap(resp), human=ctx.human)
    return 0

def _id_arg(p):
    p.add_argument("id")

@registry.command("tx get", help="show one transaction", args=_id_arg)
def cmd_get(args, ctx):
    resp = ctx.client.request("GET", f"/api/v1/transactions/{args.id}")
    output.emit(output.unwrap(resp), human=ctx.human)
    return 0

def _query_arg(p):
    p.add_argument("query")

@registry.command("tx search", help="search transactions", args=_query_arg)
def cmd_search(args, ctx):
    resp = ctx.client.request("GET", "/api/v1/search/transactions",
                              params={"query": args.query})
    output.emit(output.unwrap(resp), human=ctx.human)
    return 0
```

- [ ] **Step 4: Run test, verify it passes**

Run: `python -m unittest tests.unit.test_commands_transaction -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add firefly_cli/commands/transaction.py tests/unit/test_commands_transaction.py
git commit -S -m "feat: transaction add/list/get/search with type inference"
```

---

## Task 10: CLI wiring (argparse from registry, error handling)

**Files:**
- Create: `firefly_cli/cli.py`
- Test: `tests/unit/test_cli.py`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test, verify it fails**

Run: `python -m unittest tests.unit.test_cli -v`
Expected: FAIL, no module.

- [ ] **Step 3: Write `firefly_cli/cli.py`**

```python
# Copyright (C) 2026 Danilo M. <danix@danix.xyz>  GPL-2.0-only
import argparse
import sys
from firefly_cli import config, registry, output
from firefly_cli.client import Client
from firefly_cli.resolver import Resolver
from firefly_cli.context import Context
from firefly_cli.errors import FireflyError
import firefly_cli.commands  # noqa: F401  triggers registration

# Commands that must work without a configured client.
_NO_CLIENT = {"auth set"}

def _build_parser():
    parser = argparse.ArgumentParser(prog="firefly",
        description="CLI for Firefly III")
    parser.add_argument("--human", action="store_true",
        help="human-readable tables instead of JSON")
    parser.add_argument("--url", help="override base URL for this call")
    parser.add_argument("--token", help="override token for this call")
    sub = parser.add_subparsers(dest="_group", required=True)

    # Group "tx add" / "account list" into nested subparsers.
    groups = {}
    for cmd in registry.all_commands():
        group, _, leaf = cmd.name.partition(" ")
        if group not in groups:
            gp = sub.add_parser(group)
            groups[group] = gp.add_subparsers(dest="_leaf", required=True)
        lp = groups[group].add_parser(leaf, help=cmd.help)
        if cmd.args:
            cmd.args(lp)
        lp.set_defaults(_handler=cmd.handler, _cmdname=cmd.name)
    return parser

def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        if args._cmdname in _NO_CLIENT:
            ctx = Context(client=None, resolver=None, human=args.human)
        else:
            cfg = config.load()
            url = args.url or cfg["url"]
            token = args.token or cfg["token"]
            client = Client(url, token)
            ctx = Context(client=client, resolver=Resolver(client),
                          human=args.human)
        return args._handler(args, ctx)
    except FireflyError as e:
        output.emit_error(str(e))
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run test, verify it passes**

Run: `python -m unittest tests.unit.test_cli -v`
Expected: PASS.

- [ ] **Step 5: Run the whole unit suite and the CLI help**

Run:
```bash
python -m unittest discover -s tests/unit -v
python -m firefly_cli --help
python -m firefly_cli tx add --help
```
Expected: all tests PASS; help shows groups and the `tx add` flags.

- [ ] **Step 6: Commit**

```bash
git add firefly_cli/cli.py tests/unit/test_cli.py
git commit -S -m "feat: CLI wiring from command registry"
```

---

## Task 11: Integration tests (gated, live test account, self-cleaning)

**Files:**
- Create: `tests/integration/__init__.py`, `tests/integration/test_live.py`

- [ ] **Step 1: Write the gated integration test**

```python
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
        # Needs two asset accounts (or an asset + expense) on the TEST account.
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
```

- [ ] **Step 2: Run gated tests with no env (must skip)**

Run: `python -m unittest discover -s tests/integration -v`
Expected: tests SKIPPED (no env vars set).

- [ ] **Step 3: Run against the live test account**

Ask the user to provide test-account creds, then:
```bash
FIREFLY_TEST_URL=<url> FIREFLY_TEST_TOKEN=<tok> \
  python -m unittest discover -s tests/integration -v
```
Expected: PASS. If `current_balance` or the envelope differs, fix the relevant
production code + its unit test, then re-run.

- [ ] **Step 4: Commit**

```bash
git add tests/integration/
git commit -S -m "test: gated live integration tests, self-cleaning"
```

---

## Task 12: Final pass, docs, push

- [ ] **Step 1: Full suite + editable install smoke test**

```bash
python -m unittest discover -s tests -v
pip install -e .
firefly --help
```
Expected: tests PASS; `firefly` entry point works.

- [ ] **Step 2: Update README** with the final verified command list and a
  short "for agents" note (JSON default, exit codes, name resolution behavior).

- [ ] **Step 3: Commit and push**

```bash
git add README.md
git commit -S -m "docs: finalize README command reference"
git push
```
Expected: pushed to `origin` (danix_git:firefly-cli). Verify signed:
`git log --format='%h %G? %s' | head` (want `G`).

---

## Appendix A: CLAUDE.md content (copy verbatim in Task 1, Step 7)

```markdown
# firefly-cli

CLI tool letting an LLM agent (and the user) interact with a Firefly III
instance over its REST API. Python package, command `firefly`.

## Reference, do not modify
The Firefly III source is cloned at `../GITHUB/firefly-iii/` for reference only
(API shapes, transformers, route definitions). NEVER write to it.

## Architecture
- `firefly_cli/` package. Shared primitives: `config.py` (env over TOML file),
  `client.py` (HTTP + auth + error surfacing), `resolver.py` (name->id),
  `output.py` (JSON default, `--human` tables), `registry.py` + `context.py`.
- Commands live in `firefly_cli/commands/`, one module per group. Each command
  registers via the `@registry.command("group leaf", ...)` decorator.
- `cli.py` builds argparse subparsers from the registry. `commands/__init__.py`
  imports every command module so they self-register.

## Adding a command (the expandability rule)
1. Add or edit a module in `firefly_cli/commands/`.
2. Decorate the handler: `@registry.command("budget status", help=..., args=fn)`.
   `args` is `fn(subparser)` adding argparse arguments; handler is
   `fn(args, ctx) -> int`. `ctx` has `.client`, `.resolver`, `.human`.
3. If it is a new module, add it to the import line in `commands/__init__.py`.
4. Write a unit test under `tests/unit/` (mock `ctx.client` / `ctx.resolver`).
No other files change.

## Conventions
- Python 3.11+, standard library only. No third-party runtime deps.
- Output JSON by default (agent-first); `--human` for tables.
- Name args resolve to IDs; ambiguous or missing names are HARD errors listing
  candidates. Never silently guess an account (real money).
- All errors are `firefly_cli.errors.FireflyError` subclasses; `cli.main`
  catches them, prints `{"error": ...}` to stderr, returns exit code 1.

## Testing
- `python -m unittest discover -s tests/unit` — mocked, always run. TDD.
- Integration tests in `tests/integration/` hit a LIVE TEST ACCOUNT, gated by
  `FIREFLY_TEST_URL` / `FIREFLY_TEST_TOKEN`, skipped otherwise. Write tests
  create-then-delete their own records. NEVER point these at real data.

## License
GPLv2-only. Per-file header: `Copyright (C) 2026 Danilo M. <danix@danix.xyz>`.
```
```
