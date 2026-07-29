# Kung-Fu Chess

Kung-Fu Chess is a real-time chess variant in which pieces move and act
concurrently instead of taking alternating turns. The current implementation
supports timed movement, jumps, captures and collision resolution, configurable
short and long rest periods, graphical and text-based interfaces, and automatic
pawn promotion to a queen.

## Requirements

- Python 3.10 or newer. The code uses Python 3.10 syntax and was verified locally
  with Python 3.13.7 on Windows.
- A desktop environment is required to open the graphical OpenCV window. A
  headless terminal is sufficient for the text interface and automated tests.

The repository does not formally certify operating-system compatibility beyond
the locally verified environment.

## Installation

From the repository root, create and activate a virtual environment in Windows
PowerShell, then install the direct project dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Running the Graphical Game

`ui_app.py` is the graphical entry point:

```powershell
python ui_app.py
```

Run the command from the repository root. The application loads the standard
board, cooldown configuration, board image, and piece sprites included under
`kungfu_chess/resources` and `kungfu_chess/ui/assets`.

## Graphical Controls

| Input | Action |
| --- | --- |
| Left-click an available piece | Select it. Clicking another available friendly piece changes the selection. |
| Left-click a destination | Request a move for the selected piece. |
| Left-click outside the board | Cancel the current selection. |
| Right-click a piece's cell | Request a jump for that piece; no prior selection is required. |
| `Esc`, `q`, or `Q` | Close the game window. |
| Window close button (`X`) | Close the game window. |

An accepted move or jump clears the current selection. A rejected request keeps
the selection so another action can be attempted.

## Running the Text Interface

`app.py` is the text entry point. It reads a command script from standard input
until end-of-file. Scripts define a board and may use pixel-coordinate `click`
and `jump` commands, millisecond `wait` commands, and `print board`.

This PowerShell example prints a two-piece board:

```powershell
@'
Board:
wK .
. bK
Commands:
print board
'@ | python app.py
```

## Running Tests

Run the complete unit and integration suite from the repository root:

```powershell
python -m pytest -q
```

## Measuring Coverage

Run the branch-aware whole-project coverage workflow from the repository root:

```powershell
python -m coverage erase
python -m coverage run -m pytest
python -m coverage report -m
python -m coverage html
```

The committed configuration measures the complete `kungfu_chess` package,
reports missing lines, and enforces the verified baseline of 94.91%. The HTML
report is generated at `htmlcov/index.html`. The `.coverage` data file and
`htmlcov/` report directory are generated artifacts and must not be committed.

## Project Structure

```text
app.py                       Text-interface entry point
ui_app.py                    Graphical entry point
kungfu_chess/model           Game entities, events, snapshots, and settled board state
kungfu_chess/rules           Chess move and jump legality validation
kungfu_chess/realtime        Timed motions, jumps, rests, and action scheduling
kungfu_chess/engine          Authoritative coordination of rules and game transitions
kungfu_chess/input           Pixel mapping, selection, and controller-to-engine requests
kungfu_chess/io              Board parsing and text rendering
kungfu_chess/ui              OpenCV window, rendering, animation, and sprite loading
kungfu_chess/texttests       Text-script parser and runner
kungfu_chess/resources       Standard board and runtime configuration
tests                        Unit and integration tests
docs                         Project development guidance
```

The model owns game entities and settled state. Rules determine legality, while
the real-time layer owns scheduled actions and cooldowns. The engine coordinates
authoritative transitions across those layers. The input/controller layer
translates user actions into engine requests, and the UI renders engine snapshots
and delegates mouse input to the controller.

## Important Gameplay Notes

- Multiple pieces may move, jump, or rest concurrently.
- A busy piece cannot start another action until its current motion or rest ends.
- Right-click requests a jump on the clicked piece.
- A completed regular move starts the configured long rest; a completed jump
  starts the configured short rest.
- A pawn reaching its promotion row is automatically promoted to a queen.
- Capturing a king ends the game and prevents further actions.

## Repository Resources

The graphical assets, standard-board definition, and game configuration included
in `kungfu_chess/ui/assets` and `kungfu_chess/resources` are required by the
graphical application. Keep these directories with the source tree; no separate
course-asset download is needed.

## Development Notes

Run the complete test suite after making changes. Source code and technical
documentation are written in English. Do not commit generated caches, local
virtual environments, or other machine-specific files.
