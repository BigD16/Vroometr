# Assistant tools — thin adapters over domain services for the future agent.

Read tools live in `read_tools.py`. Mutating tools must declare `write_class`
(`auto` or `confirm`). `registry.py` checks `FLAG_AI_WRITES` and confirmation
flags via `write_policy.py` before running a mutating handler.

| If you want to change… | Open |
| --- | --- |
| Tool list / registration | `factory.py` |
| Tool schemas or handlers | `read_tools.py` |
| Invoke / unknown-tool behavior | `registry.py` |
| Auto vs confirm write rules | `write_policy.py` |
| Shared result shapes | `types.py` |
