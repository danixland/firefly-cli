# Smaller ISSUES.md items — design (v0.3.6)

Three items from `~/Documents/Finances/ISSUES.md` "Smaller" section, shipped
together as one PATCH bump (two new optional flags plus a doc fix; the CLI
contract only gains, nothing breaks).

## #2 Document `--since`/`--until` date semantics (doc-only)

**Finding (verified against Firefly source):** `tx list`'s `start`/`end`
params filter on `transaction_journals.date`
(`app/Helpers/Collector/Extensions/TimeCollection.php` `setRange`, lines
570-596: `where('transaction_journals.date', '>=', ...)` / `'<='`). That column
is the transaction's single date field — the date the user sets on the tx.
Firefly journals have no separate book/entry date, so there is no value-vs-book
ambiguity to resolve: the filter is on the tx date, which is the value date.

**Change:** SKILL.md `tx list` section states that `--since`/`--until` filter
on the transaction date (the date set on the tx), inclusive on both ends.
No code, no test, not independently version-worthy.

## #1 `tx list --flat`

**Problem:** `tx list` JSON nests every journal's splits under
`transactions[]`, even for single-split journals (the common case), forcing
scripts to reach through the array for one element.

**Change:** add `--flat` to `tx list`. When set, post-process the unwrapped
rows into one object per split, merging the split's fields up to top level with
the journal `id` repeated, and dropping the `transactions[]` key.

**Multi-split handling:** one flat row per split (approved). Single-split → one
clean object; a journal with N splits → N objects sharing the same `id`.
Uniform shape, matches the explode `--human` already does.

**Where:** new helper `output.flatten_tx(rows)`. It keeps the raw Firefly split
field names (e.g. `source_name`, `destination_name`, `category_name`,
`currency_code`) rather than renaming them the way `--human`'s `_tx_rows` does —
JSON output stays close to the API. The journal-level `id` is carried onto each
flat row; any other journal-level attributes are dropped (the split holds the
useful fields). Handler in `commands/transaction.py` `cmd_list` applies
`flatten_tx` to the unwrapped rows only when `args.flat`, on both the `--all`
and single-page paths, right before `output.emit`.

**Scope:** stdout JSON only. `flatten_tx` is applied only in the JSON path;
when `ctx.human`, it is skipped so the existing `--human` table (which already
explodes splits via `_tx_rows`) renders unchanged. So `--flat --human` renders
the same table as `--human` alone.

**Test:** unit — single-split journal flattens to one object with no
`transactions` key and the split fields at top level; a two-split journal
yields two objects sharing the id; `--human` output is unchanged (still uses
the nested explode).

## #3 `account create --if-not-exists`

**Problem:** `account create` returns full account JSON on success but a bare
`{"error": ...}` when the name is already in use, so idempotent import scripts
must special-case that error.

**Change:** add `--if-not-exists` to `account create`. When set, before the
POST, try `ctx.resolver.account(name)`:
- found → emit that account's JSON (same flattened shape as a create) with an
  added `"existed": true`, exit 0.
- not found (`ResolutionError`) → fall through to the normal create.

Detecting existence via the resolver (exact-name lookup that already raises on
missing) avoids parsing Firefly's 422 validation-error string, which is
brittle. One extra lookup, only when the flag is set.

**Edge:** without `--if-not-exists`, behavior is unchanged (a name clash still
surfaces Firefly's error, exit 1). The extra `"existed": true` key only appears
on the collision path; a fresh create is byte-for-byte as today.

**Test:** unit — `--if-not-exists` on an existing name returns the resolved
account with `existed: true` and does NOT POST; `--if-not-exists` on a new name
(resolver raises ResolutionError) POSTs normally; without the flag, existing
behavior (POST, no pre-lookup) is preserved.

## Cross-cutting

- **Version:** v0.3.6, PATCH. Two new optional flags + a doc fix; existing
  callers and JSON shapes are unchanged. Bump `pyproject.toml` and
  `firefly_cli/__init__.py` together.
- **Expandability rule:** module edits (`transaction.py`, `account.py`,
  `output.py`), unit tests, SKILL.md updates for all three, regenerate
  completion (`python scripts/gen_completion.py > completions/firefly.bash`).
  No new `--type`-style enum values, so `FLAG_VALUES` is untouched; the two new
  boolean flags appear in completion automatically via the registry.
- **Release:** signed commit(s), signed tag `v0.3.6`, push `--follow-tags`
  (one origin push reaches both remotes). Also mark the three items resolved in
  `~/Documents/Finances/ISSUES.md` (that file is outside the repo, not
  committed).
