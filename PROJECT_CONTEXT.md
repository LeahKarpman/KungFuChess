# Kung-Fu Chess — Project Context

Last updated: 2026-07-30

## 1. Purpose

This document contains the stable project context for Kung-Fu Chess.

It records durable requirements, architectural boundaries, confirmed domain decisions, workflow constraints, and the rules used to interpret future project materials.

Transient branch, commit, test, and current-task information belongs in `PROJECT_STATUS.md`.

Chronological decisions, corrections, superseded information, reviewer feedback, and intake events belong in `PROJECT_RECORD.md`.

## 2. Project Overview

Kung-Fu Chess is a real-time chess game developed as part of a CTD software-development process.

The project began with incremental board parsing and movement-rule iterations and evolved into a layered real-time game containing:

- Board and piece modeling
- Piece movement and capture rules
- Pawn movement and promotion
- Real-time movement
- Jump actions
- Concurrent timed actions
- Collision and capture resolution
- Piece activity and rest states
- Game snapshots
- Deterministic game events
- Capture-value scoring
- Independent completed-action histories for White and Black
- Mouse input
- Graphical rendering
- Sprite animation
- Text-based integration testing

The primary implementation language is Python.

## 3. Project Priorities

The project priorities are:

1. Architecture and design quality
2. Correctness
3. Clear ownership and responsibility boundaries
4. Simplicity
5. Readability
6. Maintainability
7. Testability
8. Deterministic behavior
9. Explicit state transitions
10. Incremental delivery without speculative functionality

Architecture is the primary concern of this project.

A functionally correct change is not sufficient when it places responsibility in the wrong layer, creates multiple sources of truth, weakens encapsulation, or introduces unnecessary coupling.

The project must prefer the smallest focused design that correctly satisfies the current requirement.

A new abstraction must solve a current, demonstrated architectural or behavioral problem rather than prepare for a hypothetical future feature.

## 4. Communication and Documentation

- Communication with the user is in Hebrew.
- Source code is written in English.
- Identifiers, comments, docstrings, test names, branch names, commit messages, and technical documentation are written in English.
- Project documentation is maintained in English.
- `AGENTS.md`, `PROJECT_CONTEXT.md`, `PROJECT_STATUS.md`, and `PROJECT_RECORD.md` are official project documents maintained at the repository root.
- Important authoritative quotations are preserved in their original language.
- Source code is not modified during material intake unless implementation is explicitly requested.

## 5. Source-of-Truth Order

When sources conflict, use this order:

1. Latest explicit user decision
2. Latest official assignment or reviewer requirement
3. Latest recorded project decision
4. Current implementation and tests
5. Current project status
6. Older conversations, summaries, and historical records

A newer explicit user decision overrides an older decision or requirement unless the user explicitly states otherwise.

Examples and recommendations must not be silently promoted into mandatory requirements.

## 6. Architectural Principles

The architecture must preserve:

- Single Responsibility Principle
- Encapsulation
- Explicit ownership of mutable state
- Clear dependency direction
- Small and focused methods
- Meaningful naming
- Minimal public APIs
- Deterministic event ordering
- One authoritative owner for each rule and state transition
- Public APIs instead of external access to private fields
- Separation between authoritative game state and presentation state
- Replaceable representations behind stable domain APIs
- Replaceable rule definitions behind clear rule-layer boundaries

The project must avoid:

- Over-engineering
- Premature abstraction
- Premature optimization
- Hidden side effects
- Duplicated business rules
- Multiple sources of truth
- Multiple timing mechanisms
- UI-driven game legality
- Large rewrites without concrete evidence
- Implementing unrequested future features

### 6.1 Configurable Business Values

Business values that are expected to vary must not be scattered as hard-coded literals inside business logic.

Examples include:

- Rest durations
- Animation or movement timing values
- Resource paths
- Board-layout values
- User-selectable game settings

Such values belong in configuration or in a focused injected policy object.

Semantic constants that define the current domain may remain in code when that is the clearest design. Examples include enum members, event names, internal state names, and stable protocol identifiers.

The requirement is not to move every literal into a configuration file. The requirement is to prevent changeable business policy from being duplicated or embedded throughout the implementation.

### 6.2 Future Binary Representation

