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
- **You pass names, not IDs.** `--from test01`, `--to Groceries`. For
  **accounts** the CLI resolves the name to an ID; an unknown or ambiguous
  account is a HARD error that lists the candidates and exits 1. When that
  happens, read the candidates, pick the right one, and retry. NEVER guess an
  account, a wrong account moves real money.
- **Categories and tags auto-create.** `--category NAME` and `--tags a,b` are
  passed straight to Firefly, which creates the category/tag if it does not
  exist. No resolution, no error on a new name. Reuse an existing name (see
  `firefly category list` / `firefly tag list`) to avoid duplicates.
- **`tx add` infers the transaction type** from the account types: asset to
  expense = withdrawal, revenue to asset = deposit, asset to asset = transfer.
  Override with `--type withdrawal|deposit|transfer` only when inference is
  wrong or both ends are non-asset.

## Commands

```
firefly auth test                          verify connectivity and token
firefly account list [--type asset|expense|revenue|liability|...]
firefly account get <name|id>
firefly account balance <name|id> [--at YYYY-MM-DD]
firefly account create <name> --type asset|expense|revenue
        [--opening-balance N] [--currency CODE]
firefly tx add <amount> --from <acct> --to <acct>
        [--desc TEXT] [--date YYYY-MM-DD] [--category NAME] [--tags a,b] [--type T]
firefly tx edit <id>
        [--amount N] [--date YYYY-MM-DD] [--desc TEXT] [--from <acct>] [--to <acct>]
        [--category NAME] [--tags a,b] [--type T]   # only fields passed are changed
firefly tx delete <id> --yes                        # --yes required, no prompt
firefly tx list [--since YYYY-MM-DD] [--until YYYY-MM-DD] [--account NAME] [--limit N] [--all]
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
withdrawal. `Groceries` here is the destination **expense account** and must
exist (resolved by name). The `--tags food` and any `--category NAME` are
auto-created by Firefly if new.

**Record income:**
```bash
firefly tx add 1800 --from Salary --to test01 --desc "June pay"
```

**Move money between own accounts:**
```bash
firefly tx add 200 --from test01 --to Savings --type transfer
```

**Create an account** (when `tx add` errors that an account does not exist,
and the user confirms it should be created):
```bash
firefly account create Savings --type asset --opening-balance 0
firefly account create Rent --type expense
```
Supports asset, expense, revenue. asset accounts get the default role
automatically. Unlike categories/tags, accounts are NOT auto-created by
`tx add`, create them explicitly here first.

**Check a balance:**
```bash
firefly account balance test01            # -> {"id","name","current_balance"}
firefly account balance test01 --at 2026-05-31  # historical: balance as of that date
                                                # -> adds "date"; useful for reconciliation
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

**Fix a mis-imported transaction.** `tx edit` patches only the fields you pass;
everything else is left untouched. To flip a reversed transfer, swap the ends:
```bash
firefly tx edit 75 --from BBVA --to Mediolanum
firefly tx edit 75 --amount 50.00 --date 2026-06-15
firefly tx delete 76 --yes        # remove a duplicate
```

## Gotchas

- `tx list` with no transactions in range returns `[]`. Empty is not an error;
  it means no matches, not a failure.
- `tx list` returns at most `--limit` rows (default 20). When more match, it
  prints `showing N of M (use --all for all)` to **stderr** (stdout JSON stays
  clean). Pass `--all` to auto-paginate every page. Critical for reconciliation:
  a truncated list makes a correct ledger look wrong.
- Amounts are strings in responses, often with trailing zeros
  (`"0.010000000000"`). Compare numerically, do not string-match.
- Dates in `tx list` filter by transaction date; omit them to use Firefly's
  default period, which may hide older transactions. Pass an explicit `--since`
  to be sure.
- `--tags` is a single comma-separated argument: `--tags food,fun`.
- `tx edit` handles single-split journals only. `tx delete` will not run
  without `--yes` (there is no interactive prompt); on success it prints
  `{"deleted": "<id>"}`.

## Extending

New verbs (budgets, bills, piggy banks, etc.) are added by dropping a module in
`firefly_cli/commands/`. See the project `CLAUDE.md` for the exact pattern.
