# Kung-Fu Chess — Project Record

Last updated: 2026-07-28

## Record Policy

This file is the append-only project decision and material-intake record.

Each entry should identify:

- Date
- Source
- Authority
- Extracted requirements
- Clarifications
- Corrections
- Recommendations
- Examples
- Reviewer feedback
- Administrative information
- Conflicts or superseded information
- Unresolved ambiguities
- Required project actions
- Files updated

Stable active context belongs in `PROJECT_CONTEXT.md`.

Transient current state belongs in `PROJECT_STATUS.md`.

## 2026-07-19 — Documentation Baseline Contained in Uploaded Summary

### Source

`המשך פרויקט סיכום דרישות.txt`

### Authority

Historical project summary and proposed baseline documentation.

The embedded context and status documents explicitly state `Last updated: 2026-07-19`.

### Explicit Requirements

- Communicate with the user in Hebrew.
- Keep source code, identifiers, comments, docstrings, test names, branch names, commit messages, and technical documentation in English.
- Prioritize correctness, readability, simplicity, maintainability, testability, clear responsibility boundaries, deterministic behavior, and explicit state transitions.
- Implement only explicitly defined requirements.
- Do not invent game rules or UI behavior.
- Prefer the smallest focused correct change.
- Preserve clear architectural ownership.
- Keep the real-time layer as the single authority for timed actions.
- Keep activity restrictions per piece rather than global.
- Do not allow the UI to decide legality.
- Do not expose mutable internal state or access another component's private fields.
- Require focused tests and a complete test-suite run after meaningful code changes.
- Account for NetFree restrictions in Git workflow.
- Use right-click as the jump gesture.
- Clear selection only when the jump request is accepted and the jump actually starts.
- Preserve selection when the right-click request is rejected, ignored, or cannot start.

### Clarifications

- Selection clearing applies even when a different piece was selected.
- A raw right-click event alone is not sufficient reason to clear selection.
- Game events describe facts that occurred and are not hidden commands.
- The model remains authoritative even when the UI animates events.
- Historical test results are a baseline, not proof of future correctness.

### Historical Reviewer Feedback

The summary recorded a reviewer analogy discouraging over-engineering.

This analogy is preserved only as historical intake information.

It is not retained as an active principle in `PROJECT_CONTEXT.md` after the explicit user correction dated 2026-07-27.

### Recommendations

The summary recommends storing project documentation in the repository, preferably under `docs`, and uploading it to Project Sources.

This is a repository-organization recommendation, not a game-behavior requirement.

### Examples

The summary provides example Git commands, test commands, branch workflow, and right-click jump test scenarios.

These examples guide execution but do not independently prove the current repository state.

### Historical Status Snapshot

The embedded status document reported:

- Branch: `feature/right-click-jump`
- Feature focus: right-click jump selection behavior
- Test baseline: 355 tests passed and 42 subtests passed
- Date: 2026-07-19

This snapshot is historical.

### Unresolved Ambiguities at That Time

- Whether the reported branch was later merged
- Whether the recorded tests were rerun after subsequent changes
- Whether later UI fixes were present in the repository
- Current branch and commit
- Current full-suite result
- Current whole-project completion status

### Required Project Action

Preserve the stable architectural and behavioral decisions, but do not treat the 2026-07-19 branch and test snapshot as current without newer evidence.

## 2026-07-27 — Permanent Material Intake Point Established

### Source

Current user instruction in the permanent intake chat.

### Authority

Explicit user instruction.

### Administrative Requirements

- This chat is the permanent intake point for new Kung-Fu Chess project materials.
- Uploaded emails, documents, reviewer notes, transcripts, presentations, screenshots, archives, and other official materials must be processed according to the project instructions.
- Maintain the minimum project record set:
  - `PROJECT_CONTEXT.md`
  - `PROJECT_STATUS.md`
  - `PROJECT_RECORD.md`
- Return only complete files that actually need to be updated.
- Communicate with the user in Hebrew.
- Keep project documentation in English.
- Do not modify source code unless implementation is explicitly requested.

### Correction

The supplied `PROJECT_CONTEXT.txt` contained only a placeholder marker and was not a usable project-context document.

It was superseded for project-record purposes by the complete `PROJECT_CONTEXT.md`.

### Reconciliation Decision

The 2026-07-19 `feature/right-click-jump` status was retained as historical evidence only until newer repository evidence became available.

### Files Updated

- `PROJECT_CONTEXT.md`
- `PROJECT_STATUS.md`
- `PROJECT_RECORD.md`

### Source Code Updated

- None

## 2026-07-27 — User Corrections to Active Project Context

