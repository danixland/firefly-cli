# Copyright (C) 2026 Danilo M. <danix@danix.xyz>  GPL-2.0-only
from firefly_cli import registry, output

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

@registry.command("tx add", help="record a transaction", args=_add_args)
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

def _list_args(p):
    p.add_argument("--since", default=None, help="start date YYYY-MM-DD")
    p.add_argument("--until", default=None, help="end date YYYY-MM-DD")
    p.add_argument("--account", default=None, help="filter by account name")
    p.add_argument("--limit", type=int, default=20)

@registry.command("tx list", help="list transactions", args=_list_args)
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

@registry.command("tx get", help="show one transaction", args=_id_arg)
def cmd_get(args, ctx):
    resp = ctx.client.request("GET", f"/api/v1/transactions/{args.id}")
    output.emit(output.unwrap(resp), human=ctx.human)
    return 0

def _query_arg(p):
    p.add_argument("query")

@registry.command("tx search", help="search transactions", args=_query_arg)
def cmd_search(args, ctx):
    resp = ctx.client.request("GET", "/api/v1/search/transactions",
                              params={"query": args.query})
    output.emit(output.unwrap(resp), human=ctx.human)
    return 0
