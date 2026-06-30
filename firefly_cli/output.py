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
    cols = list(rows[0].keys())
    widths = {c: max(len(c), *(len(str(r.get(c, ""))) for r in rows)) for c in cols}
    stream.write("  ".join(c.ljust(widths[c]) for c in cols) + "\n")
    for r in rows:
        stream.write("  ".join(str(r.get(c, "")).ljust(widths[c]) for c in cols) + "\n")

def emit_error(message, stream=None):
    stream = stream or sys.stderr
    json.dump({"error": message}, stream)
    stream.write("\n")
