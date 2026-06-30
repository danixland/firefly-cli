# firefly-cli — Design

Date: 2026-06-30

## Goal

A command-line tool that lets an LLM agent (and the user) interact with a
Firefly III instance over its REST API. Agent-first output, a lean set of
curated high-value commands, minimal dependencies, and an internal structure
that makes adding new commands mechanical.

The tool documents and reads from the cloned Firefly III codebase at
`../GITHUB/firefly-iii/` for reference only. It never writes to that codebase.

## Decisions (locked during brainstorming)

- **Scope:** curated agent verbs, not a full mirror of all ~254 endpoints.
  Grow the verb set over time.
- **Language:** Python 3, standard library only (no third-party runtime deps).
- **Output:** JSON by default (agent-first); `--human` flag for aligned tables.
- **Config/auth:** Personal Access Token (Bearer). Config at
  `~/.config/firefly-cli/config.toml`, read with stdlib `tomllib`. Env vars
  `FIREFLY_URL` / `FIREFLY_TOKEN` override the file. `auth set` writes the
  2-key file via a string template (tomllib cannot write; templating keeps
  deps at zero).
- **Name resolution:** name args (`--from`, `--to`, `--category`, account/tag
  names) resolve to numeric IDs internally. Ambiguous (>1 match) or no match
  is a hard error listing candidates — never a silent guess. Real money: an
  agent picking the wrong account must fail loudly.
- **Project size:** treated as a large project — a proper Python package from
  day one (not single-file). Package name `firefly_cli` (CLI command
  `firefly`) to avoid clashing with the main `firefly-iii` project.
- **Testing:** TDD. Unit tests with mocked HTTP run always. Integration tests
  hit a live test account, gated behind `FIREFLY_TEST_URL` /
  `FIREFLY_TEST_TOKEN`, skipped otherwise. They verify real response shapes
  and self-clean (create-then-delete their own records). Never run against
  real data.
- **License:** GPLv2-only. Full LICENSE, per-file header, README section,
  added early.

## Architecture

A Python package, command `firefly` (also runnable as `python -m firefly_cli`).

```
firefly-cli/                  # repo root
├── firefly_cli/
│   ├── __init__.py
│   ├── __main__.py           # python -m firefly_cli -> cli.main()
│   ├── cli.py                # argparse top-level; builds subparsers from the registry
│   ├── config.py             # tomllib read + template write + env override
│   ├── client.py             # HTTP layer, auth headers, error surfacing
│   ├── resolver.py           # name -> id lookup, ambiguity/no-match errors
│   ├── output.py             # json (default) / --human table rendering
│   └── commands/
│       ├── __init__.py       # command registry; discovers/loads command modules
│       ├── auth.py
│       ├── account.py
│       ├── transaction.py
│       ├── category.py
│       └── tag.py
├── tests/
│   ├── unit/                 # mocked HTTP, always run
│   └── integration/          # live test account, gated by FIREFLY_TEST_*
├── pyproject.toml            # console_script: firefly = firefly_cli.cli:main
├── LICENSE                   # GPLv2-only
├── README.md
└── CLAUDE.md
```

### Layers and responsibilities

- **config.py** — `load()` returns resolved `url` + `token` (env over file over
  error). `write(url, token)` templates the TOML file and creates the config
  dir. Clear error if config missing, pointing at `firefly auth set`.
- **client.py** — single `request(method, path, params=None, body=None)` using
  `urllib.request`. Sets `Authorization: Bearer <token>`,
  `Accept: application/vnd.api+json`, `Content-Type: application/json`. On
  non-2xx raises an error carrying HTTP status + Firefly's structured error
  body (Firefly returns useful validation errors). Returns parsed JSON.
- **resolver.py** — `resolve(kind, name) -> id`. Lists the relevant collection
  via client, case-insensitive exact name match. 0 matches or >1 matches raise
  with the candidate list. Numeric-as-ID is a later enhancement, not v1.
- **output.py** — `emit(data, human=False)`. Default prints JSON; for list
  results, unwraps Firefly's JSON:API envelope so the agent gets a clean array
  of resource objects. `--human` renders aligned tables. Errors go to stderr as
  JSON `{"error": ...}` with non-zero exit.
- **commands/** — each module defines one or more commands and **self-registers**
  with the registry in `commands/__init__.py`. A command declares: name, the
  argparse arguments it needs, and a handler `fn(args, ctx)` where `ctx` bundles
  config + client + resolver + output. `cli.py` iterates the registry to build
  subparsers. **Adding a command group = drop a module in `commands/`** — no
  changes elsewhere. This is the expandability mechanism.

## Commands (v1)

```
firefly auth set            # prompt/flags -> write config.toml
firefly auth test           # GET /about, confirm connectivity + token

firefly account list [--type asset|expense|revenue|liability|...]
firefly account get <name|id>
firefly account balance <name|id>

firefly tx add --from <acct> --to <acct> <amount> \
               [--desc TEXT] [--date YYYY-MM-DD] [--category NAME] [--tags a,b]
firefly tx list [--since DATE] [--until DATE] [--account NAME] [--limit N]
firefly tx get <id>
firefly tx search <query>

firefly category list
firefly tag list
```

Global flags: `--human`, `--url`, `--token` (overrides for one invocation).

Budgets are intentionally deferred from v1 (easy to add later via a new
command module).

### tx add semantics

Firefly transactions are split-based; `tx add` builds a single-split
transaction. Transaction **type is inferred from the from/to account types**:
asset→expense = withdrawal, revenue→asset = deposit, asset→asset = transfer.
Overridable with `--type`. `--date` defaults to today.

## Data flow (tx add example)

1. Parse args. 2. Resolve `--from`/`--to` names to account IDs (and types).
3. Infer transaction type from account types (or use `--type`).
4. Resolve `--category` name if given. 5. Build the JSON:API transaction body.
6. `POST /api/v1/transactions`. 7. Emit created resource (JSON or `--human`).

## Error handling

- Missing/invalid config → message pointing to `firefly auth set`, non-zero exit.
- API 4xx/5xx → surface Firefly's error message + HTTP status, non-zero exit.
- Name resolution failure (0 or >1 match) → list candidates, non-zero exit.
- All errors as `{"error": ...}` on stderr in JSON mode.

## Testing strategy

- **Unit (always):** mock `client.request`. Cover request building
  (URL/params/headers/body), name resolution including ambiguity and no-match,
  type inference, envelope unwrapping, config precedence (env over file),
  config templating round-trip. stdlib `unittest`.
- **Integration (gated):** run only when `FIREFLY_TEST_URL` /
  `FIREFLY_TEST_TOKEN` are set, else skipped. Verify real response shapes
  (envelope, account-type values, error format) against the user's test
  account. Write tests create-then-delete their own records. Capture confirmed
  shapes as fixtures so unit tests stay grounded in reality.

## Licensing

GPLv2-only. Fetch official LICENSE text from gnu.org. Per-source-file header:
`Copyright (C) 2026 Danilo M. <danix@danix.xyz>`. README License section.
Added at project start.

## Out of scope (v1)

Budgets, bills, piggy banks, rules, recurring transactions, attachments,
reports, currencies management, OAuth flow, multi-split transactions, the
generic raw-API escape hatch. All are natural later additions via new command
modules.
