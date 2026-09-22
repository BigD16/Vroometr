# Developer documentation

Start here when joining Vroometr or resuming work without the previous conversation.

1. [V1 roadmap](roadmap.md): numbered phase/task sequence and current status. Next task is 5.1.
2. [Developer guide](developer-guide.md): what exists, how requests move through the system,
   important rules, data relationships, and where to make changes.
3. [Development runbook](development-runbook.md): setup, migrations, verification, and troubleshooting.
4. [Implementation progress](implementation-progress.md): feature handoffs, verification history,
   and outstanding work for completed tasks. Current implementation is through 5.5 citations + safety.
5. [Documentation standard](documentation-standard.md): required updates before finishing a task.
6. [Architecture decision records](adr/README.md): explanations of approved design changes.

Read the repository [agent instructions](../AGENTS.md) and applicable
[Cursor rules](../.cursor/rules/) before changing code.

## Sources of truth

The [roadmap](roadmap.md) is the planned V1 sequence. The implementation guide describes the
code that exists. The progress log records completed work and its verification. None of these
replace the LOCKED product and architecture decisions in local `docs/design/DESIGN.md`,
`ARCHITECTURE.md`, `DATA_MODEL.md`, and `OPERATIONS_AND_POLICY.md`.

`docs/design/` is intentionally ignored by Git. A fresh checkout will not contain these files;
obtain the approved design documents from the project owner before making product or architecture
decisions. The roadmap and guides are in the repository so onboarding does not depend on chat
history or an external Cursor plan. Do not publish private design files as part of routine
documentation maintenance.

Subsystem details remain in the [API](../services/api/README.md),
[web](../apps/web/README.md), [shared Python](../libs/README.md),
[workers](../workers/README.md), [pipelines](../pipelines/README.md),
[infrastructure](../infra/README.md), and [tests](../tests/README.md) READMEs.
