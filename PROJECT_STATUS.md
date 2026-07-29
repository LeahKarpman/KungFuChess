# Kung-Fu Chess — Current Project Status

Last updated: 2026-07-29

## 1. Current Position

Repository state:

- The complete testing-standard change set is verified on
  `test/complete-testing-compliance` for publication to `main`.
- The official root-level project documents are tracked in Git.
- Obsolete `CTD26` ignore and Pyright-exclusion entries have been removed after the local reference directory was deleted.
- The testing work uses three focused commits: native-Pytest migration,
  reproducible coverage workflow, and meaningful remaining-path coverage.
- Generated `.coverage` data and `htmlcov/` output remain ignored and untracked.

The current repository includes a compact graphical dashboard with side scores and per-color move panels.

The next confirmed work is focused rather than a general UI rewrite:

- Add the application-provided default names `White Player` and `Black Player` without introducing a name-entry workflow.
- Perform a focused Observer design review and introduce the pattern only if a genuine one-to-many notification relationship currently requires it.

## 2. Current Verification

Complete suite, verified on 2026-07-29 on
`test/complete-testing-compliance` after the Stage 3 source-and-test changes:

```text
python -m pytest -q
```

Result:

- Collected: 687
- Passed: 687
- Failed: 0
- Errors: 0
- Duration: 6.69 seconds

```text
python -m coverage erase
python -m coverage run -m pytest
python -m coverage report -m
python -m coverage html
```

Current branch-aware result:

- Total coverage: 100.00%
- Statements: 1588
- Missed statements: 0
- Branches: 452
- Partially covered branches: 0
- HTML report: generated successfully at `htmlcov/index.html`

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

- Test files: 33
- Files using `unittest` structures: 0
- `unittest.TestCase` classes: 0
- Collected native-Pytest tests: 687

Status:

**Compliant.**

The last six legacy modules were migrated without removing or weakening any
test behavior. Their 34 former `subTest` cases are now explicit parametrized
Pytest cases.

### Monkey Patching

Current audit:

- Files using `patch`, `patch.object`, or Pytest `monkeypatch`: 0

Status:

**Compliant in the reviewed archive.**

The previous patch-based tests were replaced with explicit seams and collaborators.

### Coverage

Status:

**Compliant.**

`coverage` is declared in `requirements.txt`; `.coveragerc` enables branch
coverage, measures all of `kungfu_chess`, reports missing lines, enforces the
94.91% verified regression baseline, and writes the HTML report to `htmlcov/`.
Every previously uncovered statement and partial branch now has a
behavior-focused test, producing 100.00% statement-and-branch coverage.

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
5. Complete native-Pytest migration with no monkey-patching.
6. Reproducible whole-package branch coverage and HTML reporting.
7. Behavior-focused coverage of every production statement and branch.

Remaining official UI work:

- Add `White Player` and `Black Player` as application-provided default player names without user input.
- Apply the Observer design pattern at appropriate one-to-many notification boundaries, after a focused design review identifies a concrete need.

Remaining quality work:

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

- `PROJECT_STATUS.md`
- `PROJECT_RECORD.md`

Sources reconciled:

- The complete Stage 1 native-Pytest migration
- The committed Stage 2 coverage workflow
- The 2026-07-29 Stage 3 complete-suite and coverage run
- Static audits for legacy `unittest` structures and prohibited monkey-patching

Verified change-set branch:

`test/complete-testing-compliance`
