# TODO

Next steps for firefly-cli. Each new command group follows the expandability
rule in CLAUDE.md (module + decorator, import line, unit test, SKILL.md, regen
bash completion).

## Command groups (deferred, roughly by demand)
- [ ] `budget` — list/status; most-requested next group.
- [ ] `bill` — list and inspect bills.
- [ ] `piggy` — piggy banks.
- [ ] `rule` — rules and rule groups.
- [ ] `recurring` — recurring transactions.
- [ ] `attachment` — list/download transaction attachments.
- [ ] `report` — summary reports (income/expense by period).
- [ ] `currency` — list/manage currencies.

## Verbs on existing groups
- [ ] `account delete` — currently needs a manual curl DELETE.
- [ ] `tx update` / `tx delete`.

## Output / UX
- [ ] `--human` column whitelists live in `output.py` `_VIEWS`; extend as new
      resource shapes are added (budget, bill, ...).
- [ ] Consider a `--no-color` flag (color is currently TTY-auto only).

## Infrastructure
- [ ] `--raw` escape hatch for arbitrary API calls.
- [ ] OAuth as an alternative to personal access tokens.
- [ ] zsh / fish completion (bash done).

## UI/UX
- [x] completion suggests values for `--type` (account: asset/expense/revenue
      /liability, tx: withdrawal/deposit/transfer), keyed per command. Static
      enum, no API call. See `FLAG_VALUES` in `scripts/gen_completion.py`.
