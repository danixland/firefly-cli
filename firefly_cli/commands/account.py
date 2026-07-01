# Copyright (C) 2026 Danilo M. <danix@danix.xyz>  GPL-2.0-only
from firefly_cli import registry, output
from firefly_cli.errors import FireflyError

# v1 scope: the everyday types. Liabilities need extra required fields
# (liability_type/direction/amount); add when needed.
_CREATE_TYPES = ("asset", "expense", "revenue")

def _list_args(p):
    p.add_argument("--type", help="filter: asset, expense, revenue, liability, ...")

@registry.command("account list", help="list accounts; optionally filter by --type", args=_list_args)
def cmd_list(args, ctx):
    params = {"type": args.type} if getattr(args, "type", None) else None
    resp = ctx.client.request("GET", "/api/v1/accounts", params=params)
    output.emit(output.unwrap(resp), human=ctx.human)
    return 0

def _create_args(p):
    p.add_argument("name", help="account name (must be unique)")
    p.add_argument("--type", required=True,
                   help="asset, expense, or revenue")
    p.add_argument("--opening-balance", dest="opening_balance", default=None,
                   help="initial balance (asset accounts); dated today")
    p.add_argument("--currency", default=None, help="currency code, e.g. EUR")
    p.add_argument("--if-not-exists", dest="if_not_exists", action="store_true",
                   help="if an account with this name exists, return it (existed:true) instead of erroring")

@registry.command("account create", help="create an asset, expense, or revenue account", args=_create_args)
def cmd_create(args, ctx):
    if args.type not in _CREATE_TYPES:
        raise FireflyError(
            f'Unsupported account type "{args.type}". '
            f'Use one of: {", ".join(_CREATE_TYPES)}.')
    if getattr(args, "if_not_exists", False):
        # Resolve by name to detect existence; avoids parsing Firefly's 422
        # "name already in use" error string. Missing = ResolutionError -> create.
        from firefly_cli.errors import ResolutionError
        try:
            existing = ctx.resolver.account(args.name)
        except ResolutionError:
            existing = None
        if existing is not None:
            output.emit({**existing, "existed": True}, human=ctx.human)
            return 0
    body = {"name": args.name, "type": args.type}
    if args.type == "asset":
        body["account_role"] = "defaultAsset"
    if args.opening_balance is not None:
        from datetime import date as _date
        body["opening_balance"] = str(args.opening_balance)
        body["opening_balance_date"] = _date.today().isoformat()
    if args.currency:
        body["currency_code"] = args.currency
    resp = ctx.client.request("POST", "/api/v1/accounts", body=body)
    output.emit(output.unwrap(resp), human=ctx.human)
    return 0

def _name_arg(p):
    p.add_argument("account", help="account name or id")

@registry.command("account get", help="show full details for one account (name or id)", args=_name_arg)
def cmd_get(args, ctx):
    acc = ctx.resolver.account(args.account)
    output.emit(acc, human=ctx.human)
    return 0

def _balance_args(p):
    p.add_argument("account", help="account name or id")
    p.add_argument("--at", default=None,
                   help="balance as of this date YYYY-MM-DD (default: current)")

@registry.command("account balance", help="show balance for one account (name or id); --at for a historical date", args=_balance_args)
def cmd_balance(args, ctx):
    acc = ctx.resolver.account(args.account)
    if args.at:
        # Firefly recomputes current_balance as of ?date= on the account show endpoint.
        dated = output.unwrap(ctx.client.request(
            "GET", f"/api/v1/accounts/{acc['id']}", params={"date": args.at}))
        output.emit({"id": acc["id"], "name": dated.get("name") or acc.get("name"),
                     "date": args.at,
                     "current_balance": dated.get("current_balance")}, human=ctx.human)
        return 0
    output.emit({"id": acc["id"], "name": acc.get("name"),
                 "current_balance": acc.get("current_balance")}, human=ctx.human)
    return 0
