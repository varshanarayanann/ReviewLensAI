# AI-Assisted Development and Review

This document defines how the ReviewLens team uses AI coding tools. AI-generated
code is team-authored code: it must meet the same engineering standards,
Definition of Done, and merge requirements as code written without AI assistance.
AI output is a suggestion, not an authority.

## Approved tools

- GitHub Copilot in VS Code is the team's default AI coding assistant.
- Get team approval before using another AI coding tool with project code or
  project data. Use only a team-approved account and configuration that meet the
  project's confidentiality and data-handling requirements.
- Do not submit secrets, credentials, personal data, customer data, or other
  restricted information to an AI tool. Do not ask a tool to copy proprietary
  code or undocumented content from unrelated projects.

## Context to provide

Give the tool enough project-specific information to make a bounded change:

- The issue or task, intended behavior, acceptance criteria, and relevant
  business rules.
- Relevant source files, existing patterns, architecture and security
  constraints, and applicable project context documents.
- Expected interfaces, compatibility requirements, and error-handling behavior.
- The tests and quality checks that should cover the change.

Ask for focused changes and identify what must not change. Check the tool's
suggestions against the repository and trusted project documentation; do not
assume generated context or claims are accurate. Supply only information the
tool is approved to process.

## Human review

The contributor remains responsible for every generated or AI-modified line.
Before requesting approval, review the complete diff and confirm that:

- The implementation meets the task and acceptance criteria and follows
  repository conventions.
- The behavior, edge cases, error paths, and security implications are
  understood; no generated code, tests, comments, or configuration are accepted
  solely because they look plausible.
- No unrelated changes, secrets, or unintended data collection were introduced.
- Tests meaningfully verify behavior, including failure and boundary cases where
  relevant.

A reviewer must independently review the change as they would any team-authored
code. AI review comments can help identify questions but do not replace human
approval or required code-owner review.

## Dependencies and APIs

Before adding an AI-suggested dependency or using an unfamiliar API:

1. Prefer existing project functionality when it meets the need. Explain the
   need for any new dependency and obtain the same approval required for other
   dependency changes.
2. Verify the package, maintainer, version, license, support status, security
   posture, and compatibility using authoritative sources. Check the package
   manager's resolved metadata and update the appropriate lockfile.
3. Verify API names, signatures, behavior, version compatibility, and
   deprecation status in official documentation or source. Do not rely on
   generated examples as evidence.
4. Test the actual integration and review the resulting dependency and lockfile
   diff before merge.

## Required validation

Run the relevant existing formatter, linter/static analysis, type checks, and
automated tests for the changed code. Add or update tests for changed behavior;
include unit and integration coverage as appropriate, and exercise relevant
authorization, error, and boundary cases. Run the broader required CI checks
before merge.

Review generated tests for meaningful assertions and ensure they fail when the
behavior is incorrect. Fix failures caused by the change; do not skip, weaken, or
remove checks to make the change pass. Report checks that could not be run and
why in the pull request. Do not claim a check passed unless it actually ran
successfully.

## AI session record

For each pull request containing AI-assisted work, disclose in the pull request
description:

- The AI tool used and, when available, its model.
- Which parts of the work were AI-assisted and what the contributor changed or
  verified.
- The validation commands run and their results.

Retain the relevant AI session transcript with the pull request using the
project's approved, access-controlled GitHub storage (for example, a pull
request attachment). Link it from the description. If the tool cannot export a
transcript, record the task prompt and a concise summary of the material
suggestions used and verification performed. Redact secrets and restricted
information before retention. Do not commit raw transcripts to the source tree
unless the team explicitly approves it.

## Additional security review

Request security review in addition to normal code review when AI-assisted
changes affect or introduce:

- Authentication, authorization, identity, ownership, or tenant isolation.
- Handling, storage, logging, or transmission of secrets or sensitive data.
- Input validation, query construction, file access, serialization, or other
  trust boundaries.
- Cryptography, security configuration, permissions, or deployment controls.
- Dependencies, external services, or APIs that materially change the attack
  surface.

Security review is also required whenever a contributor or reviewer cannot
explain the security properties of the generated change. Do not merge until
identified security concerns are resolved and the applicable security checks
pass.

## Merge gate

AI-assisted changes may be merged only after the contributor has reviewed and
validated the full diff, required tests and checks pass (or an exception is
explicitly approved under project policy), required human approvals are
recorded, and the pull request includes the AI session record above. All normal
project Definition of Done requirements continue to apply.
