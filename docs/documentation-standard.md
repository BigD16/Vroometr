# Documentation completion standard

Documentation is part of completing every task. A developer must be able to continue the work
from repository files without the previous chat, an external IDE plan, or temporary artifacts.
Scale detail to the task: a small fix needs a short entry; a feature needs an implementation
handoff. Documentation-only tasks follow the same standard without redundant new guides.

## Required updates

Before marking a task complete:

1. Update [implementation progress](implementation-progress.md) with the task, date, resulting
   behavior, checks actually run, limitations, and remaining work. Keep the status summary
   current, and update the matching status on the [roadmap](roadmap.md) when a numbered
   task or phase advances.
2. Update the affected subsystem README and any relevant sections of the
   [developer guide](developer-guide.md) or [runbook](development-runbook.md). Correct outdated
   instructions where they live rather than appending contradictory notes.
3. Document new or changed API contracts, data relationships, invariants, permissions, failure
   and retry behavior, migrations, configuration key names, and dependencies where applicable.
4. Provide a file reading order and manual verification steps for meaningful features. Use
   repository-relative links and explain the rule each important file owns.
5. Add an ADR when an approved architectural decision needs a durable rationale. LOCKED design
   decisions still govern implementation; documentation does not authorize changing them.
6. Check links, paths, commands, status claims, and `git diff --check`. Run appropriate product
   checks when code changes; do not rerun the application suite solely for prose edits.
7. Include the documentation links in the final handoff.

Record “none” or “not applicable” for migrations/config/dependencies when relevant to a handoff;
do not create empty boilerplate sections for tiny edits. If a guide needs no change, record why
in the progress entry or completion summary. The rule is to review documentation after every
task and make necessary updates, not to duplicate the entire implementation in multiple files.

## Handoff entry template

```markdown
## <Task number/name> — <date>

Status and behavior: what now works, what changed, and why.

Architecture and reading order: entry point → service → persistence/adapters → UI;
link important files and identify the types/functions that own the rules.

Rules and failures: ownership, validation, state transitions, retries, deletion effects,
and known limits. Separate implemented behavior from planned behavior.

Setup: migrations, dependency changes, environment key names, and restart requirements.
State whether local migrations were actually applied.

Verification: commands actually run and outcomes; identify skips, mocks, warnings, and
manual-only coverage. Link checked-in tests. Do not present old results as a fresh run.

Manual review: concrete steps and expected results.

Remaining work: unresolved issues, next task, and documentation updated.
```

Never document secrets or real environment values. Do not publish ignored design documents
without authorization. Describe existing gaps candidly: a stub, mock, unconfigured adapter,
or temporary manual test is not a completed production capability.

The interactive developer handoff/teach-back workflow in
[the Cursor handoff rule](../.cursor/rules/50-developer-handoff.mdc) remains separate. Written
documentation must be complete before handing the task back; it must not depend on a chat
answer to become useful to another developer.
