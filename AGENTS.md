# Kung-Fu Chess — Agent Instructions

## 1. Scope and Purpose

These instructions apply to the entire repository.

`AGENTS.md` defines how coding agents work in this project. It does not replace the project requirements, current status, or historical record.

The project documents have distinct responsibilities:

- `PROJECT_CONTEXT.md` contains stable requirements, architectural boundaries, and confirmed decisions.
- `PROJECT_STATUS.md` contains the verified current repository state, open work, and current risks.
- `PROJECT_RECORD.md` is the append-only chronological decision and material-intake record.
- `README.md` contains developer and user instructions.
- `docs/project_rules.md` is binding project guidance unless a later explicit decision in `PROJECT_CONTEXT.md` overrides it.
- `docs/Clean-Code-Cheatsheet.md` is supporting reference material rather than a higher-priority source of truth.

## 2. Required Reading

Before modifying source code or tests:

1. Read `PROJECT_CONTEXT.md`.
2. Read `PROJECT_STATUS.md`.
3. Inspect the relevant implementation and tests.
4. Read the relevant parts of `PROJECT_RECORD.md` when a decision, conflict, or historical reason needs clarification.

For a small documentation-only change, read the documents directly affected by the request and enough surrounding context to preserve consistency.

Do not present commit, test, coverage, branch, or working-tree information as current without verifying it.

## 3. Source-of-Truth Order

When sources conflict, use this order:

1. Latest explicit user decision
2. Latest official assignment or reviewer requirement
3. Latest recorded project decision
4. Current implementation and tests
5. Current project status
6. Older conversations, summaries, and historical records

`AGENTS.md` governs agent workflow. `PROJECT_CONTEXT.md` governs project and domain decisions.

If a meaningful conflict or ambiguity remains after checking the available sources, do not invent a requirement. Explain the conflict and ask the user.

Do not create new project rules from assumptions. New rules must come from the user or an authoritative project source.

## 4. Language and Communication

- Communicate with the user in Hebrew unless the user explicitly requests another language.
- Write source code, identifiers, comments, docstrings, tests, branch names, commit messages, and technical documentation in English.
- Distinguish verified facts, requirements, recommendations, and assumptions.
- Do not describe an unverified assumption as an approved requirement.
- Final reports should state the outcome, changed files, verification performed, and any remaining risks or unverified items.

## 5. Authorization and Task Scope

- A request to review, explain, diagnose, or report does not authorize source-code changes.
- A request to implement or change authorizes only the focused changes needed for that request.
- Material intake does not authorize source-code changes unless implementation is explicitly requested.
- Preserve existing user changes and unrelated work.
- Report unrelated defects instead of fixing them unless they directly block the requested work.
- A small adjacent refactor is allowed when it is directly necessary for correctness, architecture, readability, or testability of the requested change.
- Do not expand the task into a general rewrite.
- Do not install dependencies without approval.
- Do not edit binary assets unless the request explicitly includes a visual or asset change.
- Do not use sub-agents or parallel agent delegation unless the user explicitly requests it or a later authoritative instruction explicitly permits it.

## 6. Engineering Priorities

Architecture and design quality are the highest project priority, while correctness remains mandatory.

Preserve:

- Single Responsibility Principle
- Encapsulation
- DRY business rules
- Clear ownership of mutable state
- Clear dependency direction
- Small focused methods
- Meaningful naming
- Minimal public APIs
- Deterministic behavior
- Explicit state transitions
- One authoritative owner for each rule and transition

Avoid:

- Over-engineering
- Premature abstraction
- Premature optimization
- Hidden side effects
- Multiple sources of truth
- UI-owned game legality
- Duplicated timing mechanisms
- Access to another component's private representation
- Speculative future functionality
- Large unrelated rewrites

A new class or abstraction is justified only when it solves a current demonstrated problem and has a clear responsibility.

If architecture and correctness appear to conflict, stop and explain the conflict rather than sacrificing either one silently.

## 7. Architectural Boundaries

Follow the layer ownership defined in `PROJECT_CONTEXT.md`.

In particular:

- The model owns core entities and settled game state.
- The rules layer owns action legality.
- The real-time layer is the single authority for timed movement, jumps, arrivals, activity, and rest.
- The engine coordinates authoritative results and events.
- The input/controller layer owns input translation and selection.
- The UI owns presentation only.
- Text parsing and script infrastructure remain boundary adapters.
- Consumers must use public board, engine, and snapshot APIs rather than private state.
- Presentation and animation must not determine final game state.

