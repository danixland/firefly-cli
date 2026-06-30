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

# Short blurb per command group, shown in `firefly --help` and as the
# description in `firefly <group> --help`.
_GROUP_HELP = {
    "auth": "configure and verify the Firefly III connection (url + token)",
    "account": "list, create, and inspect accounts (asset, expense, revenue)",
    "category": "list categories (categories auto-create when used on a tx)",
    "tag": "list tags (tags auto-create when attached to a tx)",
    "tx": "record, list, and search transactions",
}

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
            blurb = _GROUP_HELP.get(group)
            gp = sub.add_parser(group, help=blurb, description=blurb)
            groups[group] = gp.add_subparsers(dest="_leaf", required=True)
        lp = groups[group].add_parser(leaf, help=cmd.help, description=cmd.help)
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