A future board or piece representation may use a binary format instead of a textual or dictionary-based representation.

This must not be implemented now.

Current architecture must nevertheless preserve a practical migration path:

- Board storage remains private.
- Consumers use stable board and piece APIs rather than knowing the storage layout.
- Text parsing and printing remain adapters at the system boundary.
- Rules depend on domain queries rather than textual tokens or a specific storage container.
- A future representation change should primarily replace model internals and adapters, not rewrite the rules, engine, controller, or UI.

The team must be able to explain this migration path when asked.

### 6.3 Future User-Defined Board Games

A future version may allow users to define piece kinds, movement rules, promotion behavior, and other game rules.

This feature must not be implemented now.

The current design must preserve a practical extension path:

- Piece behavior must be owned by the rules layer rather than scattered across unrelated layers.
- The engine must coordinate rule outcomes rather than hard-code every standard-chess policy internally.
- Promotion must remain a current standard-game rule that could later be supplied by a different rule set.
- Rendering should resolve visuals through resource or piece-definition data rather than require game logic changes.
- Adding a future piece or replacing a rule should not require coordinated edits throughout the model, rules, engine, controller, and UI.

The current game continues to use its confirmed standard Kung-Fu Chess rules, including automatic queen promotion. Future configurability does not change current behavior.

### 6.4 Server and Scalability Principles

The project is moving from a local application to an authoritative
client-server system.

The server design must preserve:

- One authoritative `GameEngine` for each active room.
- Server ownership of game time, legality, state transitions, results, and
  command ordering.
- Client ownership of input and presentation only.
- Isolation between rooms.
- A stable way to route a player or spectator to the room's current game
  server.
- Separation between durable data and short-lived operational state.
- Non-blocking client network activity so waiting for the server does not
  freeze the graphical loop.
- Explicit handling of disconnects, reconnects, stale commands, service
  failure, and recovery.
- Incremental delivery: a small working server precedes the scalable
  multi-service implementation.

The scalable target is a system-design requirement, not a requirement to run
the development environment at production scale. The implementation must first
prove the behavior with a small working deployment and then preserve a credible
path to horizontal scaling.

## 7. Layer Responsibilities

### 7.1 Model

The model owns core game entities and settled game state.

Typical components include:

- `Board`
- `Piece`
- `Position`
- `GameSnapshot`
- Game-related value objects
- State-related types
- Game events

The model must not depend on graphical UI, raw input handling, rendering, text scripts, or test infrastructure.

### 7.2 Rules

The rules layer determines whether a requested game action is legal.

It may evaluate:

- Movement geometry
- Path blocking
- Pawn-specific rules
- Capture rules
- Board occupancy
- Action-specific restrictions
- Current piece state

It must not manage rendering, animation, raw mouse events, elapsed-time progression, or UI selection state.

### 7.3 Real-Time Layer

The real-time layer owns time-dependent actions such as movement, jumping, arrival, and rest.

It is the single source of truth for active timed actions.

Its responsibilities include:

- Tracking active actions
- Advancing actions over time
- Detecting movement boundaries and arrivals
- Tracking per-piece activity
- Managing rest periods
- Producing explicit arrival information
- Preserving deterministic completion order

Movement and jumping must not use separate competing timing systems.

Activity restrictions must be per piece rather than global.

### 7.4 Game Engine

The game engine coordinates the model, rules, and real-time layer.

It applies authoritative game results to the state and emits game events.

It must not:

- Duplicate timing logic
- Interpret raw UI events
- Render the game
- Own UI selection behavior
- Access private board storage directly

### 7.5 Input and Controller

The input layer translates user actions into game requests.

Typical responsibilities include:

- Mapping pixels to board positions
- Tracking selection
- Converting mouse gestures into move or jump requests
- Forwarding requests to the game engine
- Reacting to explicit action results

It must not duplicate legality rules that belong to the rules layer or game engine.

### 7.6 UI

The UI is responsible for presentation.

It may:

- Read game snapshots
- Consume game events
- Render the board and pieces
- Animate moves and jumps
- Forward user input to the controller

It must not:

- Decide game legality
- Directly mutate model state
- Access private engine state
- Become a second source of authoritative game state
- Derive final game results from animation

