# Copyright (C) 2026 Danilo M. <danix@danix.xyz>  GPL-2.0-only
import json
import sys

def unwrap(resp):
    """Flatten Firefly's JSON:API envelope to plain id+attributes objects."""
    def flat(item):
        out = {"id": item.get("id")}
        out.update(item.get("attributes", {}))
        return out
    data = resp.get("data", resp)
    if isinstance(data, list):
        return [flat(i) for i in data]
    if isinstance(data, dict) and "attributes" in data:
        return flat(data)
    return data

# Columns shown for transactions in --human mode, in order. The useful data
# lives in each tx's nested `transactions` split list, not the top level.
_TX_COLS = ("id", "date", "type", "amount", "currency",
            "description", "from", "to", "category")

def _it_date(d):
    """Firefly date 'YYYY-MM-DD...' -> Italian 'DD/MM/YYYY'. Raw on mismatch."""
    s = (d or "")[:10]
    parts = s.split("-")
    if len(parts) == 3 and all(parts):
        y, m, day = parts
        return f"{day}/{m}/{y}"
    return s

def _trim_amount(a):
    """Firefly sends amounts as 12-decimal strings; show a tidy 2-dp value.
    Falls back to the raw value if it is not a plain number."""
    try:
        return f"{float(a):.2f}"
    except (TypeError, ValueError):
        return a

def _tx_rows(rows):
    """Explode Firefly transaction objects into flat per-split display rows.

    Each object has a `transactions` list (one entry per split). We surface the
    fields a human actually reads; the raw JSON output is unaffected.
    """
    out = []
    for r in rows:
        for s in r.get("transactions", [{}]):
            out.append({
                "id": r.get("id"),
                "date": _it_date(s.get("date")),
                "type": s.get("type"),
                "amount": _trim_amount(s.get("amount")),
                "currency": s.get("currency_code"),
                "description": s.get("description"),
                "from": s.get("source_name"),
                "to": s.get("destination_name"),
                "category": s.get("category_name"),
            })
    return out

def _is_tx(rows):
    return bool(rows) and isinstance(rows[0], dict) and "transactions" in rows[0]

def flatten_tx(rows):
    """Explode unwrapped tx journals into one flat object per split.

    Each journal is {id, transactions: [split, ...], ...}. We emit one object
    per split: the split's raw Firefly fields (source_name, amount, etc.) with
    the journal id merged in and the `transactions` list dropped. Single-split
    journals (the common case) become one clean object. Rows without a
    `transactions` list pass through unchanged.
    """
    out = []
    for r in rows:
        splits = r.get("transactions")
        if not isinstance(splits, list):
            out.append(r)
            continue
        for s in splits:
            flat = dict(s)
            flat["id"] = r.get("id")
            out.append(flat)
    return out

# Per-resource column whitelists for --human. Firefly returns ~50 fields per
# row; only a handful are worth a table. A row is matched by a signature key.
# (signature, columns) -- first match wins; unmatched rows use a generic table.
_VIEWS = [
    ("account_role", ("id", "name", "type", "current_balance",
                      "currency_code", "active")),
    ("tag",          ("id", "tag", "description")),
    ("current_balance", ("id", "name", "current_balance")),  # `account balance`
    ("name",         ("id", "name")),                       # category, etc.
]

def _cols_for(row):
    for sig, cols in _VIEWS:
        if sig in row:
            return list(cols)
    return None

def _cell(v):
    # Tables are one row per line; collapse any embedded newlines (e.g. notes).
    return str(v if v is not None else "").replace("\n", " ").replace("\r", "")

_RESET = "\033[0m"
_TYPE_COLOR = {            # by transaction type
    "withdrawal": "\033[31m",  # red   (money out)
    "deposit":    "\033[32m",  # green (money in)
    "transfer":   "\033[36m",  # cyan  (internal)
}

def emit(data, human=False, stream=None):
    stream = stream or sys.stdout
    if not human:
        json.dump(data, stream, indent=2, default=str)
        stream.write("\n")
        return
    rows = data if isinstance(data, list) else [data]
    if not rows:
        stream.write("(no results)\n")
        return
    if _is_tx(rows):
        rows = _tx_rows(rows)
        cols = list(_TX_COLS)
    else:
        cols = _cols_for(rows[0])
        if cols is None:
            # Generic fallback: drop nested (dict/list) columns that would dump
            # unreadable blobs; show the scalar fields only.
            cols = [c for c in rows[0]
                    if not any(isinstance(r.get(c), (dict, list)) for r in rows)]
    widths = {c: max(len(c), *(len(_cell(r.get(c))) for r in rows)) for c in cols}
    color = getattr(stream, "isatty", lambda: False)()
    sep = "   "
    stream.write(sep.join(c.ljust(widths[c]) for c in cols) + "\n")
    stream.write(sep.join("─" * widths[c] for c in cols) + "\n")  # header rule
    for r in rows:
        line = sep.join(_cell(r.get(c)).ljust(widths[c]) for c in cols)
        if color:
            tint = _TYPE_COLOR.get(str(r.get("type", "")).lower())
            if tint:
                line = tint + line + _RESET
        stream.write(line + "\n")

def emit_error(message, stream=None):
    stream = stream or sys.stderr
    json.dump({"error": message}, stream)
    stream.write("\n")
