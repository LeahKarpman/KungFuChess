# Kung-Fu Chess — Current Project Status

Last updated: 2026-07-30

## 1. Current Position

Repository state:

- `main` is aligned with `origin/main`.
- Current intake base: `a1611ef docs: record pytest temp isolation`.
- PR #29 merged the complete testing-standard change set into `main`.
- Current verified implementation commit: `6d72bc7eaede5e528771fe3bd044573d2243ef62`.
- Verified implementation subject: `feat(ui): display default player names`.
- Verified implementation commit date: 2026-07-29 15:17:36 +0300.
- The official root-level project documents are tracked in Git.

The current repository includes a compact graphical dashboard with
application-provided default player names, side scores, and per-color move
panels.

The graphical client and authoritative `GameEngine` still run in one local
process. The repository currently has no network protocol, server entry point,
account or room persistence, WebSocket transport, Docker configuration,
Docker Compose deployment, or `Server_Design.md`.

The active project phase is therefore the basic authoritative server, not the
production-scale deployment. Official direction requires completing a small
working server before implementing the proposed scalable service topology.

The first externally confirmed target is:

- Two graphical clients on different computers communicating over the
  internet.
- Multiple simultaneous games addressed through rooms.
- One server-owned authoritative `GameEngine` per active room.
- Client-side input and presentation with non-blocking network communication.

The Observer design-pattern review remains recorded but is no longer the
primary next task.

## 2. Current Verification

Sandboxed-agent test execution, verified on 2026-07-29 on `main` at commit
`4ba5094`:

```powershell
$agentPytestTemp = Join-Path ([System.IO.Path]::GetTempPath()) "kungfu-chess-codex-$PID"
python -m pytest -q -p no:cacheprovider --basetemp $agentPytestTemp
```

Result:

- Collected: 688
- Passed: 688
- Failed: 0
- Errors: 0
- Duration: 6.04 seconds
- The verified agent-owned base temporary directory was removed after the run.

Focused UI tests, reverified on 2026-07-29 on `main` at commit
`6d72bc7eaede5e528771fe3bd044573d2243ef62`:

```text
python -m pytest -q -p no:cacheprovider tests/unit/test_game_presentation.py tests/unit/test_game_hud.py tests/unit/test_compact_dashboard.py tests/unit/test_game_window.py tests/unit/test_game_events.py
```

Result:

- Collected: 97
- Passed: 97
- Failed: 0
- Errors: 0
- Duration: 0.69 seconds

Complete suite:

```text
python -m pytest -q -p no:cacheprovider
```

Result:

- Collected: 688
- Passed: 688
- Failed: 0
- Errors: 0
- Duration: 4.90 seconds

```text
python -m coverage erase
python -m coverage run -m pytest -p no:cacheprovider
python -m coverage report -m
python -m coverage html
```

Current branch-aware result:

- Total coverage: 100.00%
- Statements: 1596
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
- Application-provided `White Player` and `Black Player` names in their
  corresponding side panels
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
- The application supplies `White Player` and `Black Player`; `GamePresentation`
  exposes the names as presentation state and `GameRenderer` draws each name
  in its corresponding panel through `Img`.
- The dashboard composes the board and side panels into one frame.
- Animation assets are loaded from state-specific sprite folders and JSON definitions.

### Recently Completed

The player-name display was completed in commit `6d72bc7`:

- The graphical composition root supplies the exact default player names.
- No user input, account, persistence, or setup workflow was introduced.
- Board geometry, input mapping, animations, scoring, move history, and gameplay
  behavior remain unchanged.
- Native-Pytest coverage proves both names are supplied as presentation state
  and drawn in the correct side panels.

The moves-log completion work was merged in PR #24:

- `GamePresentation` preserves complete independent White and Black histories.
- The renderer derives the visible row count from panel geometry.
- The renderer shows the newest fitting entries in chronological order.
- Intermediate-boundary, final-destination, and jump king captures emit the completed winning action before `GameOver`.
- The engine continues to suppress `RestStarted` after game over.

### Not Yet Implemented or Not Yet Defined

- The `Observer` requirement is now clarified as the Observer design pattern, to be used only at genuine one-to-many notification boundaries.
- No explicit observer subscription and notification contract was found in the current production code. The engine currently exposes a pull-based `consume_events()` queue, and `GameWindow` forwards consumed events to one `GamePresentation` instance. This is event-driven collaboration, but it is not by itself a complete Observer-pattern implementation.
- A focused design review must identify where multiple independent consumers actually require notification before introducing an observer abstraction. The requirement does not call for spectator mode or a global event bus.
- The current dashboard uses fixed frame and panel dimensions. The source discusses dynamic sizing and coordinate relationships, but it does not provide a precise acceptance rule for dynamic resizing.

