"""VELION contract adapter to an EXISTING third-party local Ollama model.

Ollama inference is real only when the user has independently installed and
started the runtime, pulled a licensed model, and explicitly invokes --live.
No VELION foundation model weights are asserted here; this is a provider port.
No agent tools, remote URL, accounts, payments or cloud access.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from http.client import HTTPConnection, HTTPException


ENDPOINT = "http://127.0.0.1:11434/api/chat"
MODEL_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:/-]{0,99}\Z")


class InferenceDenied(ValueError):
    """One local model invocation is not authorized or cannot be trusted."""


@dataclass(frozen=True)
class ModelResult:
    text: str
    provider: str
    model_name: str
    model_response_sha256: str
    model_request_sha256: str
    actual_inference: bool
    model_weights_verified: bool = False


class LocalOllamaAdapter:
    """No arbitrary endpoints: only localhost Ollama, one request, no tools."""

    def __init__(self, model: str, *, timeout_seconds: int = 45):
        if type(model) is not str or not MODEL_PATTERN.fullmatch(model):
            raise InferenceDenied("INVALID_MODEL_IDENTIFIER")
        if type(timeout_seconds) is not int or not 1 <= timeout_seconds <= 90:
            raise InferenceDenied("INVALID_TIMEOUT")
        self.model = model
        self.timeout_seconds = timeout_seconds

    def generate(self, system: str, task: str) -> ModelResult:
        if any(type(s) is not str or not 1 <= len(s) <= n or "\x00" in s
               for s,n in ((system, 1600), (task, 3500))):
            raise InferenceDenied("INVALID_MODEL_INPUT")
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": task}
            ],
            "stream": False,
            "format": "json",
            "keep_alive": 0,
            "options": {"temperature": 0, "seed": 42, "num_predict": 220}
        }
        request_body = json.dumps(payload, sort_keys=True, ensure_ascii=True).encode("utf8")
        # Direct HTTPConnection never follows redirects to off-loopback
        # hosts. Neither model outputs nor local server responses can modify
        # the connection target, path, port or authorization scope.
        connection = HTTPConnection("127.0.0.1", 11434, timeout=self.timeout_seconds)
        try:
            connection.request(
                "POST", "/api/chat", body=request_body,
                headers={"Content-Type": "application/json", "Accept": "application/json"}
            )
            response = connection.getresponse()
            if response.status != 200:
                raise InferenceDenied("OLLAMA_BAD_HTTP_STATUS")
            body = response.read(256 * 1024 + 1)
        except (HTTPException, TimeoutError, OSError) as exc:
            raise InferenceDenied("LOCAL_OLLAMA_UNAVAILABLE") from exc
        finally:
            connection.close()
        if len(body) > 256 * 1024:
            raise InferenceDenied("OLLAMA_RESPONSE_TOO_LARGE")
        try:
            result = json.loads(body)
        except (ValueError, UnicodeError) as exc:
            raise InferenceDenied("INVALID_OLLAMA_RESPONSE") from exc
        if (type(result) is not dict or result.get("done") is not True
                or result.get("model") != self.model
                or type(result.get("message")) is not dict):
            raise InferenceDenied("INVALID_OLLAMA_RESPONSE_SCHEMA")
        message = result["message"]
        content = message.get("content")
        if (message.get("role") != "assistant" or "tool_calls" in message
                or type(content) is not str or not 2 <= len(content) <= 6000):
            raise InferenceDenied("UNSAFE_OR_EMPTY_MODEL_OUTPUT")
        return ModelResult(
            text=content,
            provider="ollama_local",
            model_name=self.model,
            model_request_sha256=hashlib.sha256(request_body).hexdigest(),
            model_response_sha256=hashlib.sha256(content.encode("utf8")).hexdigest(),
            actual_inference=True,
            model_weights_verified=False,
        )
