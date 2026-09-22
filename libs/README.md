# Shared Python

Code that both the API and workers need. Keep this small.

| If you want to change… | Open |
| --- | --- |
| Env field names | `libs/vroometr/settings.py` (values in `.env`; names in `.env.example`) |
| Kill-switch flags | `libs/vroometr/flags.py` |
| AI vendor-neutral ports | `libs/vroometr/ai/ports.py` |
| Product rules | `services/api` — not here |

`vroometr/ai/embeddings.py` implements the OpenAI embedding port using HTTPX. The factory
selects it only when provider configuration is present. `ai/reranking.py` implements strict
scored reranking with the same connection; `RankedPassage` preserves the input index and score.
`ai/chat.py` implements OpenAI chat completions with optional tool calls when `AGENT_MODEL` is
set. Other model adapters remain unconfigured. See [indexing setup](../docs/document-indexing.md#configuration)
and [retrieval setup](../docs/document-retrieval.md#configuration-and-migration).
