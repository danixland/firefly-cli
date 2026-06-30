# Copyright (C) 2026 Danilo M. <danix@danix.xyz>  GPL-2.0-only
import json
import urllib.request
import urllib.parse
import urllib.error
from firefly_cli.errors import ApiError


class Client:
    def __init__(self, url, token, timeout=30):
        self.url = url.rstrip("/")
        self.token = token
        self.timeout = timeout

    def request(self, method, path, params=None, body=None):
        full = self.url + path
        if params:
            full += "?" + urllib.parse.urlencode(params)
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(full, data=data, method=method)
        req.add_header("Authorization", f"Bearer {self.token}")
        req.add_header("Accept", "application/vnd.api+json")
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            raw = e.read().decode()
            try:
                parsed = json.loads(raw)
            except ValueError:
                parsed = {"message": raw or e.reason}
            raise ApiError(e.code, parsed) from None