### Source

Explicit user corrections in the permanent intake chat.

### Authority

Highest-priority source: latest explicit user decision.

### Priority Correction

Architecture and design quality are the highest project priority.

Correctness remains mandatory, but the active context must not place correctness above architecture.

### Source-of-Truth Correction

The latest explicit user decision is the first source of truth.

Official assignments and reviewer requirements follow it.

### Active-Guidance Correction

The calculator/air-conditioner analogy is not required in active project context and was removed from `PROJECT_CONTEXT.md`.

The historical existence of the feedback remains recorded only in this append-only project record.

### Confirmed Existing Decisions

The user explicitly reconfirmed:

- Project documentation remains in English.
- The later-arriving enemy piece captures the earlier-arriving piece in a collision.
- A move request to a friendly occupied destination is rejected.
- A completed move starts long rest.
- A completed jump starts short rest.
- Rest durations are configurable and are not important permanent domain constants.
- Automatic pawn promotion to a queen must be documented.
- Path-blocking rules must be documented.
- Game-over behavior must be documented.

### Clarification About Completion Criteria

A separate Definition of Done for the entire project is not currently required.

Per-change completion criteria remain useful for verifying focused work.

### Repository-Structure Clarification

The exact current repository structure can be derived from the latest archive.

It does not require a separate user-supplied document.

### Required Project Actions

- Update active project priorities.
- Update source-of-truth order.
- Remove the analogy from active context.
- Add the confirmed rest policy.
- Add pawn promotion.
- Add piece path-blocking behavior.
- Add game-over behavior.
- Reconcile status with the uploaded repository.

## 2026-07-27 — Current Repository Archive Reconciliation

### Source

Uploaded archive:

`d70a2d04-42ec-4290-97fc-44807bca66bf.zip`

### Authority

Current implementation and Git evidence.

Implementation evidence proves what exists in the repository but does not override an explicit user decision or official requirement.

### Git Evidence

- Current branch: `main`
- Upstream relationship: `main...origin/main`
- Working tree: clean
- Latest commit: `cbad94bafa2f9ea1acd45b55d9f50d5f09aa99e3`
- Latest commit subject: `Render knight moves as one straight animation (#19)`
- Latest commit date: 2026-07-27

### Test Evidence

Command:

```text
python -m pytest -q
```

Result:

- Passed: 497
- Subtests passed: 90
- Failed: 0
- Errors: 0
- Duration: 1.49 seconds

### Verified Implementation Behavior

The archive confirms:

- Sliding-piece blockers stop rook, bishop, and queen paths.
- A knight ignores intermediate blockers.
- Pawns support forward movement, initial double movement, and diagonal capture.
- Pawn promotion is automatic and produces a queen.
- A regular move starts long rest.
- A jump starts short rest.
- Rest values are loaded from runtime configuration.
- Capturing a king sets game over.
- New moves and jumps are rejected after game over.
- Time advancement stops after game over.
- BoardMapper respects non-zero board origins.
- The graphical loop exits through the window X button.
- The graphical loop preserves fractional milliseconds.
- The graphical loop consumes queued game events.
- Knight visual movement is rendered as a straight animation.
- Movement collision processing occurs at cell boundaries.

### Current Configurable Values

- Short rest: 2000 milliseconds
- Long rest: 10000 milliseconds

These values are implementation configuration, not permanent domain constants.

### Corrections to Previous Status

The following values are no longer unknown:

- Current branch
- Current latest commit
- Current working-tree state
- Current full test result
- Presence of the later UI fixes
- Current high-level repository structure

The previous 355-test baseline remains historical and is superseded for current status by the 497-test result.

### Documentation Gap

The archive does not contain:

- `PROJECT_CONTEXT.md`
- `PROJECT_STATUS.md`
- `PROJECT_RECORD.md`

It contains `README.md`, `docs/project_rules.md`, and `docs/Clean-Code-Cheatsheet.md`.

### Remaining Ambiguities

- The exact next development task has not been specified.
- The latest official assignment document was not included.
- The latest reviewer notes were not included.
- It is unknown whether any mandatory requirement exists outside the repository and recorded conversations.
- The final intended location of the three project record files inside the repository has not been decided.
- It is not yet confirmed whether the project is feature-complete.

### Recommended Additional Materials

No additional source archive is needed for the present status update.

Useful future intake materials are:

- Latest official assignment or requirement document
- Latest reviewer notes
- Reviewer emails
- Design-review transcripts or recordings
- Screenshots containing official requirements
- A list of remaining mandatory features
- Submission or acceptance instructions

When the source does not display a date, its date should be supplied with the upload.

### Files Updated

