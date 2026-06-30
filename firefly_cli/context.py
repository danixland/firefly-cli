# Copyright (C) 2026 Danilo M. <danix@danix.xyz>  GPL-2.0-only
from dataclasses import dataclass

@dataclass
class Context:
    client: object        # firefly_cli.client.Client
    resolver: object      # firefly_cli.resolver.Resolver
    human: bool = False
