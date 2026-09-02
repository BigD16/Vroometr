# Shared Python

Code that both the API and workers need. Keep this small.

| If you want to change… | Open |
| --- | --- |
| Env field names | `libs/vroometr/settings.py` (values in `.env`; names in `.env.example`) |
| Kill-switch flags | `libs/vroometr/flags.py` |
| AI vendor-neutral ports | `libs/vroometr/ai/ports.py` |
| Product rules | `services/api` — not here |
