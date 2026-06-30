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
