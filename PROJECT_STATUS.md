# Kung-Fu Chess — Current Project Status

Last updated: 2026-07-28

## 1. Current Position

Current verified branch:

`main`

Repository state:

- `main` is aligned with `origin/main` after the current documentation publication.
- The official root-level project documents are tracked in Git.
- Obsolete `CTD26` ignore and Pyright-exclusion entries have been removed after the local reference directory was deleted.
- Latest verified implementation baseline: `236c2f24c4baf769c0ba927d4c321f671af448f3`
- Baseline subject: `Merge pull request #27 from LeahKarpman/refactor/native-pytest-game-engine`
- Baseline commit date: 2026-07-28 13:51:02 +0300

The current repository includes a compact graphical dashboard with side scores and per-color move panels.

The next confirmed work is focused rather than a general UI rewrite:

- Add the application-provided default names `White Player` and `Black Player` without introducing a name-entry workflow.
- Perform a focused Observer design review and introduce the pattern only if a genuine one-to-many notification relationship currently requires it.
- Continue the native-Pytest and coverage compliance work.

## 2. Current Verification

Complete suite:

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

The verification command was run with bytecode writing and Pytest's cache provider disabled so the review would not create project changes.

Last recorded branch-aware coverage, measured at commit `d137984a5947b94cfd91605664c7a1aae3b6e1bd`:

```text
COVERAGE_FILE=<external-path> python -m coverage run --branch --source=kungfu_chess -m pytest -q
COVERAGE_FILE=<external-path> python -m coverage report -m
```

Historical result:

- Total coverage: 95%
- Statements: 1577
- Missed statements: 62
- Branches: 446
- Partially covered branches: 39
- Lowest-covered production module: `kungfu_chess/ui/img.py` at 72%

This is not a current coverage measurement for the `236c2f2` implementation baseline.

The current environment cannot reproduce the measurement because the `coverage` package is not installed and is not declared in `requirements.txt`. No committed coverage configuration or HTML report is present.

## 3. Verified Implemented System

The archive verifies:

- Layered model, rules, real-time, engine, input, text, and UI packages
- Text and graphical entry points
- Standard chess movement geometry and path blocking
- Pawn movement, capture, and automatic queen promotion
- Concurrent movement, jumps, and rests
- Per-piece busy-state enforcement
- Configurable short and long rest durations
- Arrival-boundary collision and capture resolution
- King-capture game over and rejection of later actions
- Immutable snapshots and deterministic events
- Mouse selection and right-click jump
- Board-origin-aware input mapping
- Window exit through keyboard or the close button
- Fractional elapsed-time preservation
- Engine-event consumption in the graphical loop
- Sprite-state animation through `Img`
- Capture-value scoring
- Separate White and Black move panels
- A compact board-centered dashboard

Current rest configuration:

- Short rest: 2000 milliseconds
- Long rest: 10000 milliseconds

Current configured capture values:

- Pawn: 1
- Knight: 3
- Bishop: 3
- Rook: 5
- Queen: 9
- King: 0

These numbers are configurable implementation values.

## 4. Official UI Requirements and Current Compliance

The official UI presentation lists a moves log, capture-value score, player names, and `Observer` as additional requirements. It also presents the supplied `Img` API and sprite structure, and discusses state-based animation, JSON-defined FPS, mouse coordinates, and window/image coordinate relationships.

### Implemented

- All graphical output is routed through `Img`.
- Direct `cv2` use remains confined to `kungfu_chess/ui/img.py`.
- Score is derived from capture events and configured piece values.
- White and Black have independent move panels.
- The dashboard composes the board and side panels into one frame.
- Animation assets are loaded from state-specific sprite folders and JSON definitions.

### Recently Completed

The moves-log completion work was merged in PR #24:

- `GamePresentation` preserves complete independent White and Black histories.
- The renderer derives the visible row count from panel geometry.
- The renderer shows the newest fitting entries in chronological order.
- Intermediate-boundary, final-destination, and jump king captures emit the completed winning action before `GameOver`.
- The engine continues to suppress `RestStarted` after game over.

### Not Yet Implemented or Not Yet Defined

- Player names are not represented or displayed. The confirmed defaults are `White Player` and `Black Player`; no name-entry workflow is required.
- The `Observer` requirement is now clarified as the Observer design pattern, to be used only at genuine one-to-many notification boundaries.
- No explicit observer subscription and notification contract was found in the current production code. The engine currently exposes a pull-based `consume_events()` queue, and `GameWindow` forwards consumed events to one `GamePresentation` instance. This is event-driven collaboration, but it is not by itself a complete Observer-pattern implementation.
- A focused design review must identify where multiple independent consumers actually require notification before introducing an observer abstraction. The requirement does not call for spectator mode or a global event bus.
- The current dashboard uses fixed frame and panel dimensions. The source discusses dynamic sizing and coordinate relationships, but it does not provide a precise acceptance rule for dynamic resizing.

