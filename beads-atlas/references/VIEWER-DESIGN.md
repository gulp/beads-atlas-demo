# Viewer design contract

Load this when changing the Atlas UI or when a user asks for a materially different visualization rather than a straight regeneration.

## Product goal

Atlas is a planning instrument, not a decorative graph. A user should be able to answer quickly:

- What can start now?
- What blocks the most downstream work?
- What is the longest execution chain?
- Where does a selected issue sit in hierarchy and execution flow?
- Which workstreams can proceed independently?
- Is a strange-looking graph a real cycle/data problem or merely a different relation lens?

## Core surfaces

Keep these unless the user's goal explicitly makes one irrelevant:

- **Plan / Execute / Structure / All lenses**.
- Relation-type, status, type, priority, and label filters.
- Search across issue ID/title/labels/description.
- Ready-work, critical-path, and bottleneck/high-fan-out analysis modes.
- Click inspector with full issue metadata, description, acceptance criteria, upstream/downstream relations, and raw record.
- Dependency-neighborhood focus/trace controls.
- D3 pan/zoom, explicit zoom controls, fit-to-screen, and synchronized minimap.
- Directed arrowheads and visually distinct relationship styles.
- Optional hierarchy/workstream contours where they help orientation.
- Drag/drop and file input so the same artifact can inspect a new graph without regeneration.

## Interaction principles

- **Click selects; double-click focuses.** Selection must not unexpectedly discard the rest of the graph.
- Keep hover transient and selection persistent.
- Search should highlight matches and support next/previous navigation rather than filtering all unmatched nodes by default.
- Fit-to-screen must account for the actual rendered graph bounds and current viewport, not a hard-coded scale.
- Minimap is navigation, not a second graph; simplify it enough to remain legible.
- Filters may make a once-acyclic projection cyclic or disconnected; rerun topology validation after filters/lens changes.

## Visual hierarchy

Use color for state/type emphasis, not as the sole carrier of meaning. Relationship types also use dash patterns. Keep node labels readable before showing metadata. A selected/critical/ready state must remain visible on dark backgrounds and at fit-to-screen zoom.

## Inspector safety

Issue text is untrusted content. Render escaped text first and apply only narrowly controlled lightweight formatting. Never feed issue descriptions/labels/titles to `innerHTML` without escaping. The current Markdown-ish renderer escapes before converting backticks/bold markers.

## Generic graph behavior

Generic nodes may not have Beads metadata. Controls and inspector must degrade gracefully:

- missing status -> `open` display default;
- missing issue type -> `node`;
- missing priority -> no priority;
- labels/description optional;
- ready-work and Beads-specific wave semantics should not pretend to exist unless they are meaningful.

## Do not overfit to one repository

No repo names, issue prefixes, label taxonomies, fixed counts, or project-specific statuses belong in the template. Dataset identity is injected by the build script.