All displayed graphics must be produced through the supplied `Img` abstraction, including:

- Board rendering
- Piece rendering
- Score or status display
- Animations
- Every other graphical element shown on screen

Alternative graphics libraries such as PyGame, SFML, or LWJGL are prohibited.

Library-specific graphical operations must remain encapsulated inside the `Img` abstraction rather than leak into the rest of the UI.

Official UI material also establishes these presentation requirements:

- Display a moves log.
- Display each player's score as the configured value of pieces captured by that player.
- Display application-provided default player names.
- Use the Observer design pattern where a genuine one-to-many change-notification relationship requires it.

Player names are currently supplied by the application. The current requirement does not include name entry or other player-name input.

The current default names are:

- `White Player`
- `Black Player`

The Observer requirement is architectural, not a spectator-mode requirement. It should be applied at appropriate notification boundaries so an authoritative subject can notify independent consumers without depending on their concrete implementations. Observers must react through narrow public contracts and must not become authorities for game rules or state.

The pattern must not be introduced mechanically into one-to-one interactions where a direct call is clearer. A global event bus or broad observer framework is not required merely to satisfy the pattern name.

The supplied graphics material treats animation as state-based presentation using sprite sequences and configuration-defined timing such as FPS. The exact visual example is guidance rather than a mandate to copy one fixed layout.

### 7.7 Text and Script Infrastructure

Board parsing, board printing, script parsing, script execution, and text-based integration helpers remain separate from graphical UI and game-rule logic.

### 7.8 Network Client

The network client owns the graphical application and its connection to the
server.

It may:

- Translate local input into protocol commands.
- Send authenticated move, jump, matchmaking, and room requests.
- Receive authoritative snapshots and events.
- Render the state and status supplied by the server.
- Reconnect and request a fresh authoritative snapshot.

It must not:

- Run a competing authoritative `GameEngine`.
- Advance authoritative game time.
- Decide whether a move or jump is legal.
- Trust locally predicted state over a server correction.
- Replay commands created while disconnected without server-side validation.
- Block the graphical event loop while waiting for network I/O.

### 7.9 Server Runtime

The server owns all authoritative games.

For every room, it must:

- Own exactly one authoritative `GameEngine` at a time.
- Serialize or deterministically order commands that arrive concurrently.
- Associate each command with an authenticated participant and permitted role.
- Reject commands from a player who does not control the requested color.
- Advance the authoritative clock independently of client frame rates.
- Publish authoritative state and event updates to the room's participants.
- Use server receipt time for the move-log timestamp required by the official
  game material.

A gateway may authenticate, route, rate-limit, and transport messages, but it
must not decide game rules. A client, gateway, cache, or presentation component
must never become a competing source of game truth.

### 7.10 Official Scalable Reference Architecture

The official guidance proposes the following default design for the scalable
target:

- `API Gateway` for non-real-time operations such as login, rooms, and history.
- `WebSocket Gateway` for live client connections and state updates.
- `Matchmaker` for pairing players.
- `Game Allocator` for selecting the game-server shard that owns a room.
- `Game Server Shards` for running authoritative `GameEngine` instances.
- `Observability` for logs, metrics, health checks, and load tests.

This is an official reference architecture rather than an instruction to
implement every production-scale component before a basic server works. A
different design requires an explicit reason and must still satisfy the
responsibility boundaries above.

The official technology recommendations are:

- NATS or Redis Pub/Sub for internal messaging.
- Redis for short-lived state such as sessions, active-room routing,
  reconnect information, and matchmaking queues.
- PostgreSQL for durable users, games, results, and move history.
- Docker Compose for a small runnable multi-container deployment.
- Kubernetes or K3s for managed container deployment and horizontal scaling.

SQLite remains suitable only for the earlier small local-server exercise. It
is not the durable database for the stated global scalable target.

## 8. Confirmed Domain Decisions

### 8.1 Concurrent Actions

- Multiple pieces may move concurrently.
- Multiple pieces may jump concurrently.
- Multiple pieces may rest concurrently.
- A piece cannot start another action while that same piece is busy.
- One active piece must not block unrelated pieces.

### 8.2 Timed-Action Ownership