- `PROJECT_CONTEXT.md`
- `PROJECT_STATUS.md`
- `PROJECT_RECORD.md`

### Source Code Updated

- None

## 2026-07-27 — Official Email Excerpts and User Clarifications

### Source

Several official email excerpts supplied by the user.

The original email dates were not included in the excerpts.

### Authority

Official project guidance, interpreted together with the user's explicit clarifications in this chat.

The user's clarifications are the highest-priority source where the email wording allowed more than one interpretation.

### Explicit Testing Requirements

- All tests must be written and executed with Pytest.
- Using Pytest only as a runner for `unittest.TestCase` tests is not sufficient.
- Tests must not use monkey patching.
- The prohibition includes:
  - `unittest.mock.patch`
  - `patch.object`
  - Pytest `monkeypatch`
  - Equivalent runtime replacement of code under test
- Dependency injection, fakes, stubs, or other explicit test collaborators should be used instead.

### Coverage Requirement

- The project should strongly aim for 100% unit-test coverage.
- Coverage is a quality target rather than an absolute acceptance threshold independent of test value.
- An HTML coverage report is preferred because it identifies uncovered lines.
- Tests added for coverage must verify meaningful behavior rather than merely execute lines.

### Clean-Code Requirements

The email identifies these primary quality rules:

- DRY: each piece of logic should have one authoritative implementation.
- SRP: each function or class should have one focused responsibility.
- Encapsulation: components must not depend on another component's private representation.
- Changeable business values must not be scattered as hard-coded literals.

### User Clarification About Constants

- Changeable business values belong in configuration or injected policy objects.
- Semantic constants, enums, stable state names, and protocol identifiers may remain centralized in code.
- The requirement does not mean placing every literal or string in a configuration file.

### Future Binary Representation

The email reports a possible future binary representation for board and piece data.

Requirements:

- Do not implement it now.
- Avoid architecture that depends on textual tokens or a specific storage container.
- Preserve encapsulation and stable domain APIs.
- Be able to explain how representation internals and boundary adapters could be replaced without rewriting upper layers.

### Future User-Defined Games

The email reports a possible future ability for users to define board games, piece kinds, movement rules, and alternative policies such as promotion behavior.

Requirements:

- Do not implement the feature now.
- Avoid architecture that makes standard chess rules impossible or excessively difficult to replace.
- Be able to explain a future extension path.
- Preserve current confirmed game behavior, including automatic pawn promotion to a queen.
- Treat the alternative backward-moving pawn as an example, not a current game requirement.

### Graphics Requirement

- All displayed graphics must use the supplied `Img` abstraction.
- This includes the board, pieces, score or status, animations, and every other graphical element.
- Alternative graphics libraries such as PyGame, SFML, and LWJGL are prohibited.
- Library-specific graphical operations must remain encapsulated inside `Img`.

### Current Repository Evidence

The repository audit found:

- The complete suite runs under Pytest.
- 28 test files currently use `unittest` APIs or `unittest.TestCase`.
- 7 test files currently use `patch`, `patch.object`, or equivalent runtime replacement.
- No coverage configuration, coverage dependency, or generated report is present.
- Rest durations are already loaded from configuration.
- Board storage is private and text parsing is separated from the model, providing positive evidence for representation replacement.
- Standard piece kinds are fixed in `VALID_KINDS`.
- Movement rules use a fixed `_DESTINATION_RULES` registry.
- Queen promotion is hard-coded in `GameEngine`.
- `SpriteLoader` validates against the fixed standard piece-kind set.
- Graphical output uses `Img`, and direct `cv2` usage is confined to `kungfu_chess/ui/img.py`.

### Compliance Conclusions

- Pytest execution: compliant.
- Native Pytest test structure: partially compliant.
- Monkey-patching prohibition: not compliant.
- Coverage target: not yet measured.
- Configurable business values: partially verified.
- Binary representation readiness: promising but not fully certified.
- User-defined game readiness: not yet demonstrated.
- Img-only graphics: compliant in the reviewed archive.

### Required Project Actions

Without implementing the future features themselves:

1. Plan a focused migration to native Pytest.
2. Replace patch-based tests with dependency injection or explicit collaborators.
3. Add measurable coverage reporting and review uncovered business logic.
4. Produce a focused architecture explanation for replacing board and piece representation.
5. Produce a focused architecture explanation and, if needed, a minimal refactor for replaceable piece, movement, and promotion rules.
6. Preserve the current standard game behavior throughout any refactor.
7. Continue routing all graphical output through `Img`.

### Files Updated

- `PROJECT_CONTEXT.md`
- `PROJECT_STATUS.md`
- `PROJECT_RECORD.md`

