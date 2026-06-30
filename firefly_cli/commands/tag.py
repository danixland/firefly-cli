# Copyright (C) 2026 Danilo M. <danix@danix.xyz>  GPL-2.0-only
from firefly_cli import registry, output

@registry.command("tag list", help="list tags")
def cmd_list(args, ctx):
    resp = ctx.client.request("GET", "/api/v1/tags")
    output.emit(output.unwrap(resp), human=ctx.human)
    return 0
