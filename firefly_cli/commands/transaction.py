# Copyright (C) 2026 Danilo M. <danix@danix.xyz>  GPL-2.0-only
from firefly_cli import registry, output
from firefly_cli.errors import FireflyError

# Inference table keyed by (source_type, destination_type) -> firefly tx type.
def _infer_type(src_type, dst_type):
    s, d = (src_type or "").lower(), (dst_type or "").lower()
    if s == "asset" and d == "asset":
        return "transfer"
    if s in ("revenue",) and d == "asset":
        return "deposit"
    if s == "asset" and d in ("expense",):
        return "withdrawal"
    # Fallback: asset source -> withdrawal, asset dest -> deposit.
    if s == "asset":
        return "withdrawal"
    if d == "asset":
        return "deposit"
    raise ValueError(
        f"Cannot infer transaction type from {src_type!r}->{dst_type!r}; "
        "pass --type withdrawal|deposit|transfer.")

def _add_args(p):
    p.add_argument("amount")
    p.add_argument("--from", dest="source", required=True, help="source account")
    p.add_argument("--to", dest="dest", required=True, help="destination account")
    p.add_argument("--desc", default=None)
    p.add_argument("--date", default=None, help="YYYY-MM-DD (default today)")
    p.add_argument("--category", default=None)
    p.add_argument("--tags", default=None, help="comma-separated")
    p.add_argument("--type", default=None,
                   help="withdrawal|deposit|transfer (overrides inference)")

@registry.command("tx add", help="record a transaction; source/destination resolve to accounts, category/tags auto-create", args=_add_args)
def cmd_add(args, ctx):
    src = ctx.resolver.account(args.source)
    dst = ctx.resolver.account(args.dest)
    ttype = args.type or _infer_type(src.get("type"), dst.get("type"))
    from datetime import date as _date
    split = {
        "type": ttype,
        "date": args.date or _date.today().isoformat(),
        "amount": str(args.amount),
        "description": args.desc or "",
        "source_id": src["id"],
        "destination_id": dst["id"],
    }
    if args.category:
        # Pass name raw; Firefly auto-creates the category if it doesn't exist.
        split["category_name"] = args.category
    if args.tags:
        split["tags"] = [t.strip() for t in args.tags.split(",") if t.strip()]
    resp = ctx.client.request("POST", "/api/v1/transactions",
                              body={"transactions": [split]})
    output.emit(output.unwrap(resp), human=ctx.human)
    return 0

def _edit_args(p):
    p.add_argument("id")
    p.add_argument("--amount", default=None)
    p.add_argument("--date", default=None, help="YYYY-MM-DD")
    p.add_argument("--desc", default=None)
    p.add_argument("--from", dest="source", default=None, help="source account")
    p.add_argument("--to", dest="dest", default=None, help="destination account")
    p.add_argument("--category", default=None)
    p.add_argument("--tags", default=None, help="comma-separated")
    p.add_argument("--type", default=None, help="withdrawal|deposit|transfer")

# ponytail: single-split journals only; multi-split edits need transaction_journal_id per row.
@registry.command("tx edit", help="modify one transaction by id; only the fields you pass change", args=_edit_args)
def cmd_edit(args, ctx):
    split = {}
    if args.amount is not None:
        split["amount"] = str(args.amount)
    if args.date is not None:
        split["date"] = args.date
    if args.desc is not None:
        split["description"] = args.desc
    if args.source is not None:
        split["source_id"] = ctx.resolver.account(args.source)["id"]
    if args.dest is not None:
        split["destination_id"] = ctx.resolver.account(args.dest)["id"]
    if args.category is not None:
        split["category_name"] = args.category
    if args.tags is not None:
        split["tags"] = [t.strip() for t in args.tags.split(",") if t.strip()]
    if args.type is not None:
        split["type"] = args.type
    if not split:
        raise FireflyError("tx edit: nothing to change; pass at least one field")
    resp = ctx.client.request("PUT", f"/api/v1/transactions/{args.id}",
                              body={"transactions": [split]})
    output.emit(output.unwrap(resp), human=ctx.human)
    return 0

def _delete_args(p):
    p.add_argument("id")
    p.add_argument("--yes", action="store_true", help="confirm deletion (required)")

@registry.command("tx delete", help="delete one transaction by id (requires --yes)", args=_delete_args)
def cmd_delete(args, ctx):
    if not args.yes:
        raise FireflyError(f"tx delete {args.id}: refusing without --yes")
    ctx.client.request("DELETE", f"/api/v1/transactions/{args.id}")
    output.emit({"deleted": args.id}, human=ctx.human)
    return 0

def _list_args(p):
    p.add_argument("--since", default=None, help="start date YYYY-MM-DD")
    p.add_argument("--until", default=None, help="end date YYYY-MM-DD")
    p.add_argument("--account", default=None, help="filter by account name")
    p.add_argument("--limit", type=int, default=20)

@registry.command("tx list", help="list recent transactions (newest first)", args=_list_args)
def cmd_list(args, ctx):
    if args.account:
        acc = ctx.resolver.account(args.account)
        path = f"/api/v1/accounts/{acc['id']}/transactions"
    else:
        path = "/api/v1/transactions"
    params = {"limit": args.limit}
    if args.since:
        params["start"] = args.since
    if args.until:
        params["end"] = args.until
    resp = ctx.client.request("GET", path, params=params)
    output.emit(output.unwrap(resp), human=ctx.human)
    return 0

def _id_arg(p):
    p.add_argument("id")

@registry.command("tx get", help="show full details for one transaction by id", args=_id_arg)
def cmd_get(args, ctx):
    resp = ctx.client.request("GET", f"/api/v1/transactions/{args.id}")
    output.emit(output.unwrap(resp), human=ctx.human)
    return 0

def _query_arg(p):
    p.add_argument("query")

@registry.command("tx search", help="search transactions by Firefly query string", args=_query_arg)
def cmd_search(args, ctx):
    resp = ctx.client.request("GET", "/api/v1/search/transactions",
                              params={"query": args.query})
    output.emit(output.unwrap(resp), human=ctx.human)
    return 0
