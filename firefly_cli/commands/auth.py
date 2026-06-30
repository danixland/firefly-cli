# Copyright (C) 2026 Danilo M. <danix@danix.xyz>  GPL-2.0-only
import getpass
from firefly_cli import registry, output, config

def _set_args(p):
    p.add_argument("--url", help="Firefly III base URL")
    p.add_argument("--token", help="Personal Access Token")

@registry.command("auth set", help="save url + token to the config file (no API call)", args=_set_args)
def cmd_set(args, ctx):
    url = args.url or input("Firefly III URL: ").strip()
    token = args.token or getpass.getpass("Personal Access Token: ").strip()
    path = config.write(url, token)
    output.emit({"written": str(path)}, human=ctx.human)
    return 0

@registry.command("auth test", help="check the configured url + token reach Firefly")
def cmd_test(args, ctx):
    resp = ctx.client.request("GET", "/api/v1/about")
    output.emit(resp.get("data", resp), human=ctx.human)
    return 0