The supplied play video is treated as a visual reference only. It demonstrates real-time board play, player identity, side information, move/status feeds, highlighting, and watcher information, but it does not by itself define an exact required layout or interaction contract.

## 5. Server Phase: Requirements and Current Gap

### Current Gap

Repository inspection confirms that the server phase has not yet been
implemented:

- `app.py` and `ui_app.py` remain local entry points.
- The existing dependency list contains no network-server or database
  dependency.
- No server, socket, WebSocket, authentication, matchmaking, room, reconnect,
  or persistence implementation was found.
- No `Dockerfile`, Compose file, Kubernetes manifest, or `Server_Design.md` was
  found.

### Required Delivery Order

1. Preserve the current `GameEngine` as the server-side authority.
2. Separate the graphical client and game runtime into different processes.
3. Make one small two-client game work with authoritative commands, snapshots,
   and deterministic server timing.
4. Add multiple isolated rooms and internet-capable client connections.
5. Add the recorded baseline behavior for accounts, ELO, matchmaking,
   disconnect/reconnect, spectators, and logs.
6. Document the scalable design in `Server_Design.md`.
7. Package a small working version with Docker Compose.
8. Use Kubernetes or K3s only after the basic server works and scaling
   responsibilities are established.

### Official Scalable Reference

The official proposed topology contains:

- An API Gateway for login, rooms, and history.
- A WebSocket Gateway for live connections and state updates.
- A Matchmaker.
- A Game Allocator.
- Long-lived Game Server Shards that host authoritative room engines.
- Logs, metrics, health checks, and load tests.

The recommended data split is PostgreSQL for durable users, games, results,
and move history, and Redis for sessions, active-room routing, reconnect state,
and matchmaking queues. NATS or Redis Pub/Sub is recommended for internal
messaging.

### Open Decisions

The supplied materials do not yet settle:

- The exact client/server message schema and versioning policy.
- The Python WebSocket framework and concurrency model.
- Registration, password hashing, authentication tokens, and authorization.
- Whether spectators are required in the first working increment.
- Room expiration, ownership transfer, spectator permissions, and capacity.
- Reconnect identity, snapshot, command-sequence, and stale-command contracts.
- Regional placement, cross-region matching policy, and latency targets.
- Concrete service-level objectives, retention periods, and backup targets.
- The minimum Docker Compose service set for the first submitted version.

The additional design-review recordings may resolve these decisions before
`Server_Design.md` is finalized.

## 6. Testing-Standard Compliance

### Native Pytest

Current audit:

- Test files: 33
- Files using `unittest` structures: 0
- `unittest.TestCase` classes: 0
- Collected native-Pytest tests: 688

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

## 7. Architecture and Future Extensibility

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

## 8. Current Work, Recent Completions, and Risks

Recently completed correctness work:

1. Full move-history retention.
2. Geometry-based renderer row limiting.
3. Winning-action completion before `GameOver` for every supported capture path.
4. Preservation of the rule that no rest begins after game over.
5. Complete native-Pytest migration with no monkey-patching.
6. Reproducible whole-package branch coverage and HTML reporting.
7. Behavior-focused coverage of every production statement and branch.
8. Application-provided default player names displayed in the corresponding
   dashboard panels.
9. Sandboxed Pytest runs isolated from the human user's default temporary root.

Active server work:

1. Define the smallest authoritative client/server protocol and room lifecycle.
2. Move `GameEngine` ownership and time advancement into the server runtime.
3. Keep graphical client I/O non-blocking and resynchronize from server
   snapshots.
4. Prove two internet-connected clients and multiple isolated rooms.
5. Add the remaining baseline behaviors incrementally, with tests.
6. Write `Server_Design.md` from the confirmed requirements and design-review
   feedback.
7. Produce a small working Docker Compose deployment.

Deferred UI work:

- Apply the Observer design pattern at appropriate one-to-many notification
  boundaries only after a focused review identifies a concrete need. This
  requirement is separate from server-side spectator support.

Remaining quality work:

- Complete the binary-representation migration explanation.
- Establish minimal future rule-definition extension boundaries without implementing custom games.

## 9. Documentation and Process

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

The player-name implementation and tests are contained in commit `6d72bc7`.

## 10. Latest Documentation Update

Files updated:

- `PROJECT_CONTEXT.md`
- `PROJECT_STATUS.md`
- `PROJECT_RECORD.md`

Sources reconciled:

- `CTD 26 Game requirements.remuxed.mp4`
- `CTD - Server.mp3`
- `CTD.mp3`
- Two official server-scaling emails supplied by the user
- The latest uploaded repository archive
- The user's confirmed internet and multi-room deployment targets

Current verified branch:

`main`

Current intake base:

`a1611ef docs: record pytest temp isolation`

Source code and tests updated:

- None

Verification note:

- The last recorded complete verification remains 688 passed with 100.00%
  statement and branch coverage.
- Tests were not rerun for this documentation-only material intake.