### Source Code Updated

- None

## 2026-07-27 — Compliance Recheck Against Added Project Sources

### Source

- Added project sources:
  - `PROJECT_CONTEXT.md`
  - `PROJECT_STATUS.md`
  - `PROJECT_RECORD.md`
- Uploaded current repository archive:
  - `1343b057-c31d-4c8a-ae0f-d9072ed71cf8.zip`

### Authority

The project sources define the active requirements and current recorded risks.

The repository archive provides current implementation and test evidence.

### Git Evidence

- Branch: `main`
- Upstream: `origin/main`
- Working tree: clean
- Commit: `cbad94bafa2f9ea1acd45b55d9f50d5f09aa99e3`
- Subject: `Render knight moves as one straight animation (#19)`

### Functional Verification

Command:

```text
python -m pytest -q
```

Result:

- Passed: 497
- Subtests passed: 90
- Failed: 0
- Errors: 0
- Duration: 1.67 seconds

The current implemented gameplay and UI behaviors recorded in the project context remain verified by the complete passing suite and repository inspection.

### Native-Pytest Audit

Repository evidence:

- Discovered test files: 28
- Test files using `unittest` APIs or `unittest.TestCase`: 28
- `unittest.TestCase` classes: 69
- Native Pytest test functions discovered by static inspection: 0

Conclusion:

- Pytest runner usage is compliant.
- Native-Pytest test structure is not compliant with the final project requirement.

### Monkey-Patching Audit

The following 7 files use `patch` or `patch.object`:

- `tests/integration/test_text_scripts.py`
- `tests/unit/test_board_renderer.py`
- `tests/unit/test_controller.py`
- `tests/unit/test_game_window.py`
- `tests/unit/test_img.py`
- `tests/unit/test_rule_engine.py`
- `tests/unit/test_sprite_loader.py`

Conclusion:

- The prohibition on monkey patching is not satisfied.
- These tests require explicit collaborators, fakes, stubs, or dependency injection.

### Coverage Audit

Commands:

```text
COVERAGE_FILE=<external-path> python -m coverage run --branch --source=kungfu_chess -m pytest -q
COVERAGE_FILE=<external-path> python -m coverage report -m
```

Result:

- Total statement and branch coverage: 96%
- Statements: 1369
- Missed statements: 34
- Branches: 392
- Partially covered branches: 23
- Lowest-covered production module: `kungfu_chess/ui/img.py` at 76%

The coverage data file was stored outside the repository.

Conclusion:

- Coverage is high but below the strong 100% target.
- The repository has no committed coverage configuration or HTML coverage report.

### Architecture and Extensibility Audit

Positive evidence:

- Board storage remains private.
- No external production component accesses `Board._cells`.
- Text parsing and printing remain boundary adapters.
- Direct `cv2` usage remains confined to `kungfu_chess/ui/img.py`.
- No prohibited alternative graphics library was found.

Remaining coupling:

- `VALID_KINDS` fixes standard piece kinds in the model.
- `_DESTINATION_RULES` fixes movement-rule registration.
- Queen promotion remains hard-coded in `GameEngine`.
- `SpriteLoader` validates against the model's fixed piece-kind set.

Conclusion:

- Binary-representation readiness remains promising but not fully certified.
- Future user-defined-game readiness is not yet demonstrated.
- Img-only graphical output is compliant.

### Documentation Audit

The repository still does not contain:

- `PROJECT_CONTEXT.md`
- `PROJECT_STATUS.md`
- `PROJECT_RECORD.md`

Conclusion:

- Project Sources contain the authoritative documents, but repository documentation can drift until their final repository location is decided.

### Overall Compliance Conclusion

The project is functionally strong and the currently implemented game behavior passes all automated tests.

It does not yet satisfy every added requirement.

Confirmed remaining compliance work:

1. Migrate all tests from `unittest.TestCase` to native Pytest.
2. Remove all prohibited patching.
3. Add a reproducible coverage configuration and HTML report.
4. Review and meaningfully cover the remaining uncovered paths.
5. Complete the binary-representation dependency explanation.
6. Establish a minimal replaceable boundary for piece kinds, movement rules, promotion, and sprite definitions without implementing user-defined games.
7. Decide whether the three project record files belong at repository root or under `docs`.

### Files Updated

- `PROJECT_STATUS.md`
- `PROJECT_RECORD.md`

### Source Code Updated

- None

## 2026-07-28 — Updated UI Sources, Repository, and Move-Log Decisions

### Sources

