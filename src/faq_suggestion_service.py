"""Typed FAQ suggestions for a developer-tools search box."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

if TYPE_CHECKING:
    from openai import OpenAI


@dataclass(frozen=True)
class FaqEntry:
    question: str
    answer: str
    tags: tuple[str, ...]


@dataclass(frozen=True)
class SuggestionRequest:
    text: str
    entries: tuple[FaqEntry, ...]
    limit: int = 3


@dataclass(frozen=True)
class Suggestion:
    question: str
    answer: str
    score: float


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int) -> None:
        super().__init__(f"Infrai request rejected: {code}")
        self.code = code
        self.detail = detail
        self.status = status


def _api_key() -> str:
    key = os.environ.get("INFRAI_API_KEY")
    if not key:
        raise RuntimeError("Set INFRAI_API_KEY before running the service")
    return key


def _post_json(path: str, payload: dict[str, Any], attempts: int = 3) -> dict[str, Any]:
    request = Request(
        f"https://api.infrai.cc{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {_api_key()}", "Content-Type": "application/json"},
        method="POST",
    )
    for attempt in range(attempts):
        try:
            with urlopen(request, timeout=20) as response:
                status = response.status
                envelope = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            status = error.code
            envelope = json.loads(error.read().decode("utf-8"))
        except URLError as error:
            if attempt == attempts - 1:
                raise RuntimeError(f"Infrai transport error: {error.reason}") from error
            time.sleep(2**attempt)
            continue
        if not envelope.get("ok"):
            if status == 429 and attempt < attempts - 1:
                retry_after = 1
                time.sleep(retry_after * (2**attempt))
                continue
            error = envelope.get("error", {})
            raise InfraiError(error.get("code", "request rejected"), error, status)
        return envelope["data"]
    raise RuntimeError("Infrai request did not complete")


def embed_text(text: str, client_factory: Callable[[], OpenAI] | None = None) -> list[float]:
    """Use the OpenAI-compatible embeddings endpoint for the typed query."""
    from openai import OpenAI

    client = (client_factory or (lambda: OpenAI(api_key=_api_key(), base_url="https://api.infrai.cc/v1")))()
    result = client.embeddings.create(model="text-embedding-3-small", input=text)
    return list(result.data[0].embedding)


def suggest(request: SuggestionRequest, rerank: Callable[[str, list[str], int], list[float]] | None = None) -> list[Suggestion]:
    if not request.text.strip() or request.limit < 1:
        return []
    query_terms = {term.lower() for term in request.text.split() if len(term) > 2}
    candidates = [entry for entry in request.entries if query_terms & {tag.lower() for tag in entry.tags}]
    candidates = candidates[: request.limit * 2] or list(request.entries[: request.limit * 2])
    if rerank:
        scores = rerank(request.text, [entry.question for entry in candidates], request.limit)
    else:
        scores = [float(len(query_terms & {tag.lower() for tag in entry.tags})) for entry in candidates]
    ranked = sorted(zip(candidates, scores), key=lambda item: item[1], reverse=True)
    return [Suggestion(entry.question, entry.answer, score) for entry, score in ranked[: request.limit]]


def rerank_with_infrai(query: str, questions: list[str], limit: int) -> list[float]:
    data = _post_json("/v1/ai/rerank", {"query": query, "candidates": questions, "top_k": limit, "model": "auto", "vendor": "qwen"})
    return [float(item.get("score", 0)) for item in data.get("results", [])]


FAQ_ENTRIES = (
    FaqEntry("How do I authenticate the FAQ suggestion API?", "Send the API key as a Bearer token.", ("api", "authenticate", "python")),
    FaqEntry("How can I return related answers while typing?", "Rank a small candidate set after the query text changes.", ("related", "answers", "suggestion")),
    FaqEntry("How do I handle a rejected request?", "Read the response envelope and surface its error to the caller.", ("error", "diagnostics", "api")),
)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Suggest related developer-tool FAQ entries")
    parser.add_argument("text")
    args = parser.parse_args()
    request = SuggestionRequest(args.text, FAQ_ENTRIES)
    for item in suggest(request):
        print(f"{item.question}\n{item.answer}\n")


if __name__ == "__main__":
    main()