The supplied play video is treated as a visual reference only. It demonstrates real-time board play, player identity, side information, move/status feeds, highlighting, and watcher information, but it does not by itself define an exact required layout or interaction contract.

## 5. Testing-Standard Compliance

### Native Pytest

Current audit:

- Test files: 32
- Files still using `unittest` structures: 8
- `unittest.TestCase` classes: 30
- Native module-level Pytest test functions: 28

Status:

**Partially compliant.**

PR #27 migrated the remaining GameEngine move, jump, collision, and cooldown suites. The remaining `unittest.TestCase` tests still require migration.

### Monkey Patching

Current audit:

- Files using `patch`, `patch.object`, or Pytest `monkeypatch`: 0

Status:

**Compliant in the reviewed archive.**

The previous patch-based tests were replaced with explicit seams and collaborators.

### Coverage

Status:

**Partially compliant.**

The last recorded coverage was 95% at commit `d137984`, but current coverage for the `236c2f2` implementation baseline has not been measured. The project still lacks the installed or declared coverage tooling, a reproducible committed configuration, and the preferred HTML report.

Coverage work must remain behavior-driven rather than adding tests solely to increase a percentage.

## 6. Architecture and Future Extensibility

Positive evidence:

- Board storage is private.
- Consumers use public board APIs.
- Text parsing and printing remain boundary adapters.
- Timed actions remain owned by the real-time arbiter.
- Presentation state is derived from engine events rather than mutating game state.
- Rendering and input share board geometry.
- Graphics-library details remain encapsulated in `Img`.

Remaining extensibility concerns:

- Standard piece kinds remain fixed in the model.
- Movement-rule registration remains a fixed registry.
- Queen promotion remains hard-coded in `GameEngine`.
- Sprite validation remains tied to the fixed standard piece-kind set.

Binary-representation readiness remains plausible but has not received a complete dependency certification.

User-defined-game readiness is not yet demonstrated. The future feature must not be implemented now, but a minimal replaceable boundary for piece definitions, movement rules, promotion policy, and visual definitions still requires architectural planning.

## 7. Current Work, Recent Completions, and Risks

Recently completed correctness work:

1. Full move-history retention.
2. Geometry-based renderer row limiting.
3. Winning-action completion before `GameOver` for every supported capture path.
4. Preservation of the rule that no rest begins after game over.

Remaining official UI work:

- Add `White Player` and `Black Player` as application-provided default player names without user input.
- Apply the Observer design pattern at appropriate one-to-many notification boundaries, after a focused design review identifies a concrete need.

Remaining quality work:

- Complete migration to native Pytest.
- Add a committed coverage workflow and HTML report.
- Add meaningful tests for uncovered production paths.
- Complete the binary-representation migration explanation.
- Establish minimal future rule-definition extension boundaries without implementing custom games.

## 8. Documentation and Process

The repository currently contains:

- `README.md`
- `docs/project_rules.md`
- `docs/Clean-Code-Cheatsheet.md`

The following official project documents are maintained at the repository root and tracked in Git:

- `AGENTS.md`
- `PROJECT_CONTEXT.md`
- `PROJECT_STATUS.md`
- `PROJECT_RECORD.md`

Their intended location is the repository root.

The deleted local `CTD26/` reference directory was not tracked. Its obsolete entries were removed from `.gitignore` and `pyrightconfig.json`.

No source or test code was changed during this documentation and configuration update.

## 9. Latest Documentation Update

Files updated:

- `.gitignore`
- `AGENTS.md`
- `PROJECT_CONTEXT.md`
- `PROJECT_STATUS.md`
- `PROJECT_RECORD.md`
- `pyrightconfig.json`

Sources reconciled:

- Current repository working tree
- Current Git history
- Complete current test run
- Historical coverage measurement and current tooling availability
- Official CTD graphics presentation
- Play-reference video
- Latest explicit project-chat decisions about agent workflow, document ownership, default player names, the meaning of `Observer`, and removal of the local `CTD26/` reference directory

Current branch:

`main`

Current verified implementation baseline:

`236c2f2 Merge pull request #27 from LeahKarpman/refactor/native-pytest-game-engine`