- Official presentation: `CTD 26 (UI).pdf`
- Visual reference: `KFChess Play.mp4`
- Current repository archive: `34a8396d-c45b-48a9-a333-dbf0a94b9ba7.zip`
- Latest explicit project-chat decisions concerning the moves log and game-over ordering

### Authority and Interpretation

The latest explicit user decisions are authoritative for move-history semantics and event ordering.

The presentation's page titled `Additional Requirements` explicitly requires:

- Moves log
- Score based on the cost of captured pieces
- Player names
- `Observer`

The presentation does not define `Observer`; no meaning is inferred.

The animation and controls pages provide technical guidance about the supplied `Img` API, sprite folders, state-based animation, JSON-defined FPS, mouse input, and coordinate relationships. They are not treated as a demand to copy one exact screen layout.

The video is retained as a visual reference rather than an exact acceptance specification.

### Current Repository Evidence

Git:

- Branch: `main`
- Upstream: `origin/main`
- Working tree: clean
- Commit: `d137984a5947b94cfd91605664c7a1aae3b6e1bd`
- Subject: `Merge pull request #23 from LeahKarpman/refactor/compact-game-dashboard`

Recent completed work includes:

- Removal of patch-based tests through explicit seams
- Partial migration from `unittest` to native Pytest
- Capture-value score and moves-log presentation
- Compact dashboard composition

Functional verification:

```text
python -m pytest -q
```

Result:

- Passed: 554
- Subtests passed: 64
- Failed: 0
- Errors: 0
- Duration: 2.43 seconds

Coverage verification:

- Total coverage: 95%
- Statements: 1577
- Missed statements: 62
- Branches: 446
- Partially covered branches: 39
- `kungfu_chess/ui/img.py`: 72%

Testing-standard audit:

- Test files: 32
- Files still using `unittest`: 18
- `unittest.TestCase` classes: 54
- Native module-level Pytest tests: 26
- Files using prohibited patching: 0

### Verified UI State

Implemented:

- Img-only graphical output
- Compact dashboard
- Configured capture-value scoring
- Independent White and Black move panels
- State-specific sprite animation

Missing or incomplete:

- Player-name presentation
- Defined `Observer` behavior
- Complete move-history retention
- Geometry-based visible-row limiting

### Explicit Move-Log Decisions

- `GamePresentation` must preserve the full history; the current five-entry cap is not acceptable as data storage.
- White and Black histories remain independent.
- The renderer alone limits visible entries according to available panel geometry.
- It shows the newest fitting entries, ordered chronologically within the visible slice.
- A move that captures a king at an intermediate cell boundary must emit and record its winning `MoveCompleted` before `GameOver`.
- Final-destination move captures and jump captures must preserve their existing completion-before-`GameOver` behavior.
- No `RestStarted` may occur after game over.

### Conflicts and Superseded Status

The previous repository status at commit `cbad94b` with 497 tests and 90 subtests is historical.

The current status is commit `d137984` with 554 tests and 64 subtests.

The previous monkey-patching noncompliance is resolved in the reviewed archive.

The native-Pytest migration and coverage target remain incomplete.

### Required Actions

1. Fix move-history retention and renderer row selection.
2. Fix intermediate-boundary winning-move event ordering.
3. Preserve existing terminal-state and jump/final-destination behavior.
4. Add player-name presentation.
5. Clarify `Observer` before implementation.
6. Continue native-Pytest migration and coverage work.
7. Continue focused future-extensibility planning without implementing custom games or binary storage.

### Files Updated

- `PROJECT_CONTEXT.md`
- `PROJECT_STATUS.md`
- `PROJECT_RECORD.md`

### Source Code Updated

- None

## 2026-07-28 — Observer Requirement Clarified

### Source

Explicit user clarification in the permanent intake chat.

### Authority

Latest explicit user decision.

### Clarification

The `Observer` item in the official UI material means the Observer design pattern.

It is not a requirement for spectator mode or watcher functionality.

The pattern should be used where an actual one-to-many change-notification relationship requires it. It should not be inserted mechanically into every interaction.

### Architectural Interpretation

- An authoritative subject may notify multiple independent consumers through narrow public contracts.
- Concrete UI or presentation consumers must not be known by the subject.
- Observers may react to published facts but must not become authorities for game legality or game state.
- A global event bus or general observer framework is not required unless a concrete current need justifies it.
- Direct calls remain preferable for simple one-to-one collaboration.

### Current Repository Evidence

No explicit observer subscription and notification API was found in the reviewed production code.

The current engine stores immutable game events and exposes them through the pull-based `consume_events()` API. `GameWindow` consumes those events and applies them to one `GamePresentation` instance. This is event-driven collaboration but does not alone establish a complete Observer-pattern implementation.

