# Assistant tools — thin adapters over domain services for the future agent.

Read tools live in `read_tools.py`. Mutating tools must declare `write_class`
(`auto` or `confirm`). `registry.py` checks `FLAG_AI_WRITES` and confirmation
flags via `write_policy.py` before running a mutating handler.
`citations.py` decides whether exact critical values may be stated, how Sources
chips are shaped, and when to escalate to a mechanic.
Hierarchical memory tools call `HierarchicalMemoryService` (search summaries,
then expand raw spans).

| If you want to change… | Open |
| --- | --- |
| Tool list / registration | `factory.py` |
| Tool schemas or handlers | `read_tools.py` |
| Invoke / unknown-tool behavior | `registry.py` |
| Auto vs confirm write rules | `write_policy.py` |
| Withhold / cite / escalate rules | `citations.py` |
| Summary search / span expand | `../services/hierarchical_memory.py` |
| Shared result shapes | `types.py` |
