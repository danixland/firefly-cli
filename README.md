# firefly-cli

A command-line tool that lets an LLM agent (and you) interact with a
[Firefly III](https://www.firefly-iii.org/) instance over its REST API.
Python package, stdlib only, exposing the `firefly` command.

## Install

```bash
pip install -e .
```

Requires Python 3.11 or newer. No third-party runtime dependencies.

## Configuration

Provide your Firefly III URL and a personal access token in either way:

- Run `firefly auth set` and follow the prompts (stored in a local TOML file).
- Or set environment variables `FIREFLY_URL` and `FIREFLY_TOKEN`, which take
  precedence over the config file.

## Commands

Run `firefly --help` to see the available command groups and options. The full
set of commands is still being built out, so expect more to appear over time.

## License

Released under the GNU General Public License, version 2 only (GPLv2-only).
See the [LICENSE](LICENSE) file for the full text.
