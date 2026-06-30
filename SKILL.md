---
name: firefly-cli
description: Operate a Firefly III instance from the command line via the `firefly` tool. Use when recording transactions, checking balances or accounts, or querying budgets/categories/tags in Firefly III, or whenever a personal-finance task mentions Firefly.
---

# firefly-cli

`firefly` is a stdlib-only Python CLI for a [Firefly III](https://www.firefly-iii.org/)
instance. It is built for an agent to drive: JSON in/out, names resolved to IDs,
clear exit codes. This skill tells you how to use it correctly.

## Setup check

Before anything, confirm it is configured:

```bash
firefly auth test
```

- Exit 0 with an `about` payload: ready.
- Exit 1 with `{"error": "No Firefly III config found..."}`: not configured.
  Either run `firefly auth set` (interactive) or set `FIREFLY_URL` and
  `FIREFLY_TOKEN` env vars. Do NOT invent a URL or token; ask the user.

If `firefly` is not on PATH, run from the repo with `python -m firefly_cli ...`
(same arguments) or `pip install -e .` first.

## The contract you rely on

- **Output is JSON by default.** Parse it. Lists return a flat array of
  objects (`[{"id": "1", "name": "...", ...}]`); single resources return one
  object. Do not pass `--human` when you intend to parse, it prints tables.
- **Exit code 0 = success, 1 = error.** On error, `{"error": "..."}` goes to
  stderr. Always check the exit code before trusting output.
- **You pass names, not IDs.** `--from test01`, `--category Groceries`. The CLI
  resolves them. An unknown or ambiguous name is a HARD error that lists the
  candidates and exits 1. When that happens, read the candidates, pick the
  right one, and retry. NEVER guess an account, a wrong account moves real
  money.
- **`tx add` infers the transaction type** from the account types: asset to
  expense = withdrawal, revenue to asset = deposit, asset to asset = transfer.
  Override with `--type withdrawal|deposit|transfer` only when inference is
  wrong or both ends are non-asset.

## Commands

```
firefly auth test                          verify connectivity and token
firefly account list [--type asset|expense|revenue|liability|...]
firefly account get <name|id>
firefly account balance <name|id>
firefly tx add <amount> --from <acct> --to <acct>
        [--desc TEXT] [--date YYYY-MM-DD] [--category NAME] [--tags a,b] [--type T]
firefly tx list [--since YYYY-MM-DD] [--until YYYY-MM-DD] [--account NAME] [--limit N]
firefly tx get <id>
firefly tx search <query>
firefly category list
firefly tag list
```

Global: `--human` (tables, do not use when parsing), `--url`/`--token`
(per-call override of config).

## Task recipes

**Record an expense** (most common):
```bash
firefly tx add 42.50 --from test01 --to Groceries --desc "weekly shop" --tags food
```
`test01` is an asset account, `Groceries` an expense account, so this is a
withdrawal. If `Groceries` does not exist, the CLI errors with the available
expense accounts; pick one or ask the user before creating a new category.

**Record income:**
```bash
firefly tx add 1800 --from Salary --to test01 --desc "June pay"
```

**Move money between own accounts:**
```bash
firefly tx add 200 --from test01 --to Savings --type transfer
```

**Check a balance:**
```bash
firefly account balance test01            # -> {"id","name","current_balance"}
```

**Find recent spending in a window:**
```bash
firefly tx list --account test01 --since 2026-06-01 --until 2026-06-30
```

**Look up a transaction by id** (ids come from `tx add`/`tx list` output):
```bash
firefly tx get 75
```
Returns a transaction group: `{"id", ..., "transactions": [ {split}, ... ]}`.
The real fields (type, amount, description, source/destination, tags) are in
`transactions[0]` for a single-split transaction.

## Gotchas

- `tx list` with no transactions in range returns `[]`. Empty is not an error;
  it means no matches, not a failure.
- Amounts are strings in responses, often with trailing zeros
  (`"0.010000000000"`). Compare numerically, do not string-match.
- Dates in `tx list` filter by transaction date; omit them to use Firefly's
  default period, which may hide older transactions. Pass an explicit `--since`
  to be sure.
- `--tags` is a single comma-separated argument: `--tags food,fun`.

## Extending

New verbs (budgets, bills, piggy banks, etc.) are added by dropping a module in
`firefly_cli/commands/`. See the project `CLAUDE.md` for the exact pattern.