### Superseded Ambiguity

The previous record stated that the meaning of `Observer` was undefined. That ambiguity is resolved by this clarification.

### Required Project Action

Perform a focused design review to identify concrete one-to-many notification boundaries and apply the Observer pattern only where it improves decoupling. Do not implement spectator mode and do not introduce a broad framework without a demonstrated need.

### Files Updated

- `PROJECT_CONTEXT.md`
- `PROJECT_STATUS.md`
- `PROJECT_RECORD.md`

### Source Code Updated

- None

## 2026-07-28 — Current Repository Reconciliation and Documentation Clarifications

### Sources

- Current repository working tree and Git history
- Complete current Pytest run
- Static audit of test structure and prohibited patching
- Explicit user clarifications in the permanent intake chat

### Authority

- Current implementation and Git evidence establish the present repository state.
- The latest explicit user clarifications establish document ownership, player-name scope, and Observer interpretation.
- The user confirmed that the official materials recorded in this file were supplied by the user and remain authoritative.

### Documentation Decisions

- `PROJECT_CONTEXT.md`, `PROJECT_STATUS.md`, and `PROJECT_RECORD.md` are official project documents intended to be maintained in the repository.
- Their intended location is the repository root.
- The current files remain untracked until they are explicitly added to Git.

### Player-Name Clarification

- The UI must display player names.
- The application supplies default names for the current requirement.
- No user name-entry workflow is currently required.
- The exact default labels may be selected during the focused UI implementation unless an official source defines them.

### Observer Clarification Reconfirmed

- Use the Observer design pattern only where a genuine current one-to-many notification relationship requires it.
- Do not introduce the pattern mechanically.
- Do not implement spectator mode or a broad event framework merely to satisfy the pattern name.

### Current Git Evidence

- Branch: `main`
- Upstream: `origin/main`
- Ahead/behind: `0/0`
- Latest commit: `61d34ae8cda9670f6a98ef03c9493de00a788174`
- Subject: `Merge pull request #26 from LeahKarpman/refactor/native-pytest-batch-3`
- Commit date: 2026-07-28 13:13:29 +0300
- Working-tree changes: the three untracked project-control Markdown files only

### Completed Work Since the Previous Status

- PR #24 fixed complete move-history retention.
- The renderer now derives visible move rows from panel geometry and displays the newest fitting chronological slice.
- Intermediate-boundary winning moves now emit `MoveCompleted` before `GameOver`.
- Existing final-destination and jump-capture ordering remains preserved.
- PRs #25 and #26 continued the migration from `unittest.TestCase` to native Pytest.

### Current Functional Verification

Command:

```text
$env:PYTHONDONTWRITEBYTECODE='1'
python -m pytest -q -p no:cacheprovider
```

Result:

- Passed: 572
- Subtests passed: 44
- Failed: 0
- Errors: 0
- Duration: 5.38 seconds

Bytecode writing and Pytest's cache provider were disabled to avoid creating project changes.

### Current Testing-Standard Audit

- Test files: 32
- Files still using `unittest` structures: 12
- `unittest.TestCase` classes: 42
- Native module-level Pytest test functions: 28
- Files using prohibited patching: 0

### Coverage Status

The previous 95% branch-aware coverage result belongs to commit `d137984`.

Current coverage at commit `61d34ae` was not measured because the `coverage` package is not installed in the current environment and is not declared in `requirements.txt`.

The repository still has no committed coverage configuration or HTML coverage report.

### Superseded Current Status

The `d137984` status with 554 tests, 64 subtests, 18 files using `unittest`, and 54 `unittest.TestCase` classes is now historical.

The move-history retention and intermediate-boundary winning-action issues recorded as required work have been resolved.

### Current Required Actions

1. Add application-provided default player names without adding a name-entry workflow.
2. Perform a focused Observer design review and implement the pattern only if a genuine one-to-many boundary is identified.
3. Continue the native-Pytest migration.
4. Establish reproducible coverage tooling and measure the current commit.
5. Continue focused future-extensibility planning without implementing custom games or binary storage.
6. Add the three official project documents to Git when the documentation update is ready to commit.

### Files Updated

- `PROJECT_CONTEXT.md`
- `PROJECT_STATUS.md`
- `PROJECT_RECORD.md`

### Source Code Updated

- None

## 2026-07-28 — Agent Workflow and Default Player Names Confirmed

### Source

Explicit user approval of the proposed complete `AGENTS.md` policy and its recommended defaults.

### Authority

Latest explicit user decision.

### Agent-Workflow Decisions

