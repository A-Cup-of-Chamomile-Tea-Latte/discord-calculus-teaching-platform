# Task matrix and parallelization

> M3 status: Tasks 02–34 are complete for their authorized fixture/local scope. This matrix remains the historical execution dependency record; current status and production blockers are in [M3 任務台帳](README.md) and [`docs/IMPLEMENTATION_STATUS.md`](../docs/IMPLEMENTATION_STATUS.md).

## Prerequisite chain

`02 → 03 → 04 → 05 → 06 → 07 → 08`

After Task 08, four lanes may proceed in parallel **only in separate branches/worktrees**:

| Lane | Tasks | Primary paths |
|---|---:|---|
| Portal | 09–14 | `apps/portal`, portal docs |
| GAS / Sheets | 15–19 | `apps/gas`, Sheets docs |
| Discord bots | 20–25 | `bots`, bot tests |
| Local export | 26–28 | `tools`, export fixtures |

Then run:

`29 → 30 → 31 → 32 → 33 → 34`

Task 34 is a fixture-only follow-up package driven by the preserved 2026-07-23 product-decision handoff. Its internal engineering lanes may run in parallel when they keep packaging/Case ID, Portal/projection, and data/bot/provisioning paths separate; the root gates and fresh-extraction packaging verification remain a single final integration step.

## Safe overnight recommendation

For one Codex session, start with `BATCH_A_FOUNDATION.md`. It is the most valuable unattended batch because later tasks depend on its contracts and fixtures.

After Batch A succeeds, run Batches B–E in separate sessions/worktrees. Run Batch F only after merging/reconciling the lanes.

## Conflict policy

A lane should not edit another lane's primary directory except:
- shared contracts through a deliberate contract change;
- fixtures through a deliberate fixture change;
- its own task report;
- documentation explicitly named in the task.

If a contract change is required, stop implementation, propose the change in the report, and update the contract only through a dedicated follow-up or a clearly documented atomic commit.
