# PredictRx Codex Starter Pack

This pack contains the project-level guardrails, full product blueprint, a reusable Codex skill, and the first task prompt.

## Recommended installation

1. Unzip this folder.
2. Copy `AGENTS.md` and `PREDICTRX_MASTER_SPEC.md` into the root of the existing PredictRx repository.
3. Copy the `.agents/skills/predictrx-product/` folder into the same relative location in the repository.
4. Open the repository in Codex.
5. Paste the contents of `START_HERE_PROMPT.md` as the first task.

If the repository already has an `AGENTS.md`, do not overwrite it blindly. Merge the PredictRx-specific guardrails while preserving existing repository instructions.

## Files

- `AGENTS.md` — persistent project guardrails and non-negotiable constraints.
- `PREDICTRX_MASTER_SPEC.md` — full product, design, routing, security, data-boundary, licensing, legal-readiness and implementation specification.
- `.agents/skills/predictrx-product/SKILL.md` — reusable project skill for future Codex tasks.
- `START_HERE_PROMPT.md` — initial audit-and-build instruction to paste into Codex.

## Important

The specification describes the target product. Codex must inspect the actual repository and distinguish implemented, partial, mocked and missing capabilities. It must not pretend the current research prototype is already a clinically validated or regulator-authorized production system.
