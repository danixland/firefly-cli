# firefly-cli

A command-line tool that lets an LLM agent (and you) interact with a
[Firefly III](https://www.firefly-iii.org/) instance over its REST API.
Python package, stdlib only, exposing the `firefly` command.

## Install

```bash
pip install -e .
```

Requires Python 3.11 or newer. No third-party runtime dependencies.

### Bash completion

A completion script lives at `completions/firefly.bash`. Enable it by sourcing
it from your shell profile, or install it system-wide:

```bash
# per-user: add to ~/.bashrc
source /path/to/firefly-cli/completions/firefly.bash

# or system-wide
sudo cp completions/firefly.bash /usr/share/bash-completion/completions/firefly
```

It is generated from the command registry, never hand-edited. Regenerate after
adding or changing commands:

```bash
python scripts/gen_completion.py > completions/firefly.bash
```

## Configuration

Provide your Firefly III URL and a personal access token in either way:

- Run `firefly auth set` and follow the prompts (stored in a local TOML file).
- Or set environment variables `FIREFLY_URL` and `FIREFLY_TOKEN`, which take
  precedence over the config file.

## Commands

Run `firefly --help` for the full list. Current commands:

```
firefly auth set                 write URL and token to the config file
firefly auth test                verify connectivity and token

firefly account list [--type T]  list accounts (filter: asset, expense, ...)
firefly account get <name|id>    show one account
firefly account balance <name>   show an account balance
firefly account create <name> --type asset|expense|revenue
        [--opening-balance N] [--currency CODE]

firefly tx add <amount> --from <acct> --to <acct> [--desc T]
        [--date YYYY-MM-DD] [--category C] [--tags a,b] [--type T]
firefly tx list [--since D] [--until D] [--account A] [--limit N]
firefly tx get <id>              show one transaction
firefly tx search <query>        search transactions

firefly category list
firefly tag list
```

The command set grows over time; see `CLAUDE.md` for how to add one.

## For agents

- Output is JSON by default. Pass `--human` for aligned tables.
- Exit code is 0 on success, 1 on any error; errors print as
  `{"error": "..."}` on stderr.
- Account arguments accept names, which are resolved to IDs. An ambiguous or
  unknown account is a hard error listing the candidates, never a silent guess.
- Categories and tags are not resolved: `tx add --category`/`--tags` pass the
  names straight to Firefly, which creates them if new. Accounts are never
  auto-created; use `account create`.
- `tx add` infers the transaction type from the account types (asset to expense
  is a withdrawal, revenue to asset is a deposit, asset to asset is a transfer).
  Override with `--type`.

## For agents (skill)

[`SKILL.md`](SKILL.md) is an agent-operating guide for driving `firefly`: the
JSON/exit-code contract, name resolution, transaction-type inference, task
recipes, and gotchas. It carries skill frontmatter, so it can be symlinked into
a Claude Code skills directory to auto-activate on Firefly III and personal
finance tasks.

## License

Released under the GNU General Public License, version 2 only (GPLv2-only).
See the [LICENSE](LICENSE) file for the full text.
