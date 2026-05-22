# Tracker V2 Contract (Phase 1)

Status: accepted (implementation target for subsequent phases)

## Scope

Phase 1 defines architecture and handler contracts for the migration from a single global tracker to a multi-tracker system where each tracker instance is bound to a rotator.

This document is intentionally contract-first. Runtime internals are updated in later phases.

## Core Decisions

1. Tracker identity is mandatory in contracts.
   - `tracker_id` is required on all tracker-related requests/events.
   - Backward compatibility during migration may default to `tracker_id="default"` in handlers.

2. Tracking becomes instance-scoped.
   - No contract assumes a single global tracking context.
   - All tracking updates, command statuses, and UI tracker values are tied to a tracker instance.

3. One tracker instance owns one rotator at a time.
   - Ownership conflicts are resolved server-side.
   - A rotator cannot be actively controlled by multiple tracker instances.

4. Frontend target flow is rotator-first.
   - "Set as Target" opens a rotator-selection dialog.
   - Target selection only completes after a rotator is chosen.

## Event Contract (v2)

- `satellite-tracking-v2`
  - Required: `tracker_id`
  - Optional payload keys: `tracking_state`, `satellite_data`, `rotator_data`, `rig_data`, `events`

- `ui-tracker-state-v2`
  - Required: `tracker_id`
  - Contains UI selection payload for the corresponding tracker instance

- `tracker-command-status`
  - Required: `tracker_id`, `command_id`, `status`

## API / Handler Contract Changes

- Tracking read/write handlers accept `tracker_id` in request payload.
- Tracking responses include `tracker_id`.
- Legacy names/events may coexist only as transitional transport wrappers; the canonical contract is v2 with `tracker_id`.

## Naming Contract for Persistence

- Canonical tracking-state name format:
  - `satellite-tracking:<tracker_id>`
- Transitional default instance:
  - `tracker_id = "default"`

## Out of Scope for Phase 1

- Multi-process tracker supervisor implementation
- DB schema/data migrations
- Full frontend state model rewrite
- Final regression/e2e testing

These are handled in subsequent phases.