- The real-time arbiter owns active timed actions.
- Move and jump actions use the same authoritative timing infrastructure.
- The game engine must not maintain a second jump or movement clock.
- Piece state must agree with the real-time arbiter's active-action state.

### 8.3 Collision and Capture

The confirmed collision rule is:

> When pieces of different colors collide in the same cell, the piece that arrives later captures the piece that arrived earlier.

This rule applies when one or both pieces were moving.

Capture resolution occurs at a cell arrival boundary and must be deterministic.

### 8.4 Friendly Destination

When a requested destination is occupied by a friendly piece at request time:

- The request is rejected.
- The action does not start.
- Unrelated state remains unchanged unless another explicit rule requires otherwise.

If a moving piece reaches a cell that has become occupied by a friendly piece during transit, it stops at its current safe cell rather than occupying the friendly piece's cell.

### 8.5 Piece Movement and Blocking

#### Rook

- Moves horizontally or vertically.
- A friendly piece blocks the destination and everything beyond it.
- An enemy piece may be captured, but movement cannot continue beyond it.

#### Bishop

- Moves diagonally.
- A friendly piece blocks the destination and everything beyond it.
- An enemy piece may be captured, but movement cannot continue beyond it.

#### Queen

- Uses the combined rook and bishop movement rules.
- It follows the same path-blocking behavior.

#### Knight

- Moves in an L shape.
- Intermediate cells do not block the move.
- A friendly piece on the destination makes the destination illegal.
- An enemy piece on the destination may be captured.

#### King

- Moves one cell in any direction.
- A friendly piece on the destination makes the destination illegal.
- An enemy piece on the destination may be captured.

#### Pawn

- Moves one cell forward into an empty cell.
- May move two cells forward from its starting row only when both cells are empty.
- Captures one cell diagonally forward.
- Does not capture forward.
- Does not move diagonally into an empty cell.

### 8.6 Pawn Promotion

- A pawn that completes a move onto its promotion row is automatically promoted to a queen.
- White promotes on the top row.
- Black promotes on the bottom row.
- Promotion occurs when the move arrives, not when the move request is submitted.
- Promotion does not require a user choice.

### 8.7 Rest Policy

- A completed regular move starts a long rest.
- A completed jump starts a short rest.
- The exact durations are configurable implementation values.
- The important domain rule is the relative policy: move means long rest; jump means short rest.
- Documentation and architecture must not depend on a particular number of milliseconds unless the current configuration itself is being discussed.

### 8.8 Selection

- Clicking an available piece selects it.
- Clicking another available friendly piece replaces the selection.
- Clicking an empty cell with no selection is ignored.
- A destination click with a selected piece sends a move request.
- An illegal move preserves selection.
- An accepted move clears selection.
- Selection belongs to the input/controller layer.

### 8.9 Right-Click Jump

A jump is requested with the right mouse button.

When the jump request is accepted and the jump actually starts:

- Clear every existing selection.
- Clear selection even when another piece was selected.

When the request is rejected, ignored, invalid, outside the board, targets an empty origin, or cannot start:

- Preserve the existing selection.

Selection clearing depends on whether the jump actually started, not merely on receiving a right-click event.

### 8.10 Game Over

- Capturing a king ends the game immediately.
- The winner is the color of the piece that captured the king.
- New move and jump requests are rejected after game over.
- Advancing time after game over does not continue game progression.
- The game-over state is authoritative in the engine and exposed through snapshots.
- Input and UI layers must respect the engine's terminal state rather than inventing separate termination rules.

### 8.11 Board Geometry

Rendering and mouse mapping must use the same board geometry configuration.

`BoardLayout` supports:

- `cell_size`
- `origin_x`
- `origin_y`

Input mapping must respect the rendered board origin and must not independently assume that the board begins at pixel `(0, 0)`.

### 8.12 Board Encapsulation

- External components must not access board-private storage such as `Board._cells`.
- Required iteration must use a focused public API such as `all_pieces()`.
- Public APIs must preserve board invariants.
- Mutable board internals must not be exposed directly.

### 8.13 Snapshots

- Snapshots are immutable representations of observable current state.
- Consumers must not mutate the game through a snapshot.
- Snapshot creation must use public model APIs.
- Mutable engine collections must not be exposed directly.

