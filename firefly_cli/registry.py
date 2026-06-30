# Copyright (C) 2026 Danilo M. <danix@danix.xyz>  GPL-2.0-only
from dataclasses import dataclass
from typing import Callable, Optional

@dataclass
class Command:
    name: str            # e.g. "tx add"
    handler: Callable     # fn(args, ctx) -> int
    help: str = ""
    args: Optional[Callable] = None   # fn(argparse_subparser) -> None

_COMMANDS = []

def command(name, help="", args=None):
    def deco(fn):
        _COMMANDS.append(Command(name=name, handler=fn, help=help, args=args))
        return fn
    return deco

def all_commands():
    return list(_COMMANDS)