- Add an official root-level `AGENTS.md` that applies to the entire repository.
- Keep agent workflow in `AGENTS.md` and keep domain requirements in `PROJECT_CONTEXT.md`.
- Require agents to read current project context and status before source-code changes.
- Treat `docs/project_rules.md` as binding unless a later explicit project decision overrides it.
- Treat `docs/Clean-Code-Cheatsheet.md` as supporting reference material.
- Preserve focused task scope and report unrelated issues instead of fixing them automatically.
- Allow only small directly necessary adjacent refactors.
- Do not install dependencies or perform Git mutations such as commit, push, merge, PR creation, or branch deletion without authorization.
- Do not use sub-agents or parallel delegation unless the user explicitly requests it or a later authoritative instruction permits it.
- Keep generated caches, virtual environments, and coverage output out of intentional changes.
- Do not create new project rules from agent assumptions.

### Testing Decisions

- All new tests use native Pytest.
- Do not add new `unittest.TestCase` tests.
- Migrate touched legacy tests only when the focused migration remains small.
- The prohibition on monkey patching remains absolute, including wrapper and infrastructure tests.
- Coverage remains a strong meaningful target without a hard numeric gate.
- Coverage measurement is required for significant changes or coverage-focused work, not for documentation-only or trivial changes.
- Ruff and Pyright are not mandatory completion checks until an agreed reproducible workflow exists.
- Adding coverage tooling requires a separate focused task and dependency approval.

### UI Decisions

- The exact application-provided default names are `White Player` and `Black Player`.
- No name-entry workflow is required.
- An Observer review may correctly conclude that no new Observer implementation is needed when no genuine current one-to-many notification relationship exists.

### Documentation Decisions

- `AGENTS.md`, `PROJECT_CONTEXT.md`, `PROJECT_STATUS.md`, and `PROJECT_RECORD.md` are official root-level project documents.
- Update only the document whose owned information changed.
- Keep `PROJECT_RECORD.md` append-only.
- Identify transient test and coverage results by date and commit.

### Current Working-Tree Effect

The working tree now contains four untracked official Markdown files:

- `AGENTS.md`
- `PROJECT_CONTEXT.md`
- `PROJECT_STATUS.md`
- `PROJECT_RECORD.md`

### Files Updated

- `AGENTS.md`
- `PROJECT_CONTEXT.md`
- `PROJECT_STATUS.md`
- `PROJECT_RECORD.md`

### Source Code Updated

- None

## 2026-07-28 — PR #27 Reconciliation and Local Reference Cleanup

### Sources

- Current repository and Git history
- Complete current Pytest run
- Static testing-standard audit
- Explicit user instruction to reconcile, commit, and publish all current work
- User deletion of the local `CTD26/` reference directory and related configuration cleanup

### Authority

- Current implementation and Git evidence establish the present repository state.
- The user's latest instruction authorizes the required documentation corrections, commits, and GitHub publication.

### Repository Changes

- The verified implementation baseline advanced to commit `236c2f24c4baf769c0ba927d4c321f671af448f3`.
- PR #27 migrated GameEngine move, jump, collision, and cooldown tests to native Pytest.
- The local untracked `CTD26/` reference directory was deleted by the user.
- The obsolete `CTD26/` entry was removed from `.gitignore`.
- The obsolete `CTD26` Pyright exclusion was removed from `pyrightconfig.json`.
- Current operational project documents no longer depend on the deleted directory.
- The historical reference to the official presentation name `CTD 26 (UI).pdf` remains in its dated record because it identifies an authoritative source rather than the deleted local directory.

### Current Functional Verification

Command:

```text
$env:PYTHONDONTWRITEBYTECODE='1'
python -m pytest -q -p no:cacheprovider
```

Result:

- Passed: 578
- Subtests passed: 36
- Failed: 0
- Errors: 0
- Duration: 5.05 seconds

### Current Testing-Standard Audit

- Test files: 32
- Files still using `unittest` structures: 8
- `unittest.TestCase` classes: 30
- Native module-level Pytest test functions: 28
- Files using prohibited patching: 0

### Documentation Publication Decision

- Track `AGENTS.md`, `PROJECT_CONTEXT.md`, `PROJECT_STATUS.md`, and `PROJECT_RECORD.md` at the repository root.
- Publish the configuration cleanup separately from the project-documentation commit.
- Push the completed commits to `origin/main`.

### Files Updated

- `.gitignore`
- `AGENTS.md`
- `PROJECT_CONTEXT.md`
- `PROJECT_STATUS.md`
- `PROJECT_RECORD.md`
- `pyrightconfig.json`

### Source Code Updated

- None

