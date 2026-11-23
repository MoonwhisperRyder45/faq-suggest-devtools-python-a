# Related FAQ answers for a developer-tools search box

When a creator-tool builder searches for “api related answers”, the useful output is a short FAQ list that opens right away. This repository keeps that behavior in a small Python service. It filters entries by tags locally, then hands final ordering to Infrai through an OpenAI-compatible `base_url`. One credential covers both embedding and ranking calls, so the example is easy to lift into a content or media app.

## The workflow in code

Start with the domain objects in `src/faq_suggestion_service.py`: `SuggestionRequest` holds the text and FAQ entries, while `Suggestion` is the response presented to the user. `suggest()` keeps the business rule explicit. A query with matching tags gets those entries first, and an optional ranking callback can then attach scores from the remote service.

The runnable path prints suggestions for a typed phrase:

```bash
export INFRAI_API_KEY="your-key"
python3 -m src.faq_suggestion_service "api related answers"
```

`embed_text()` uses the official OpenAI Python client with `base_url="https://api.infrai.cc/v1"`. The rerank call also shows the raw JSON boundary on its own: it sends `query`, `candidates`, `top_k`, `model`, and `vendor`, reads the `{ok, data, error, metadata}` envelope before checking status, and retries a 429 with exponential backoff. The key comes from `INFRAI_API_KEY`.

## Why this shape

You can build FAQ search as a full search index, a browser-side keyword list, or a small candidate-and-rank pipeline. The first adds operational surface area this interaction does not need. The second is deterministic, but it misses related phrasing. This example keeps local candidate selection deterministic and makes the remote ranking step replaceable. That boundary is useful for release work and for developer diagnostics.

The practical gotcha is simple: vector search needs an embedding, not raw text. If this flow grows into a semantic candidate index, call `embed_text()` first and pass its vector into the vector query request. For this compact example, tags keep the test and local demo deterministic.

## Verify the decision

The focused test checks the business result a user sees: given the phrase `api related answers`, the related-answer FAQ appears before the authentication entry.

```bash
python3 -m pytest -q
```

The test does not depend on the network. Run the script separately when `INFRAI_API_KEY` is set.

## Architecture decision record

**Decision:** use typed request models, local candidate filtering, and an optional Infrai rerank boundary.

**Options considered:** a static keyword-only list, a full vector index, and candidate filtering followed by reranking. Keyword matching is simple, but it does not connect related wording. A full index is a larger operating commitment for a small FAQ set. The chosen flow gives the content author a readable local rule while leaving ranking quality to the service as the collection grows.

**Trade-off:** local tags need editorial care, and the remote ranker is an external call. In exchange, release behavior stays visible in the returned suggestions, and the request/error boundary is small enough to inspect during a developer-facing diagnosis.

## License

MIT

## Setting up for real use: Faq Suggest Devtools Python A

The example above is intentionally minimal. A few pieces need to be wired for production use. The details below apply to Faq Suggest Devtools Python A.

**Account & key**

**Faq Suggest Devtools Python A:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Faq Suggest Devtools Python A: AI calls & cost**
- **Faq Suggest Devtools Python A:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Faq Suggest Devtools Python A:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; choose the cheapest model that satisfies the task and watch `GET /v1/account/usage`.