### 8.14 Game Events

- Events describe facts that already occurred.
- Event ordering must be deterministic.
- Events must not act as hidden commands.
- The model remains authoritative.
- UI animation may consume events but must not determine final game state.
- Long-running consumers must drain event queues through the public event-consumption API.
- A completed winning action must be emitted before `GameOver`, including a move that captures a king at an intermediate cell boundary.
- Final-destination king captures and jump captures must preserve the same completion-before-`GameOver` ordering.
- No `RestStarted` event may be emitted after game over.

### 8.15 Score and Moves History

- Score is presentation state derived from authoritative capture events.
- Each captured piece contributes its configured piece value to the capturing player's score.
- White and Black maintain independent completed-action histories.
- Presentation state preserves the complete history; it must not discard older entries merely because the current panel cannot display them.
- The renderer selects only the newest entries that fit the available panel geometry.
- Within the visible slice, entries are displayed in chronological order.
- Rejected requests and actions that did not complete do not create log entries.
- Promotion notation updates the completed move that caused the promotion.
- The action that wins the game must appear in the moves history before the game-over presentation.

### 8.16 Player Names

- The graphical presentation displays a name for each player.
- The application supplies default player names.
- The default names are `White Player` and `Black Player`.
- The current requirement does not include user-entered names or a name-entry workflow.

### 8.17 Baseline Server Behavior

The recorded baseline server assignment establishes this progression:

- Develop the first server locally, then support two clients on different
  computers over the internet.
- Run client presentation and server game logic in separate processes.
- Let two clients send commands and receive authoritative updates.
- In the first two-player milestone, assign White to the first connected
  player and Black to the second.
- Keep usernames, credential verification, and ratings on the server.
- Start every new rating at 1200 and update ratings using ELO.
- Keep random `Play` matchmaking separate from named-room play.
- Match random players within 100 rating points and report failure after one
  minute without a match.
- On an in-game disconnect, allow a 20-second reconnect countdown before an
  automatic loss and corresponding rating update.
- Use unique room names as the initial room identifiers.
- Treat the room creator and the first joining participant as the two players;
  later joiners are spectators in the recorded demonstration model.
- Do not apply the random-match rating restriction to an explicitly agreed
  named room.
- Write diagnostic logs on both the client and the server.
- Handle near-simultaneous commands deterministically.
- Resynchronize a reconnecting client from authoritative state instead of
  applying delayed local clicks blindly.

The exact registration protocol, password storage policy, authentication-token
format, reconnect message contract, room lifetime, and spectator permissions
are not yet defined by the supplied materials.

The recorded native Windows popup was an input-workflow suggestion for the
server exercise. It does not override the later confirmed rule that displayed
project graphics use `Img`; no popup requirement is active without an explicit
resolution of that conflict.

### 8.18 Scalable-Server Target

The scalable-system design must reason explicitly about:

- 100 million registered users.
- 10 million concurrently active users distributed globally.
- One game action per active user every two seconds on average.
- Games lasting between 30 and 90 seconds on average.
- Room-to-shard ownership and routing.
- Global matchmaking and named-room discovery.
- Network capacity in both directions, including protocol overhead and
  fan-out.
- Service failure, database failure, disk exhaustion, health checks, backup,
  and recovery.
- The consistency-versus-availability trade-off for each type of state.
- The lifecycle and scaling policy of long-lived service containers and
  short-lived game rooms.

The required design deliverable is `Server_Design.md`. It must explain the
services, each service's responsibility, communication paths, data ownership,
capacity assumptions, failure behavior, and design rationale.

The required small implementation target uses Docker Compose. Kubernetes and
K3s are learning and scale-out targets after the basic server exists.

## 9. Repository Organization

The project uses these main areas:

- `kungfu_chess/model`
- `kungfu_chess/rules`
- `kungfu_chess/realtime`
- `kungfu_chess/engine`
- `kungfu_chess/input`
- `kungfu_chess/io`
- `kungfu_chess/texttests`
- `kungfu_chess/ui`
- `kungfu_chess/resources`
- `tests/unit`
- `tests/integration`
- `docs`

Primary entry points:

- `app.py` for the text interface
- `ui_app.py` for the graphical interface

