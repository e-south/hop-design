---
doc_id: hop-github-governance
title: GitHub governance contract
intent: Define public repository settings, required checks, and review boundaries.
audience:
  - maintainers
  - security reviewers
owner: HOP Design maintainers
status: active
last_verified: 2026-08-20
---

# GitHub governance contract

## Main-branch rule

`main` accepts changes through pull requests. The rule requires strict status
checks named `Checks`, `Dependency review`, and `CodeQL`, resolved
conversations, linear history, and administrator enforcement. Force pushes and
branch deletion are disabled.

The initial repository seed is the one exception: GitHub cannot protect a
branch that does not yet exist. Protect `main` immediately after that push.
For a single-maintainer repository, zero approving reviews avoids making every
pull request impossible to merge. Review comments and automated review remain
useful evidence but do not replace required tests.

## Repository security

- Workflow permissions default to read-only.
- Actions are restricted to full-length commit SHA pins.
- A committed, SHA-pinned CodeQL workflow analyzes Python with the extended
  query suite and exposes one stable `CodeQL` job. GitHub scans workflow files
  through its Actions security analysis.
- Dependency graph, Dependabot alerts and security updates, secret scanning,
  and push protection are enabled when the account plan exposes them.
- Private vulnerability reports use GitHub Security Advisories.

Repository settings are server-owned controls. The workflows and Dependabot
configuration in the repository make most intent reviewable, while settings
must be re-audited through the GitHub API.

## Hosted evidence

Local verification establishes macOS source and clean-wheel behavior. It cannot
establish Linux behavior, GitHub token permissions, workflow context names, CodeQL
database creation, dependency-review access, fork behavior, or branch-rule
enforcement. If Actions is unavailable because of billing or quota, keep the
rules fail closed and record those checks as pending. Do not describe the
repository as release-ready until one hosted run passes.

Codex code review is configured separately in ChatGPT/Codex after the GitHub
repository is connected. `@codex review` and automatic review may add findings;
they do not grant merge permission or replace branch protection.
