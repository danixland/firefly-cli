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
- `python -m unittest discover -s tests/unit`, mocked, always run. TDD.
- Integration tests in `tests/integration/` hit a LIVE TEST ACCOUNT, gated by
  `FIREFLY_TEST_URL` / `FIREFLY_TEST_TOKEN`, skipped otherwise. Write tests
  create-then-delete their own records. NEVER point these at real data.

## License
GPLv2-only. Per-file header: `Copyright (C) 2026 Danilo M. <danix@danix.xyz>`.
