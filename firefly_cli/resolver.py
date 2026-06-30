# Copyright (C) 2026 Danilo M. <danix@danix.xyz>  GPL-2.0-only
from firefly_cli.errors import ResolutionError

class Resolver:
    def __init__(self, client):
        self.client = client

    def _list(self, path):
        resp = self.client.request("GET", path, params={"limit": 1000})
        out = []
        for item in resp.get("data", []):
            attrs = item.get("attributes", {})
            out.append({"id": item.get("id"), **attrs})
        return out

    def _match(self, kind, items, name):
        hits = [i for i in items if str(i.get("name", "")).lower() == name.lower()]
        if len(hits) == 1:
            return hits[0]
        names = ", ".join(f'{i.get("name")}(id={i.get("id")})' for i in items)
        if not hits:
            raise ResolutionError(
                f'No {kind} named "{name}". Available: {names or "(none)"}')
        raise ResolutionError(
            f'Ambiguous {kind} "{name}" matches ids '
            + ", ".join(i["id"] for i in hits))

    def account(self, name):
        return self._match("account", self._list("/api/v1/accounts"), name)

    def tag(self, name):
        return self._match("tag", self._list("/api/v1/tags"), name)

    def category(self, name):
        return self._match("category", self._list("/api/v1/categories"), name)