## 2026-07-29 — Testing-Standard Compliance Completed

### Sources

- Explicit user instruction to complete the testing-standard work in three stages
- Current implementation and native-Pytest suite
- Branch-aware whole-package coverage reports generated before and after the work

### Authority

Latest explicit user decision.

### Stage 1 — Native Pytest Migration

- Migrated the final six legacy modules to native Pytest:
  - `tests/integration/test_text_scripts.py`
  - `tests/unit/test_board_renderer.py`
  - `tests/unit/test_controller.py`
  - `tests/unit/test_game_window.py`
  - `tests/unit/test_img.py`
  - `tests/unit/test_sprite_loader.py`
- Preserved every test behavior and converted 34 `subTest` cases to explicit
  parametrized cases.
- Removed all remaining `unittest`, `TestCase`, `self.assert*`,
  `assertRaises`, and `subTest` structures.
- Verified 607 collected and passing tests after migration.
- Commit subject: `refactor(tests): complete native pytest migration`.

### Stage 2 — Reproducible Coverage

- Added `coverage` to `requirements.txt`.
- Added `.coveragerc` with branch coverage, whole-`kungfu_chess` measurement,
  missing-line reporting, HTML output, and a 94.91% regression threshold.
- Documented the exact erase, run, report, and HTML commands in `README.md`.
- Verified that `.coverage` and `htmlcov/` remain ignored and untracked.
- Verified the 94.91% baseline: 1579 statements, 58 missed statements,
  446 branches, and 37 partial branches.
- Commit subject: `chore(test): add coverage reporting workflow`.

### Stage 3 — Meaningful Remaining Paths

- Added behavior-focused tests for invalid and incomplete configuration, empty
  board parsing, motion and rest boundary states, parser and runner edge cases,
  presentation and renderer validation, sprite validation and resizing,
  safe UI composition, and remaining observable engine behavior.
- Expanded `Img` coverage through an explicit fake OpenCV backend across
  creation, loading, resizing, conversion, composition, drawing, text, and
  window operations.
- Added explicit stream injection to the text-runner entry adapter.
- Added explicit dependency factories and layout/config inputs to the
  graphical composition root.
- Added clear `Img.draw_on` validation for unsupported source and target pixel
  shapes.
- Final 2026-07-29 verification: 687 collected tests, 687 passed, 0 failed,
  and 100.00% coverage across 1588 statements and 452 branches.
- No paths were intentionally left uncovered.
- Commit subject: `test: cover remaining meaningful paths`.

### Compliance Audit

- Legacy `unittest` structures: 0
- Prohibited monkey-patching occurrences: 0
- Generated coverage artifacts committed: 0

### Production Files Updated

- `kungfu_chess/texttests/script_runner.py`: explicit input/output stream seam
  for the boundary adapter.
- `kungfu_chess/ui/game_window.py`: explicit composition-root factories and
  layout/config inputs for safe assembly and testing.
- `kungfu_chess/ui/img.py`: explicit validation for unsupported pixel shapes
  before conversion and drawing.

## 2026-07-29 — Testing Compliance Merged and Reverified on Main

### Sources

- Current Git history
- Merge commit `d647d7470036a1b1aaa831a65d00ba5c365ae677`
- Complete Pytest and branch-coverage run on `main`
- Static audit of legacy `unittest` structures and prohibited patching

### Current Repository Evidence

- Branch: `main`
- Upstream: `origin/main`
- Ahead/behind: `0/0`
- Commit: `d647d7470036a1b1aaa831a65d00ba5c365ae677`
- Subject: `Merge pull request #29 from LeahKarpman/test/complete-testing-compliance`
- Commit date: 2026-07-29 14:30:00 +0300

### Main-Branch Verification

Commands:

```text
$env:PYTHONDONTWRITEBYTECODE='1'
python -m coverage erase
python -m coverage run -m pytest -q -p no:cacheprovider
python -m coverage report -m
```

Result:

- Collected: 687
- Passed: 687
- Failed: 0
- Errors: 0
- Duration: 7.76 seconds
- Statements: 1588
- Missed statements: 0
- Branches: 452
- Partially covered branches: 0
- Total coverage: 100.00%

### Compliance Audit

- Test files: 33
- Files using `unittest` structures: 0
- `unittest.TestCase` classes: 0
- Prohibited monkey-patching occurrences: 0

### Superseded Status

The earlier status describing `test/complete-testing-compliance` as awaiting publication is superseded. PR #29 is merged and the same testing-standard compliance is verified on `main`.

### Files Updated

- `PROJECT_STATUS.md`
- `PROJECT_RECORD.md`

### Source Code Updated

- None
