# Domain docs

This repo uses a single-context layout.

## Before exploring

- Read `GLOSSARY.md` at the repo root if it exists.
- Read ADRs under `docs/adr/` that concern the area you are working in.

If these files or directories do not exist, proceed silently. Do not suggest creating them upfront. The domain-modeling skill creates them when terms or decisions are resolved.

## File layout

- `GLOSSARY.md`: shared domain terminology.
- `docs/adr/<NNNN>-<decision-slug>.md`: architecture decisions.

## Use the glossary's vocabulary

Use defined domain terms in issue titles, proposals, hypotheses, code, and tests. Avoid synonyms the glossary explicitly rejects.

If a needed concept is absent, reconsider whether the term belongs in the project. Note genuine terminology gaps for domain-modeling.

## Flag ADR conflicts

If a proposal contradicts an existing ADR, identify the ADR and explain why the decision should be reopened rather than silently overriding it.