The exact repository tree is implementation evidence and must be reverified from the latest archive when current status matters.

## 10. Testing Requirements

All project tests must be written and executed with Pytest.

Using Pytest only as a runner for `unittest.TestCase` suites is not sufficient for the final project standard. Tests should use native Pytest functions, fixtures, parametrization, and assertion style where appropriate.

Every new behavior requires appropriate tests.

Prefer:

- Focused unit tests
- Integration tests for meaningful collaboration
- Deterministic test inputs
- Explicit behavior-oriented test names
- Native Pytest fixtures and parametrization
- Assertions on observable behavior
- Dependency injection or explicit test seams

Avoid:

- `unittest.TestCase` as the project test structure
- `unittest.mock.patch`
- `patch.object`
- Pytest `monkeypatch`
- Any other runtime replacement of the code under test
- Tests coupled to private implementation details
- Excessive mocking
- Shared mutable test state
- Modifying valid tests only to make the implementation pass
- Duplicate tests without additional coverage

The prohibition on monkey patching includes temporarily replacing functions, methods, classes, module globals, or imported dependencies at runtime. Use dependency injection, fakes, stubs, or focused collaborators instead.

### 10.1 Coverage

The project should strongly aim for 100% unit-test coverage.

This is a quality target, not an automatic claim that every line must be covered regardless of value or that coverage alone proves test quality.

Coverage work should:

- Produce a measurable coverage report.
- Prefer an HTML report that identifies uncovered lines.
- Investigate every uncovered business-logic path.
- Add meaningful behavior tests rather than tests written only to increase a percentage.
- Record any intentionally uncovered code and its justification.

### 10.2 Test Execution

After each meaningful change:

1. Run focused Pytest tests.
2. Run the complete Pytest suite.
3. Generate or update the coverage report when the change affects tested code.
4. Record the exact commands.
5. Record passed, failed, skipped, and errored results.
6. Record the measured coverage when a coverage run was performed.
7. Do not claim full success when the complete suite was not run.

Sandboxed coding-agent runs must provide Pytest with a unique agent-owned
`--basetemp` directory. They must not use Pytest's default per-user temporary
root, because a sandbox can have a different Windows security identity while
still reporting the human user's name. Human developer runs may continue to use
the standard documented command.

Passing tests and high coverage do not by themselves prove that the architecture is correct.

## 11. Git and Environment Constraints

The primary development environment is Windows, Visual Studio Code, Python, Pytest, Git, and GitHub.

NetFree restrictions may prevent some GitHub web operations.

A valid workflow may therefore use:

- A focused feature branch
- Local commit
- Push of the feature branch
- Local merge into `main`
- Full test execution after merge
- Push of `main`

Force push must not be used without explicit justification and approval.

Branches must not be deleted until their changes are committed, pushed, merged, and verified.

## 12. Material Intake Protocol

This chat is the permanent intake point for new official project materials.

For each uploaded email, document, reviewer note, transcript, presentation, screenshot, archive, or other official source:

1. Treat the material as authoritative for what it explicitly states.
2. Identify requirements, clarifications, corrections, recommendations, examples, reviewer feedback, administrative information, and unresolved ambiguities.
3. Compare it with this context, current status, the project record, current official requirements, and available implementation evidence.
4. Identify conflicts and superseded information.
5. Update only the project documents that genuinely need to change.
6. Return each changed Markdown file as a complete file.
7. Do not return unchanged files.
8. Do not modify source code unless implementation is explicitly requested.

## 13. Change Completion Criteria

A project change is complete only when:

- The requirement is clearly defined.
- Responsibility is assigned to the correct layer.
- The design preserves architectural boundaries.
- The implementation is focused and readable.
- Relevant native-Pytest tests are added or updated.
- Tests do not use monkey patching or runtime replacement of the code under test.
- Focused tests pass.
- The complete Pytest suite passes.
- Coverage is measured when appropriate and meaningful gaps are addressed.
- The diff contains only intended changes.
- No unrequested future feature was introduced.
- Remaining risks are recorded.
- Git state is safe and verified.
- Project documentation is updated when the change affects recorded context or status.

This section applies to completing individual changes. It is not a declaration of the final completion criteria for the entire Kung-Fu Chess project.
