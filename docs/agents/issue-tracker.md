# Issue tracker: Local Markdown

Issues and specs live as Markdown files under `.scratch/`. Do not publish them to GitHub Issues.

## Conventions

- Use one directory per feature: `.scratch/<feature-slug>/`.
- Store the spec at `.scratch/<feature-slug>/spec.md`.
- Store each implementation ticket at `.scratch/<feature-slug>/issues/<NN>-<slug>.md`, numbered from `01`. Keep tickets in separate files.
- Record triage state as a `Status:` line near the top of each issue file. Use the role strings in `triage-labels.md`.
- Append comments and conversation history under a `## Comments` heading.

## Publishing and fetching

When a skill says "publish to the issue tracker", write the spec or individual ticket at the corresponding path above, creating directories as needed.

When a skill says "fetch the relevant ticket", read the referenced file. Resolve ticket numbers within the relevant feature directory. Ask when the feature is ambiguous.

## Wayfinding operations

For `/wayfinder`, use a map file with one child file per ticket.

- **Map**: `.scratch/<effort>/map.md`, containing Notes, Decisions-so-far, and Fog.
- **Child ticket**: `.scratch/<effort>/issues/<NN>-<slug>.md`, numbered from `01`, with the question in the body and a `Type:` line containing `research`, `prototype`, `grilling`, or `task`.
- **Lifecycle**: Wayfinder uses `Status: open`, `Status: claimed`, and `Status: resolved` instead of triage roles for its child tickets.
- **Blocking**: Record `Blocked by: NN, NN` near the top. A ticket is unblocked when every listed ticket is resolved.
- **Frontier**: Choose the first open, unblocked, unclaimed ticket by number.
- **Claim**: Set `Status: claimed` and save before starting work.
- **Resolve**: Append the answer under `## Answer`, set `Status: resolved`, and append a summary with a link to the map's Decisions-so-far.
