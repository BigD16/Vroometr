# ADR 0001: Model electric powertrains explicitly

## Status

Accepted — 2026-09-08

## Context

The original bike profile assumed every machine had combustion displacement and a 2T/4T
stroke cycle. Vroometr also needs to represent electric motorcycles and dirt bikes without
inventing combustion specifications.

## Decision

- Store `powertrain_type` as `combustion` or `electric`.
- Require positive displacement and a 2T/4T stroke cycle for combustion bikes.
- Require displacement and stroke cycle to be absent for electric bikes.
- Backfill existing bikes as combustion without changing their facts.
- Default new bike unit preferences to metric without rewriting existing preferences.

The domain service and PostgreSQL constraints both enforce valid powertrain configurations.

## Consequences

Electric profiles do not currently store motor power or battery capacity. Those fields can be
added later when their product requirements are defined. API clients that omit
`powertrain_type` remain compatible and create combustion bikes.
