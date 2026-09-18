# Assistant tools — thin adapters over domain services for the future agent.

Read tools live in `read_tools.py`. The registry rejects mutating tools until write
policy (5.4). Call the same services HTTP uses; do not add SQL here.

| If you want to change… | Open |
| --- | --- |
| Tool list / registration | `factory.py` |
| Tool schemas or handlers | `read_tools.py` |
| Invoke / unknown-tool behavior | `registry.py` |
| Shared result shapes | `types.py` |
