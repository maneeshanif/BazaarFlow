# Context templates

Full templates (rendered with `scripts/render.py`): `code-standards.md`, `library-docs.md`, `ui-rules.md`,
`ui-tokens.md`, `ui-registry.md`, `progress-tracker.md`. The three files below are written fresh from the PRD;
this list is their required shape.


`/bootstrap` fills these in from the PRD. Each file below lists the sections it must contain,
mirroring the reference project. Content comes from the PRD; anything the PRD does not answer
is written as an entry in `progress-tracker.md` → Open Questions, never invented.

## project-overview.md
- About the Project (2-3 paragraphs: who it is for, what problem it solves)
- Product Objectives
- Modules & Primary Screens (table: module, screens, feature IDs)
- Feature Priority (P0 / P1 / P2)
- Non-Negotiable Architectural Constraints (the same list that goes into AGENTS.md)
- Deployment Models
- Definition of Done (what the PRD says "accepted" means)

## architecture.md
- Stack (table: layer, technology, why)
- Deployment Units
- Folder Structure (tree of the real repo layout, matching verify.sh lane paths)
- Contract Flow (how types/clients are generated, if the project has an API contract)
- Multi-Tenancy & Scoping (if applicable)
- Authentication & Authorization
- Audit (if applicable)
- Database Conventions and Domains (if the project has a database)
- Performance Targets (from the PRD's non-functional requirements)

## build-plan.md
- Core Principle (how work is sequenced, e.g. UI with mock data first)
- Phase Map (table: phase, scope, exit criteria) taken from the PRD's phases
- Per phase: numbered tasks, each with a feature/form ID from the PRD, acceptance criteria,
  and dependencies. Task 00 is always "record stack decision (ADR) and sign off".

## code-standards.md (template exists — see code-standards.md)
- Engineering Mindset
- The Rules That Cannot Be Broken (5-10 rules, each one enforceable by a test or lint)
- Per-language sections for the chosen stack: layering, conventions, naming
- Error Handling
- Testing (what must be tested; the verification loop = scripts/verify.sh)
- Git & Pull Requests (commit style; CI failure => fix + preventing check)
- AI-Assisted Development Protocol

## library-docs.md
- Before Using Any Library (fetch current docs, prefer project patterns)
- One short section per library actually chosen: version, install, the project's usage pattern, gotchas
- Start with only the chosen stack's libraries; append as new ones are adopted

## ui-rules.md, ui-tokens.md, ui-registry.md (only if the PRD has a UI)
- ui-rules: font, layout, forms & validation, data grid, buttons, feedback, the four states
  (loading/empty/error/populated), responsive, accessibility, "before building any component"
- ui-tokens: design intent, complete token definition (colors, spacing, radius, type), status colors, dark mode
- ui-registry: How to Use + empty Component Inventory (filled by the `imprint` skill)

## progress-tracker.md
See `../progress-tracker.md` in this folder — copy it and fill the placeholders.