Do not implement future binary storage or user-defined games unless the user explicitly requests the relevant future feature.

## 8. UI and Graphics Rules

- Route every displayed graphical element through the supplied `Img` abstraction.
- Keep direct OpenCV usage confined to `kungfu_chess/ui/img.py`.
- Do not introduce PyGame, SFML, LWJGL, or another competing graphics abstraction.
- Rendering and input mapping must share authoritative board geometry.
- The application-provided default player names are `White Player` and `Black Player`.
- The current requirement does not include user-entered player names or a name-entry workflow.
- Apply the Observer design pattern only when a genuine current one-to-many notification relationship needs it.
- Do not add Observer mechanically, create spectator mode, or introduce a broad event framework merely to satisfy the pattern name.
- A focused Observer review may correctly conclude that no new Observer implementation is currently needed.

## 9. Testing Rules

- Run tests with Pytest.
- Write all new tests in native Pytest style.
- Do not add new `unittest.TestCase` tests.
- When touching an old `unittest` test file, migrate only the focused relevant area when the migration remains small and does not expand the task materially.
- Do not use `unittest.mock.patch`, `patch.object`, Pytest `monkeypatch`, or equivalent runtime replacement of code under test.
- Use dependency injection, fakes, stubs, or explicit collaborators instead.
- Keep tests deterministic and behavior-oriented.
- Prefer assertions on public observable behavior.
- Do not modify a valid test merely to make an incorrect implementation pass.
- Avoid duplicate tests that add no meaningful coverage.

For meaningful code changes:

1. Run focused tests.
2. Run the complete Pytest suite.
3. Measure coverage when the change is significant or the task specifically concerns coverage.
4. Record exact commands and results.

Aim strongly for 100% meaningful unit-test coverage, but do not add low-value tests merely to increase a percentage. No hard numeric coverage gate is currently defined.

Do not declare Ruff or Pyright mandatory completion checks until the repository provides an agreed reproducible workflow for them.

## 10. Dependencies and Generated Files

- Do not install or add dependencies without approval.
- A future focused task may add `coverage` or `pytest-cov` and a reproducible coverage configuration.
- Do not intentionally edit or commit generated caches, virtual environments, or coverage output.
- Avoid changes to `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, `.coverage*`, `htmlcov/`, and local virtual-environment directories.

## 11. Git Safety and Workflow

- Check Git status before and after work.
- Preserve unrelated tracked, staged, and untracked user changes.
- Do not use `git reset --hard`, destructive checkout, or equivalent destructive recovery commands.
- Do not force push without explicit approval and justification.
- Do not create a branch unless the user requests branch work or the requested workflow clearly requires it.
- Do not commit, push, merge, open a pull request, or delete a branch without explicit authorization for that action.
- Keep changes focused and do not stage unrelated files.
- Documentation may be committed with the implementation or in a separate focused documentation commit, but `PROJECT_STATUS.md` must not remain knowingly incorrect after the related work is merged.

## 12. Project Documentation Updates

Update project documents only when their owned information changes:

- Stable requirement, architecture, or confirmed decision: update `PROJECT_CONTEXT.md`.
- Current repository state, current verification, open work, or current risk: update `PROJECT_STATUS.md`.
- New official material, user decision, correction, superseded status, or completed intake: append a new entry to `PROJECT_RECORD.md`.

Do not rewrite historical record entries merely because their former current state is now obsolete. Append a new entry that supersedes them.

Do not update every project document mechanically. Update only the files whose owned information changed.

Transient measurements must identify the relevant date and commit. Do not carry an old coverage or test result forward as a current result.

## 13. Completion Criteria

Before reporting a code change as complete, verify that:

- The requirement is defined clearly.
- Responsibility is assigned to the correct layer.
- The implementation is focused and readable.
- Relevant native-Pytest tests exist.
- No prohibited monkey patching was introduced.
- Focused tests pass.
- The complete suite passes when it can be run.
- Coverage was considered when appropriate.
- The diff contains only intended changes.
- No unrequested future feature was introduced.
- Git state is safe and verified.
- Relevant project documentation is current.
- Remaining risks and unverified items are reported explicitly.
