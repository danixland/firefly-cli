# Copyright (C) 2026 Danilo M. <danix@danix.xyz>  GPL-2.0-only

class FireflyError(Exception):
    """Base for all firefly-cli errors."""

class ConfigError(FireflyError):
    """Missing or invalid configuration."""

class ResolutionError(FireflyError):
    """A name could not be resolved to a single id."""

class ApiError(FireflyError):
    """Firefly returned a non-2xx response."""
    def __init__(self, status, body):
        self.status = status
        self.body = body
        msg = body.get("message") if isinstance(body, dict) else body
        super().__init__(f"API error {status}: {msg}")
