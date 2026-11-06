"""
Rubik's Cube Camera Scanner + Solver
====================================

Python 3.10+
Required packages: pyserial, OpenCV, NumPy and one Kociemba implementation.

The six-snapshot camera routine is embedded directly in this file. During a
hardware scan the ESP32 handles motor moves only; a continuously capturing
camera reader supplies stage-tagged three-frame bursts while colour
classification overlaps the following motor movements.

The final restoration block is intentionally omitted. After a successful scan,
the reconstructed URFDLB state is transformed virtually to the cube's current
physical state, regular Kociemba validates and solves it, and a verified
five-face physical robot solution can be sent to the ESP32 from the GUI.

Expected ESP32 serial protocol:
    PING                 -> PONG
    F / R' / L2 / ...    -> DONE <command>
"""

from __future__ import annotations

import argparse
import heapq
import json
import math
import platform
import queue
import threading
import time
import tkinter as tk
from collections import Counter, deque
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Protocol

from robot_solver import (
    FiveFaceSolverError,
    apply_moves,
    solve_physical_facelets_without_u,
)

try:
    import cv2
    import numpy as np
except ImportError:  # Report missing camera dependencies when Solve is clicked.
    cv2 = None
    np = None

try:
    import serial
    from serial import Serial
except ImportError:  # Report missing serial dependencies when Solve is clicked.
    serial = None
    Serial = object  # type: ignore[assignment,misc]


CAMERA_SLOTS = (
    "U1", "U2", "U3", "U4",
    "U6", "U7", "U8", "U9",
)

CAMERA_SCAN_MAPPINGS = (
    ("U1", "U2", "U3", "U4", "U6", "U7", "U8", "U9"),
    ("F3", "R6", "F9", "F2", "F8", "F1", "R4", "F7"),
    ("R1", "R2", "R3", "B4", "B6", "R7", "R8", "R9"),
    ("D9", "D8", "D7", "D6", "D4", "D3", "D2", "D1"),
    ("B7", "L4", "B1", "B8", "B2", "B9", "L6", "B3"),
    ("L1", "L2", "L3", "F4", "F6", "L7", "L8", "L9"),
)

SCAN_MOVE_BLOCK_A = ("F'", "B", "L'", "R")
SCAN_MOVE_BLOCK_B = ("F'", "B", "L", "R'")
SCAN_MOVE_BLOCKS = (
    SCAN_MOVE_BLOCK_A,
    SCAN_MOVE_BLOCK_B,
    SCAN_MOVE_BLOCK_A,
    SCAN_MOVE_BLOCK_B,
    SCAN_MOVE_BLOCK_A,
    SCAN_MOVE_BLOCK_B,
)
OMITTED_RESTORATION_MOVES = SCAN_MOVE_BLOCKS[-1]
ACTIVE_SCAN_MOVE_BLOCKS = SCAN_MOVE_BLOCKS[:-1]
EMBEDDED_MOVE_SEQUENCE = tuple(move for block in ACTIVE_SCAN_MOVE_BLOCKS for move in block)
DEFAULT_ROI_FILE = Path(__file__).resolve().parent / "camera_calibration.json"

# ---------------------------------------------------------------------------
# Cube definitions
# ---------------------------------------------------------------------------

COLOURS = ("WHITE", "YELLOW", "ORANGE", "RED", "GREEN", "BLUE")
COLOUR_SET = set(COLOURS)


@dataclass(frozen=True)
class ColourReading:
    """One classified colour with probabilities and optional camera diagnostics."""

    colour: str
    probabilities: dict[str, float]
    source: str
    bgr: tuple[int, int, int] | None = None
    hsv: tuple[int, int, int] | None = None
    camera_slot: str | None = None
    camera_stage: int | None = None
    classifier_confidence: float | None = None

    def __post_init__(self) -> None:
        colour = self.colour.upper()
        probabilities = {
            str(key).upper(): float(value)
            for key, value in self.probabilities.items()
        }
        if colour not in COLOUR_SET:
            raise ControllerError(f"Unsupported reading colour: {self.colour!r}")
        if set(probabilities) != COLOUR_SET:
            raise ControllerError("A colour reading must contain exactly all six cube colours.")
        if any(value < 0.0 for value in probabilities.values()):
            raise ControllerError("A colour reading cannot contain a negative probability.")
        if not math.isclose(sum(probabilities.values()), 1.0, rel_tol=0.0, abs_tol=1e-6):
            raise ControllerError("Colour reading probabilities must sum to 1.0.")
        if not isinstance(self.source, str) or not self.source.strip():
            raise ControllerError("A colour reading must include a source.")
        if self.camera_slot is not None and self.camera_slot not in CAMERA_SLOTS:
            raise ControllerError(f"Unsupported camera slot: {self.camera_slot!r}")
        if self.camera_stage is not None and not 1 <= self.camera_stage <= 6:
            raise ControllerError(f"Unsupported camera stage: {self.camera_stage!r}")
        if self.classifier_confidence is not None and not 0.0 <= self.classifier_confidence <= 1.0:
            raise ControllerError("Classifier confidence must be between 0 and 1.")
        object.__setattr__(self, "colour", colour)
        object.__setattr__(self, "probabilities", probabilities)


@dataclass(frozen=True)
class FaceletConfidence:
    colour: str
    probability: float
    second_colour: str
    second_probability: float
    margin: float
    observation_count: int
    agreeing_observations: int
    confirmed: bool
    conflicted: bool
    probabilities: dict[str, float]


def aggregate_colour_readings(readings: list[ColourReading]) -> FaceletConfidence:
    """Combine independent physical readings by summing their log probabilities."""
    if not readings:
        raise ValueError("At least one physical colour reading is required.")
    log_scores = {
        colour: sum(math.log(max(reading.probabilities[colour], 1e-9)) for reading in readings)
        for colour in COLOURS
    }
    largest = max(log_scores.values())
    weights = {colour: math.exp(score - largest) for colour, score in log_scores.items()}
    total = sum(weights.values())
    probabilities = {colour: weights[colour] / total for colour in COLOURS}
    ranked = sorted(COLOURS, key=lambda colour: (-probabilities[colour], colour))
    colour, second_colour = ranked[:2]
    probability = probabilities[colour]
    second_probability = probabilities[second_colour]
    agreeing = sum(reading.colour == colour for reading in readings)
    conflicted = len({reading.colour for reading in readings}) > 1
    is_single_camera_reading = (
        len(readings) == 1 and readings[0].camera_slot is not None
    )
    confirmed = (
        is_single_camera_reading
        and probability >= 0.80
        and probability - second_probability >= 0.25
    ) or (
        len(readings) >= 2
        and agreeing >= 2
        and probability >= 0.85
        and probability - second_probability >= 0.30
    )
    return FaceletConfidence(
        colour=colour,
        probability=probability,
        second_colour=second_colour,
        second_probability=second_probability,
        margin=probability - second_probability,
        observation_count=len(readings),
        agreeing_observations=agreeing,
        confirmed=confirmed,
        conflicted=conflicted,
        probabilities=probabilities,
    )

FIXED_CENTRES = {
    "U5": "WHITE",
    "D5": "YELLOW",
    "L5": "ORANGE",
    "R5": "RED",
    "F5": "GREEN",
    "B5": "BLUE",
}


ALL_FACELETS = tuple(
    f"{face}{position}" for face in "ULFRBD" for position in range(1, 10)
)
OUTER_FACELETS = tuple(item for item in ALL_FACELETS if not item.endswith("5"))

# Standard facelet numbering while looking directly at each face.
EDGE_FACELET_PAIRS = (
    ("U2", "B2"),
    ("U4", "L2"),
    ("U6", "R2"),
    ("U8", "F2"),
    ("D2", "F8"),
    ("D4", "L8"),
    ("D6", "R8"),
    ("D8", "B8"),
    ("F4", "L6"),
    ("F6", "R4"),
    ("B4", "R6"),
    ("B6", "L4"),
)

CORNER_FACELET_TRIPLES = (
    ("U9", "R1", "F3"),
    ("U7", "F1", "L3"),
    ("U1", "L1", "B3"),
    ("U3", "B1", "R3"),
    ("D3", "F9", "R7"),
    ("D1", "L9", "F7"),
    ("D7", "B9", "L7"),
    ("D9", "R9", "B7"),
)

VALID_CORNER_SETS = {
    frozenset(FIXED_CENTRES[f"{facelet[0]}5"] for facelet in triple)
    for triple in CORNER_FACELET_TRIPLES
}

OPPOSITE_COLOURS = {
    frozenset(("WHITE", "YELLOW")),
    frozenset(("ORANGE", "RED")),
    frozenset(("GREEN", "BLUE")),
}

VALID_EDGE_PAIRS = tuple(
    frozenset((first, second))
    for index, first in enumerate(COLOURS)
    for second in COLOURS[index + 1 :]
    if frozenset((first, second)) not in OPPOSITE_COLOURS
)

SUPPORTED_MOVES = {
    "F", "F'", "F2",
    "R", "R'", "R2",
    "L", "L'", "L2", "L45", "L45'",
    "B", "B'", "B2",
    "D", "D'", "D2",
}


# ---------------------------------------------------------------------------
# Routine model and validation
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Action:
    type: str
    value: str = ""
    mapping: tuple[str, ...] = ()

    def validate(self) -> None:
        if self.type == "move":
            if self.value not in SUPPORTED_MOVES:
                raise ValueError(f"Unsupported move: {self.value!r}")
            if self.mapping:
                raise ValueError("A move action cannot contain a camera mapping.")
            return
        if self.type == "camera_scan":
            if self.value:
                raise ValueError("A camera scan cannot contain a move value.")
            if len(self.mapping) != len(CAMERA_SLOTS):
                raise ValueError("Every camera scan must contain exactly eight mappings.")
            invalid = [facelet for facelet in self.mapping if facelet not in OUTER_FACELETS]
            if invalid:
                raise ValueError(f"Invalid or centre camera mapping: {invalid[0]}")
            return
        raise ValueError(f"Unsupported action type: {self.type!r}")


@dataclass(frozen=True)
class Routine:
    source: str
    actions: tuple[Action, ...]

    @classmethod
    def embedded(cls) -> "Routine":
        actions: list[Action] = []
        for stage_index, mapping in enumerate(CAMERA_SCAN_MAPPINGS):
            actions.append(Action(type="camera_scan", mapping=mapping))
            if stage_index < len(ACTIVE_SCAN_MOVE_BLOCKS):
                actions.extend(
                    Action(type="move", value=move)
                    for move in ACTIVE_SCAN_MOVE_BLOCKS[stage_index]
                )
        routine = cls("embedded six-snapshot camera routine", tuple(actions))
        routine.validate()
        return routine

    def validate(self) -> None:
        for action in self.actions:
            action.validate()
        scans = [action for action in self.actions if action.type == "camera_scan"]
        moves = [action.value for action in self.actions if action.type == "move"]
        if len(self.actions) != 26:
            raise ValueError("The embedded camera routine must contain exactly 26 actions.")
        if len(scans) != 6:
            raise ValueError("The embedded camera routine must contain exactly six camera scans.")
        if len(moves) != 20:
            raise ValueError("The embedded camera routine must contain exactly 20 scan moves.")
        if tuple(moves) != EMBEDDED_MOVE_SEQUENCE:
            raise ValueError("The embedded move sequence does not match its fixed constants.")
        if scans[0].mapping != CAMERA_SLOTS:
            raise ValueError("Camera scan 1 must be the identity U-face mapping.")
        mapped = [facelet for action in scans for facelet in action.mapping]
        counts = Counter(mapped)
        if set(counts) != set(OUTER_FACELETS) or any(count != 1 for count in counts.values()):
            missing = sorted(set(OUTER_FACELETS) - set(mapped))
            duplicated = sorted(facelet for facelet, count in counts.items() if count != 1)
            raise ValueError(
                "Camera mappings must cover all 48 non-centre facelets exactly once; "
                f"missing={missing}, duplicated={duplicated}."
            )
        expected_types = tuple(
            action_type
            for _ in range(5)
            for action_type in ("camera_scan", "move", "move", "move", "move")
        ) + ("camera_scan",)
        if tuple(action.type for action in self.actions) != expected_types:
            raise ValueError(
                "The first five camera scans must be followed by four moves, and "
                "camera scan 6 must be the final action."
            )
        actual_blocks = tuple(
            tuple(self.actions[index + offset].value for offset in range(1, 5))
            for index in range(0, 25, 5)
        )
        if actual_blocks != ACTIVE_SCAN_MOVE_BLOCKS:
            raise ValueError("Active camera move blocks must alternate exactly A, B, A, B, A.")
        if self.actions[-1].type != "camera_scan":
            raise ValueError("Camera scan 6 must be the final embedded action.")

    @property
    def camera_scan_count(self) -> int:
        return sum(action.type == "camera_scan" for action in self.actions)

    @property
    def mapped_reading_count(self) -> int:
        return sum(
            len(action.mapping)
            for action in self.actions
            if action.type == "camera_scan"
        )

    @property
    def camera_mappings(self) -> tuple[tuple[str, ...], ...]:
        return tuple(
            action.mapping for action in self.actions if action.type == "camera_scan"
        )

    @property
    def move_sequence(self) -> tuple[str, ...]:
        return tuple(action.value for action in self.actions if action.type == "move")

# Cube inventory validation
# ---------------------------------------------------------------------------

class CubeValidationError(ValueError):
    """The reconstructed colours cannot describe a complete legal inventory."""


def _known_colour_counts(state: dict[str, str]) -> Counter[str]:
    counts = Counter(state.values())
    invalid = set(counts) - COLOUR_SET
    if invalid:
        raise CubeValidationError(f"Unsupported known colour: {sorted(invalid)[0]}")
    for colour in COLOURS:
        if counts[colour] > 9:
            raise CubeValidationError(
                f"Too many {colour} facelets: {counts[colour]} (maximum 9)."
            )
    return counts


def validate_complete_cube_colours(state: dict[str, str]) -> None:
    missing = [facelet for facelet in ALL_FACELETS if facelet not in state]
    if missing:
        raise CubeValidationError("Cube is incomplete: " + ", ".join(missing))
    counts = _known_colour_counts(state)
    wrong = {colour: counts[colour] for colour in COLOURS if counts[colour] != 9}
    if wrong:
        raise CubeValidationError(f"Final colour counts are invalid: {wrong}")
    edge_pairs = [
        frozenset((state[first], state[second]))
        for first, second in EDGE_FACELET_PAIRS
    ]
    if set(edge_pairs) != set(VALID_EDGE_PAIRS) or len(set(edge_pairs)) != 12:
        raise CubeValidationError("Final edge-piece inventory is invalid.")


def validate_corner_inventory(state: dict[str, str]) -> None:
    """Cheap unordered corner inventory check; Kociemba remains final authority."""
    corner_sets = [
        frozenset(state[facelet] for facelet in triple)
        for triple in CORNER_FACELET_TRIPLES
    ]
    if set(corner_sets) != VALID_CORNER_SETS or len(set(corner_sets)) != 8:
        raise CubeValidationError("Final corner-piece inventory is invalid.")

# Regular Kociemba legality validation + five-face physical solving
# ---------------------------------------------------------------------------

KOCIEMBA_FACE_ORDER = "URFDLB"
COLOUR_CUBE_ORDER = "ULFRBD"
COLOUR_TO_FACE = {
    colour: facelet[0] for facelet, colour in FIXED_CENTRES.items()
}
FACE_TO_COLOUR = {face: colour for colour, face in COLOUR_TO_FACE.items()}
COLOUR_TO_INITIAL = {
    "WHITE": "W",
    "YELLOW": "Y",
    "ORANGE": "O",
    "RED": "R",
    "GREEN": "G",
    "BLUE": "B",
}
SOLVED_KOCIEMBA_FACELETS = "".join(face * 9 for face in KOCIEMBA_FACE_ORDER)


STANDARD_SOLVER_MOVES = {
    face + suffix
    for face in KOCIEMBA_FACE_ORDER
    for suffix in ("", "'", "2")
}


class SolverError(RuntimeError):
    pass


@dataclass(frozen=True)
class SolvePlan:
    facelets: str
    standard_moves: tuple[str, ...]
    executable_moves: tuple[str, ...]

    @property
    def standard_text(self) -> str:
        return " ".join(self.standard_moves) or "Already solved"

    @property
    def executable_text(self) -> str:
        return " ".join(self.executable_moves) or "No moves required"

    @property
    def replaced_u_count(self) -> int:
        return sum(move.startswith("U") for move in self.standard_moves)


def build_kociemba_facelets(state: dict[str, str]) -> str:
    """Return the scanned cube in Kociemba's U1..B9 / URFDLB order."""
    validate_complete_cube_colours(state)
    output: list[str] = []
    for face in KOCIEMBA_FACE_ORDER:
        for position in range(1, 10):
            facelet = f"{face}{position}"
            colour = state.get(facelet)
            try:
                output.append(COLOUR_TO_FACE[colour])
            except KeyError as exc:
                raise SolverError(
                    f"Cannot convert {facelet} colour {colour!r} to Kociemba notation."
                ) from exc
    facelets = "".join(output)
    if len(facelets) != 54:
        raise SolverError(f"Expected 54 Kociemba facelets, produced {len(facelets)}.")
    return facelets


def invert_move_sequence(moves: tuple[str, ...]) -> tuple[str, ...]:
    """Return the group inverse of a standard move sequence."""
    inverse: list[str] = []
    for move in reversed(moves):
        move = move.strip().replace("’", "'")
        if move not in (SUPPORTED_MOVES | STANDARD_SOLVER_MOVES) or move.startswith("L45"):
            raise ValueError(f"Cannot invert unsupported virtual move: {move!r}")
        if move.endswith("2"):
            inverse.append(move)
        elif move.endswith("'"):
            inverse.append(move[:-1])
        else:
            inverse.append(move + "'")
    return tuple(inverse)


def cube_state_from_kociemba_facelets(facelets: str) -> dict[str, str]:
    """Convert a 54-character URFDLB facelet string back to logical colours."""
    if len(facelets) != 54:
        raise SolverError(f"Expected 54 Kociemba facelets, received {len(facelets)}.")
    invalid = sorted(set(facelets) - set(KOCIEMBA_FACE_ORDER))
    if invalid:
        raise SolverError(f"Unsupported Kociemba face letters: {invalid}")
    state = {
        f"{face}{position}": FACE_TO_COLOUR[facelets[index]]
        for index, (face, position) in enumerate(
            (face_position, position)
            for face_position in KOCIEMBA_FACE_ORDER
            for position in range(1, 10)
        )
    }
    validate_complete_cube_colours(state)
    return state


def adjusted_state_for_omitted_restoration(
    reconstructed_state: dict[str, str],
) -> tuple[dict[str, str], str, tuple[str, ...], str]:
    """Map the reconstructed pre-scan state to the current post-scan state."""
    reconstructed_facelets = build_kociemba_facelets(reconstructed_state)
    inverse_moves = invert_move_sequence(OMITTED_RESTORATION_MOVES)
    adjusted_facelets = apply_moves(reconstructed_facelets, inverse_moves)
    adjusted_state = cube_state_from_kociemba_facelets(adjusted_facelets)
    return adjusted_state, reconstructed_facelets, inverse_moves, adjusted_facelets


def _regular_kociemba_solution(facelets: str, state: dict[str, str]) -> tuple[str, ...]:
    """Run the established Kociemba path; callers may discard its move sequence."""
    if facelets == SOLVED_KOCIEMBA_FACELETS:
        return ()
    try:
        import kociemba
    except ImportError:
        kociemba = None

    try:
        if kociemba is not None:
            solution = kociemba.solve(facelets)
        else:
            try:
                from cube_solver import Cube, Kociemba
            except ImportError as exc:
                raise SolverError(
                    "No supported Kociemba package is installed in this virtual "
                    "environment. On Windows install the wheel-backed option with: "
                    "python -m pip install cube-solver"
                ) from exc
            colour_string = "".join(
                COLOUR_TO_INITIAL[state[f"{face}{position}"]]
                for face in COLOUR_CUBE_ORDER
                for position in range(1, 10)
            )
            result = Kociemba().solve(Cube(repr=colour_string))
            if result is None:
                raise SolverError("The Kociemba search returned no solution.")
            solution = str(result)
    except SolverError:
        raise
    except Exception as exc:
        raise SolverError(
            "Kociemba rejected the scanned cube. This normally means at least one "
            f"facelet mapping/colour is wrong. Details: {exc}"
        ) from exc
    return tuple(str(solution).split())


def validate_cube_state_legality(state: dict[str, str]) -> None:
    """Use normal Kociemba only as the final legality authority."""
    facelets = build_kociemba_facelets(state)
    _regular_kociemba_solution(facelets, state)


FIVE_FACE_SOLVER_DIRECTORY = Path(__file__).resolve().parent / "five_face_solver"


def solve_final_cube_state_without_u(state: dict[str, str]) -> SolvePlan:
    """Create the verified robot plan from the selected legal physical cube state."""
    facelets = build_kociemba_facelets(state)
    standard_moves = _regular_kociemba_solution(facelets, state)
    if facelets == SOLVED_KOCIEMBA_FACELETS:
        return SolvePlan(facelets, (), ())
    try:
        physical_moves = tuple(
            solve_physical_facelets_without_u(
                facelets,
                solver_directory=FIVE_FACE_SOLVER_DIRECTORY,
            )
        )
    except FiveFaceSolverError as exc:
        raise SolverError(f"Five-face physical solver failed: {exc}") from exc
    if any(move.startswith("U") for move in physical_moves):
        raise SolverError("Five-face mapping produced an unavailable physical U move.")
    return SolvePlan(facelets, standard_moves, physical_moves)


# ---------------------------------------------------------------------------
# Motor controller and grouped camera capture
# ---------------------------------------------------------------------------

BAUD_RATE = 115200
SERIAL_READ_TIMEOUT_SECONDS = 0.10
MOVE_TIMEOUT_SECONDS = 30.0
OPENING_DELAY_SECONDS = 2.0
CAMERA_SETTLE_SECONDS = 0.05
CAMERA_BURST_FRAMES = 3
CAMERA_BURST_TIMEOUT_SECONDS = 1.5

HUE_REFERENCES = {
    "RED": 0,
    "ORANGE": 12,
    "YELLOW": 30,
    "GREEN": 60,
    "BLUE": 110,
}


class ControllerError(RuntimeError):
    pass


class ScanStopped(RuntimeError):
    pass


def convert_move_for_controller(move: str) -> str:
    """Preserve the direction conversion used by the previous working GUI."""
    unchanged = {"F", "F'", "F2", "D2", "R2", "L2", "B2"}
    if move in unchanged:
        return move
    swaps = {
        "D": "D'", "D'": "D",
        "R": "R'", "R'": "R",
        "L": "L'", "L'": "L",
        "B": "B'", "B'": "B",
        "L45": "L45'", "L45'": "L45",
    }
    if move not in swaps:
        raise ValueError(f"Unsupported move: {move}")
    return swaps[move]


class ControllerProtocol(Protocol):
    def open(self) -> None: ...
    def close(self) -> None: ...
    def move(self, command: str) -> None: ...


@dataclass(frozen=True)
class CameraBurst:
    stage_id: int
    mapping: tuple[str, ...]
    frame_timestamps: tuple[float, ...]
    frames: tuple[object, ...]


@dataclass(frozen=True)
class CameraClassification:
    stage_id: int
    mapping: tuple[str, ...]
    readings: tuple[ColourReading, ...]


class CameraReaderProtocol(Protocol):
    def open(self) -> None: ...
    def close(self) -> None: ...
    def capture_burst(
        self,
        stage_id: int,
        mapping: tuple[str, ...],
        after_time: float | None,
    ) -> CameraBurst: ...
    def classify_burst(self, burst: CameraBurst) -> CameraClassification: ...


class ESP32Controller:
    def __init__(self, port: str, events: queue.Queue, stop_event: threading.Event):
        self.port = port
        self.events = events
        self.stop_event = stop_event
        self.connection: Optional[Serial] = None

    def log(self, message: str) -> None:
        self.events.put(("log", message))

    def _check_stopped(self) -> None:
        if self.stop_event.is_set():
            raise ScanStopped("Scan stopped by the user.")

    def open(self) -> None:
        if serial is None:
            raise ControllerError("pyserial is not installed. Run: python -m pip install pyserial")
        self.log(f"Opening {self.port} at {BAUD_RATE} baud...")
        self.connection = serial.Serial(
            self.port,
            BAUD_RATE,
            timeout=SERIAL_READ_TIMEOUT_SECONDS,
            write_timeout=2.0,
        )
        time.sleep(OPENING_DELAY_SECONDS)
        self.connection.reset_input_buffer()
        self.connection.reset_output_buffer()
        response = self.send_and_wait("PING", ("PONG",), 5.0)
        if response != "PONG":
            raise ControllerError(f"Unexpected PING response: {response}")
        self.log("ESP32 connection confirmed.")

    def close(self) -> None:
        if self.connection is not None and self.connection.is_open:
            self.connection.close()
            self.log("Serial connection closed.")

    def _read_line(self) -> str | None:
        if self.connection is None:
            raise ControllerError("Serial connection is not open.")
        raw = self.connection.readline()
        if not raw:
            return None
        return raw.decode("utf-8", errors="replace").strip()

    def _write(self, command: str) -> None:
        self._check_stopped()
        if self.connection is None:
            raise ControllerError("Serial connection is not open.")
        self.log(f"-> {command}")
        self.connection.write((command + "\n").encode("ascii"))
        self.connection.flush()

    def send_and_wait(
        self,
        command: str,
        prefixes: tuple[str, ...],
        timeout_seconds: float,
    ) -> str:
        self._write(command)
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            self._check_stopped()
            line = self._read_line()
            if not line:
                continue
            if line == "READY" or line.startswith("DEBUG "):
                self.log(f"ESP32: {line}")
                continue
            if line.startswith("ERROR "):
                self.log(f"<- {line}")
                raise ControllerError(line)
            if line.startswith(prefixes):
                self.log(f"<- {line}")
                return line
            self.log(f"ESP32: {line}")
        raise ControllerError(f"Timed out waiting for {command!r}.")

    def move(self, command: str) -> None:
        response = self.send_and_wait(command, ("DONE ",), MOVE_TIMEOUT_SECONDS)
        if response != f"DONE {command}":
            raise ControllerError(f"Expected 'DONE {command}', received {response!r}.")


@dataclass(frozen=True)
class Region:
    label: str
    points: object


def _require_opencv() -> None:
    if cv2 is None or np is None:
        raise ControllerError(
            "Camera scanning requires OpenCV and NumPy. Run: "
            "python -m pip install opencv-python numpy"
        )


def load_roi_config(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Could not find ROI calibration file: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("ROI calibration root must be a JSON object.")
    regions = data.get("regions")
    if not isinstance(regions, dict) or set(regions) != set(CAMERA_SLOTS):
        raise ValueError(
            "ROI calibration must contain exactly U1, U2, U3, U4, U6, U7, U8 and U9."
        )
    camera = data.get("camera")
    if not isinstance(camera, dict):
        raise ValueError("ROI calibration has no camera settings.")
    for name in ("frame_width", "frame_height"):
        if int(camera.get(name, 0)) <= 0:
            raise ValueError(f"ROI calibration camera.{name} must be positive.")
    int(camera.get("index", 0))
    for label in CAMERA_SLOTS:
        item = regions[label]
        if not isinstance(item, dict):
            raise ValueError(f"ROI {label} must be an object.")
        points = item.get("points_normalized", item.get("points_pixels"))
        if (
            not isinstance(points, list)
            or len(points) != 4
            or any(not isinstance(point, list) or len(point) != 2 for point in points)
        ):
            raise ValueError(f"{label} must contain four [x, y] corner points.")
        try:
            for point in points:
                float(point[0])
                float(point[1])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{label} contains a non-numeric coordinate.") from exc
    return data


def regions_for_frame(data: dict, frame_width: int, frame_height: int) -> list[Region]:
    _require_opencv()
    saved_camera = data.get("camera", {})
    saved_width = float(saved_camera.get("frame_width", frame_width))
    saved_height = float(saved_camera.get("frame_height", frame_height))
    regions: list[Region] = []
    for label in CAMERA_SLOTS:
        item = data["regions"][label]
        if "points_normalized" in item:
            points = np.asarray(item["points_normalized"], dtype=np.float32)
            if points.shape != (4, 2):
                raise ValueError(f"{label} must contain four [x, y] corner points.")
            points[:, 0] *= frame_width
            points[:, 1] *= frame_height
        elif "points_pixels" in item:
            points = np.asarray(item["points_pixels"], dtype=np.float32)
            if points.shape != (4, 2):
                raise ValueError(f"{label} must contain four [x, y] corner points.")
            points[:, 0] *= frame_width / saved_width
            points[:, 1] *= frame_height / saved_height
        else:
            raise ValueError(f"{label} has neither normalized nor pixel points.")
        regions.append(Region(label, points))
    return regions


def make_inset_contour(points, scale: float = 0.86):
    """Shrink a polygon toward its centre to stay away from sticker edges."""
    _require_opencv()
    centre = np.mean(points, axis=0)
    inset = centre + (points - centre) * scale
    return np.round(inset).astype(np.int32)


def median_bgr_in_region(frame, points):
    """Use the tested inset, mask, trimming and median sampling behaviour."""
    _require_opencv()
    contour = make_inset_contour(points)
    mask = np.zeros(frame.shape[:2], dtype=np.uint8)
    cv2.fillPoly(mask, [contour], 255)
    pixels = frame[mask == 255]
    if len(pixels) < 20:
        return None
    brightness = np.max(pixels, axis=1)
    lower, upper = np.percentile(brightness, [10, 90])
    trimmed = pixels[(brightness >= lower) & (brightness <= upper)]
    if len(trimmed) >= 20:
        pixels = trimmed
    return np.median(pixels, axis=0).astype(np.float32)


def bgr_to_hsv(bgr) -> tuple[int, int, int]:
    _require_opencv()
    pixel = np.clip(np.round(bgr), 0, 255).astype(np.uint8).reshape(1, 1, 3)
    hsv = cv2.cvtColor(pixel, cv2.COLOR_BGR2HSV)[0, 0]
    return int(hsv[0]), int(hsv[1]), int(hsv[2])


def circular_hue_distance(first: float, second: float) -> float:
    difference = abs(first - second)
    return min(difference, 180.0 - difference)


def classify_hsv(hue: int, saturation: int, value: int) -> tuple[str, float]:
    """The physically tested live detector's HSV classifier."""
    if value < 45:
        return "UNKNOWN", 0.0
    if saturation < 60:
        if value >= 90:
            whiteness = 1.0 - saturation / 60.0
            brightness = min(1.0, (value - 70.0) / 100.0)
            confidence = 0.45 + 0.4 * whiteness + 0.15 * brightness
            return "WHITE", max(0.0, min(1.0, confidence))
        return "UNKNOWN", 0.0
    distances = sorted(
        (circular_hue_distance(hue, reference), colour)
        for colour, reference in HUE_REFERENCES.items()
    )
    nearest_distance, colour = distances[0]
    second_distance = distances[1][0]
    separation = max(
        0.0,
        (second_distance - nearest_distance) / max(second_distance, 1.0),
    )
    saturation_strength = min(1.0, (saturation - 45.0) / 150.0)
    confidence = 0.75 * separation + 0.25 * saturation_strength
    return colour, max(0.0, min(1.0, confidence))


def camera_probabilities(
    winner: str,
    confidence: float,
    hue: int,
) -> dict[str, float]:
    """Convert camera confidence to the six-colour distribution used by repair."""
    if winner not in COLOUR_SET:
        raise ControllerError(f"Cannot build probabilities for {winner!r}.")
    confidence = max(0.0, min(1.0, float(confidence)))
    winner_probability = max(0.70, min(0.98, 0.70 + 0.28 * confidence))
    remaining = 1.0 - winner_probability
    hue_ranking = sorted(
        HUE_REFERENCES,
        key=lambda colour: (
            circular_hue_distance(hue, HUE_REFERENCES[colour]),
            colour,
        ),
    )
    if winner == "RED":
        second = "ORANGE"
        second_share = 0.65
    elif winner == "ORANGE":
        second = "RED"
        second_share = 0.65
    elif winner == "WHITE":
        second = hue_ranking[0]
        second_share = 0.50
    else:
        second = next(colour for colour in hue_ranking if colour != winner)
        second_share = 0.50
    second_probability = remaining * second_share
    other_colours = [colour for colour in COLOURS if colour not in {winner, second}]
    other_probability = (remaining - second_probability) / len(other_colours)
    probabilities = {colour: other_probability for colour in COLOURS}
    probabilities[winner] = winner_probability
    probabilities[second] = second_probability
    probabilities[winner] += 1.0 - sum(probabilities.values())
    return probabilities


def open_camera(index: int, width: int, height: int):
    _require_opencv()
    if platform.system() == "Windows":
        capture = cv2.VideoCapture(index, cv2.CAP_DSHOW)
    else:
        capture = cv2.VideoCapture(index)
    capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    return capture


class CameraColourReader:
    """Continuously capture frames and return grouped eight-ROI colour readings."""

    def __init__(
        self,
        roi_file: Path,
        camera_index: int | None,
        events: queue.Queue,
        stop_event: threading.Event,
        width: int | None = None,
        height: int | None = None,
        config: dict | None = None,
    ):
        self.roi_file = Path(roi_file)
        self.config = config if config is not None else load_roi_config(self.roi_file)
        camera = self.config["camera"]
        self.camera_index = (
            int(camera.get("index", 0)) if camera_index is None else int(camera_index)
        )
        self.width = int(width or camera["frame_width"])
        self.height = int(height or camera["frame_height"])
        if self.width <= 0 or self.height <= 0:
            raise ValueError("Requested camera width and height must be positive.")
        self.events = events
        self.stop_event = stop_event
        self._capture = None
        self._thread: threading.Thread | None = None
        self._capture_stop = threading.Event()
        self._condition = threading.Condition()
        self._frames = deque(maxlen=30)
        self._capture_error: str | None = None
        self._regions: list[Region] = []

    def log(self, message: str) -> None:
        self.events.put(("log", message))

    def _check_stopped(self) -> None:
        if self.stop_event.is_set():
            raise ScanStopped("Scan stopped by the user.")

    def open(self) -> None:
        _require_opencv()
        if self._capture is not None:
            return
        self.log(
            f"Opening camera {self.camera_index} at requested "
            f"{self.width}x{self.height}..."
        )
        capture = open_camera(self.camera_index, self.width, self.height)
        try:
            if not capture.isOpened():
                raise ControllerError(
                    f"Could not open camera {self.camera_index}. Close other camera apps "
                    "or select another camera index."
                )
            ok, frame = capture.read()
            if not ok or frame is None:
                raise ControllerError(
                    f"Camera {self.camera_index} opened but returned no image."
                )
            frame_height, frame_width = frame.shape[:2]
            self._regions = regions_for_frame(self.config, frame_width, frame_height)
        except Exception:
            capture.release()
            raise
        self._capture = capture
        self._capture_error = None
        self._capture_stop.clear()
        with self._condition:
            self._frames.clear()
            self._frames.append((time.monotonic(), frame))
        self._thread = threading.Thread(
            target=self._capture_loop,
            name="rubiks-camera-capture",
            daemon=True,
        )
        self._thread.start()
        self.log(
            f"Camera {self.camera_index} ready at {frame_width}x{frame_height}; "
            f"loaded {self.roi_file}."
        )

    def _capture_loop(self) -> None:
        while not self._capture_stop.is_set():
            capture = self._capture
            if capture is None:
                break
            ok, frame = capture.read()
            captured_at = time.monotonic()
            if not ok or frame is None:
                with self._condition:
                    self._capture_error = "Camera frame capture failed."
                    self._condition.notify_all()
                break
            with self._condition:
                self._frames.append((captured_at, frame))
                self._condition.notify_all()

    def close(self) -> None:
        self._capture_stop.set()
        with self._condition:
            self._condition.notify_all()
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=2.0)
        capture = self._capture
        if capture is not None:
            capture.release()
        if thread is not None and thread.is_alive():
            thread.join(timeout=1.0)
        if capture is not None:
            self.log("Camera capture stopped and camera released.")
        self._thread = None
        self._capture = None

    def _collect_fresh_frames(
        self,
        after_time: float | None,
    ) -> list[tuple[float, object]]:
        threshold = (
            time.monotonic()
            if after_time is None
            else after_time + CAMERA_SETTLE_SECONDS
        )
        deadline = time.monotonic() + CAMERA_BURST_TIMEOUT_SECONDS
        fresh: list[tuple[float, object]] = []
        with self._condition:
            while True:
                self._check_stopped()
                fresh = [item for item in self._frames if item[0] > threshold]
                if len(fresh) >= CAMERA_BURST_FRAMES:
                    selected = fresh[-CAMERA_BURST_FRAMES:]
                    return [(timestamp, frame.copy()) for timestamp, frame in selected]
                if self._capture_error:
                    raise ControllerError(self._capture_error)
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                self._condition.wait(timeout=min(0.05, remaining))
        raise ControllerError(
            f"Camera supplied only {len(fresh)} fresh frames; at least "
            f"{CAMERA_BURST_FRAMES} are required."
        )

    def capture_burst(
        self,
        stage_id: int,
        mapping: tuple[str, ...],
        after_time: float | None,
    ) -> CameraBurst:
        if not 1 <= stage_id <= len(CAMERA_SCAN_MAPPINGS):
            raise ControllerError(f"Invalid camera scan stage: {stage_id}.")
        if len(mapping) != len(CAMERA_SLOTS):
            raise ControllerError("A camera burst requires eight logical mappings.")
        timestamped_frames = self._collect_fresh_frames(after_time)
        timestamps = tuple(timestamp for timestamp, _ in timestamped_frames)
        minimum_timestamp = (
            None if after_time is None else after_time + CAMERA_SETTLE_SECONDS
        )
        if minimum_timestamp is not None and any(
            timestamp <= minimum_timestamp for timestamp in timestamps
        ):
            raise ControllerError(
                f"Camera stage {stage_id} received a frame that was not newer than "
                "the preceding DONE response and settling interval."
            )
        self.log(
            f"Captured camera stage {stage_id}: {len(timestamped_frames)} fresh frames "
            f"({timestamps[0]:.6f} to {timestamps[-1]:.6f})."
        )
        return CameraBurst(
            stage_id=stage_id,
            mapping=tuple(mapping),
            frame_timestamps=timestamps,
            frames=tuple(frame for _, frame in timestamped_frames),
        )

    def classify_burst(self, burst: CameraBurst) -> CameraClassification:
        if len(burst.frames) != CAMERA_BURST_FRAMES:
            raise ControllerError(
                f"Camera stage {burst.stage_id} contains {len(burst.frames)} frames; "
                f"expected {CAMERA_BURST_FRAMES}."
            )
        readings: list[ColourReading] = []
        unknown: list[str] = []
        for region in self._regions:
            samples = [
                median_bgr_in_region(frame, region.points)
                for frame in burst.frames
            ]
            if any(sample is None for sample in samples):
                unknown.append(region.label)
                continue
            median_bgr = np.median(np.asarray(samples), axis=0)
            bgr = tuple(int(round(channel)) for channel in median_bgr)
            hsv = bgr_to_hsv(median_bgr)
            colour, confidence = classify_hsv(*hsv)
            if colour == "UNKNOWN":
                unknown.append(region.label)
                continue
            readings.append(
                ColourReading(
                    colour=colour,
                    probabilities=camera_probabilities(colour, confidence, hsv[0]),
                    source=f"camera stage {burst.stage_id} {region.label}",
                    bgr=bgr,
                    hsv=hsv,
                    camera_slot=region.label,
                    camera_stage=burst.stage_id,
                    classifier_confidence=confidence,
                )
            )
        if unknown:
            raise ControllerError(
                f"Camera classification failed at stage {burst.stage_id}; UNKNOWN slots: "
                + ", ".join(unknown)
            )
        if tuple(reading.camera_slot for reading in readings) != CAMERA_SLOTS:
            raise ControllerError(
                f"Camera stage {burst.stage_id} produced an incomplete or misordered result."
            )
        return CameraClassification(
            stage_id=burst.stage_id,
            mapping=burst.mapping,
            readings=tuple(readings),
        )


# Routine execution and confidence-guided repair
# ---------------------------------------------------------------------------

@dataclass
class ExecutionResult:
    cube_state: dict[str, str]
    sources: dict[str, str]
    observations: dict[str, list[ColourReading]]
    resolved_confidence: dict[str, FaceletConfidence]
    repair: "RepairResult"
    solve_plan: SolvePlan | None
    solve_error: str | None
    camera_snapshots: int
    reconstructed_facelets: str
    adjusted_current_facelets: str
    omitted_restoration_moves: tuple[str, ...]
    omitted_restoration_inverse: tuple[str, ...]


MAX_REPAIR_CHANGES = 4
MAX_REPAIR_ASSIGNMENTS = 50000


@dataclass(frozen=True)
class RepairChange:
    facelet: str
    from_colour: str
    to_colour: str


@dataclass
class RepairResult:
    attempted: bool = False
    selected: bool = False
    ambiguous: bool = False
    assignments_evaluated: int = 0
    limit_reached: bool = False
    changes: tuple[RepairChange, ...] = ()
    message: str = ""


class RoutineExecutor:
    def __init__(
        self,
        routine: Routine,
        controller: ControllerProtocol,
        camera_reader: CameraReaderProtocol,
        events: queue.Queue,
        stop_event: threading.Event,
        convert_moves: bool,
    ):
        self.routine = routine
        self.controller = controller
        self.camera_reader = camera_reader
        self.events = events
        self.stop_event = stop_event
        self.convert_moves = convert_moves
        self.state = dict(FIXED_CENTRES)
        self.sources = {facelet: "fixed centre" for facelet in FIXED_CENTRES}
        self.observations: dict[str, list[ColourReading]] = {}
        self.repair = RepairResult()
        self.repaired_facelets: set[str] = set()
        self.camera_snapshots = 0
        self.last_move_completed_at: float | None = None
        self.reconstructed_facelets = ""
        self.adjusted_current_facelets = ""
        self.omitted_restoration_inverse = invert_move_sequence(
            OMITTED_RESTORATION_MOVES
        )
        self._classification_pool: ThreadPoolExecutor | None = None
        self._pending_classifications: dict[
            int,
            tuple[tuple[str, ...], Future[CameraClassification]],
        ] = {}
        self._applied_camera_stages: set[int] = set()

    def log(self, message: str) -> None:
        self.events.put(("log", message))

    def _check_stopped(self) -> None:
        if self.stop_event.is_set():
            raise ScanStopped("Scan stopped by the user.")

    def _confidence_for(self, facelet: str) -> FaceletConfidence:
        if facelet in FIXED_CENTRES:
            colour = FIXED_CENTRES[facelet]
            probabilities = {candidate: float(candidate == colour) for candidate in COLOURS}
            second = next(candidate for candidate in COLOURS if candidate != colour)
            return FaceletConfidence(
                colour, 1.0, second, 0.0, 1.0, 0, 0, True, False, probabilities
            )
        return aggregate_colour_readings(self.observations[facelet])

    def _resolved_confidence(self) -> dict[str, FaceletConfidence]:
        return {
            facelet: self._confidence_for(facelet)
            for facelet in sorted(self.observations)
        }

    def _physical_state(self) -> dict[str, str]:
        state = dict(FIXED_CENTRES)
        state.update(
            {
                facelet: self._confidence_for(facelet).colour
                for facelet in self.observations
            }
        )
        return state

    def _publish_state(self) -> None:
        self.events.put(
            (
                "state",
                dict(self.state),
                dict(self.sources),
                self._resolved_confidence(),
                set(self.repaired_facelets),
            )
        )

    def _rebuild_working_state(self) -> None:
        self.state = self._physical_state()
        self.sources = {facelet: "fixed centre" for facelet in FIXED_CENTRES}
        for facelet, readings in self.observations.items():
            self.sources[facelet] = readings[-1].source
        self._publish_state()

    def _record_colour(
        self,
        facelet: str,
        reading: ColourReading,
        *,
        publish: bool = True,
    ) -> None:
        if facelet not in OUTER_FACELETS:
            raise ControllerError(f"A camera reading cannot target {facelet!r}.")
        if not isinstance(reading, ColourReading):
            raise ControllerError(f"Malformed colour reading for {facelet}.")
        previous = self._confidence_for(facelet) if facelet in self.observations else None
        self.observations.setdefault(facelet, []).append(reading)
        resolved = self._confidence_for(facelet)
        if previous is None:
            self.log(
                f"Recorded {facelet} from {reading.camera_slot or reading.source}: "
                f"{reading.colour} ({reading.probabilities[reading.colour]:.2f}); "
                f"aggregate {resolved.colour} ({resolved.probability:.2f})."
            )
        elif reading.colour == previous.colour:
            self.log(
                f"Supporting observation at {facelet}: {reading.colour}; "
                f"aggregate {resolved.colour} ({resolved.probability:.2f})."
            )
        else:
            self.log(
                f"Conflict at {facelet}: previous {previous.colour}, new "
                f"{reading.colour}; aggregate {resolved.colour} "
                f"({resolved.probability:.2f})."
            )
        if publish:
            self._rebuild_working_state()

    def _queue_camera_scan(self, action: Action) -> None:
        if self._classification_pool is None:
            raise ControllerError("Camera classification worker is not running.")
        stage_id = self.camera_snapshots + 1
        if stage_id in self._pending_classifications:
            raise ControllerError(f"Camera stage {stage_id} was queued more than once.")
        burst = self.camera_reader.capture_burst(
            stage_id,
            action.mapping,
            self.last_move_completed_at,
        )
        if burst.stage_id != stage_id or burst.mapping != action.mapping:
            raise ControllerError(
                f"Camera burst association mismatch at stage {stage_id}."
            )
        future = self._classification_pool.submit(
            self.camera_reader.classify_burst,
            burst,
        )
        self._pending_classifications[stage_id] = (action.mapping, future)
        self.camera_snapshots += 1
        self.events.put(
            (
                "progress",
                len([facelet for facelet in OUTER_FACELETS if facelet in self.state]),
                self.camera_snapshots,
            )
        )

    def _apply_camera_classification(
        self,
        expected_stage: int,
        expected_mapping: tuple[str, ...],
        result: CameraClassification,
    ) -> None:
        if expected_stage in self._applied_camera_stages:
            raise ControllerError(f"Camera stage {expected_stage} was applied twice.")
        if result.stage_id != expected_stage or result.mapping != expected_mapping:
            raise ControllerError(
                f"Camera classification association mismatch: expected stage "
                f"{expected_stage}, received stage {result.stage_id}."
            )
        if len(result.readings) != len(CAMERA_SLOTS):
            raise ControllerError(
                f"Camera stage {expected_stage} returned {len(result.readings)} "
                f"readings; expected {len(CAMERA_SLOTS)}."
            )
        for expected_slot, logical_facelet, reading in zip(
            CAMERA_SLOTS,
            expected_mapping,
            result.readings,
        ):
            if reading.camera_slot != expected_slot:
                raise ControllerError(
                    f"Camera stage {expected_stage} order mismatch: expected "
                    f"{expected_slot}, received {reading.camera_slot!r}."
                )
            if reading.camera_stage != expected_stage:
                raise ControllerError(
                    f"Camera reading stage mismatch: expected {expected_stage}, "
                    f"received {reading.camera_stage!r}."
                )
            self._record_colour(logical_facelet, reading, publish=False)
        self._applied_camera_stages.add(expected_stage)
        self._rebuild_working_state()
        self.log(f"Applied camera classification for stage {expected_stage}.")
        self.events.put(
            (
                "progress",
                len([facelet for facelet in OUTER_FACELETS if facelet in self.state]),
                self.camera_snapshots,
            )
        )

    def _collect_camera_classifications(self, *, wait: bool) -> None:
        for stage_id in sorted(tuple(self._pending_classifications)):
            mapping, future = self._pending_classifications[stage_id]
            if not wait and not future.done():
                continue
            try:
                result = future.result()
            except Exception as exc:
                raise ControllerError(
                    f"Camera classification failed for stage {stage_id}: {exc}"
                ) from exc
            self._apply_camera_classification(stage_id, mapping, result)
            del self._pending_classifications[stage_id]

    def _complete_candidate(self, candidate: dict[str, str]) -> dict[str, str]:
        completed = dict(candidate)
        validate_complete_cube_colours(completed)
        validate_corner_inventory(completed)
        return completed

    def _candidate_sources(self, state: dict[str, str]) -> dict[str, str]:
        del state
        sources = {facelet: "fixed centre" for facelet in FIXED_CENTRES}
        for facelet, readings in self.observations.items():
            sources[facelet] = readings[-1].source
        return sources

    def _solve_adjusted_current_state(
        self,
        reconstructed_state: dict[str, str],
    ) -> tuple[SolvePlan | None, str | None]:
        try:
            (
                adjusted_state,
                self.reconstructed_facelets,
                inverse_moves,
                self.adjusted_current_facelets,
            ) = adjusted_state_for_omitted_restoration(reconstructed_state)
            if inverse_moves != self.omitted_restoration_inverse:
                raise SolverError("Omitted-restoration inverse changed unexpectedly.")
            validate_corner_inventory(adjusted_state)
            self.log(
                "Original reconstructed facelets: " + self.reconstructed_facelets
            )
            self.log(
                "Omitted physical restoration: "
                + " ".join(OMITTED_RESTORATION_MOVES)
            )
            self.log(
                "Calculated restoration inverse: "
                + " ".join(self.omitted_restoration_inverse)
            )
            self.log(
                "Adjusted current facelets: " + self.adjusted_current_facelets
            )
            plan = solve_final_cube_state_without_u(adjusted_state)
            self.log("Final Kociemba solution: " + plan.standard_text)
            return plan, None
        except (CubeValidationError, SolverError, FiveFaceSolverError) as exc:
            self.log(f"ADJUSTED-STATE SOLVER ERROR: {exc}")
            return None, str(exc)

    def _repair_options(
        self,
    ) -> list[tuple[str, FaceletConfidence, tuple[tuple[str, float], ...]]]:
        eligible: list[tuple[str, FaceletConfidence]] = []
        for facelet in sorted(self.observations):
            if facelet in FIXED_CENTRES:
                continue
            confidence = self._confidence_for(facelet)
            if (
                not confidence.confirmed
                or confidence.conflicted
                or confidence.probability < 0.92
            ):
                eligible.append((facelet, confidence))
        eligible.sort(
            key=lambda item: (
                item[1].margin,
                item[1].probability,
                item[1].agreeing_observations,
                item[0],
            )
        )
        options: list[tuple[str, FaceletConfidence, tuple[tuple[str, float], ...]]] = []
        for facelet, confidence in eligible:
            allowed = {confidence.colour, confidence.second_colour}
            if {confidence.colour, confidence.second_colour} & {"RED", "ORANGE"}:
                allowed.update(("RED", "ORANGE"))
            alternatives = []
            for colour in sorted(allowed):
                if colour == confidence.colour:
                    continue
                probability = confidence.probabilities[colour]
                penalty = math.log(
                    max(confidence.probability, 1e-9) / max(probability, 1e-9)
                ) + 0.75
                alternatives.append((colour, penalty))
            if alternatives:
                options.append((facelet, confidence, tuple(alternatives)))
        return options

    def _repair_candidates(
        self,
        options: list[tuple[str, FaceletConfidence, tuple[tuple[str, float], ...]]],
    ):
        """Yield bounded-change assignments in nondecreasing exact repair cost."""
        heap: list[tuple[float, tuple[tuple[int, str], ...]]] = []
        for index, (_, _, alternatives) in enumerate(options):
            for colour, penalty in alternatives:
                heapq.heappush(heap, (penalty, ((index, colour),)))
        while heap:
            cost, changes = heapq.heappop(heap)
            yield cost, changes
            if len(changes) >= MAX_REPAIR_CHANGES:
                continue
            last_index = changes[-1][0]
            for index in range(last_index + 1, len(options)):
                for colour, penalty in options[index][2]:
                    heapq.heappush(heap, (cost + penalty, changes + ((index, colour),)))

    def _run_repair(self, initial_error: Exception) -> tuple[SolvePlan | None, str | None]:
        self.repair = RepairResult(attempted=True, message=str(initial_error))
        options = self._repair_options()
        if not options:
            self.repair.message = "No uncertain physical facelets were eligible for repair."
            return None, self.repair.message
        aggregate_state = self._physical_state()
        legal: list[tuple[float, dict[str, str], tuple[RepairChange, ...]]] = []
        candidate_iter = self._repair_candidates(options)
        while self.repair.assignments_evaluated < MAX_REPAIR_ASSIGNMENTS:
            try:
                cost, changes = next(candidate_iter)
            except StopIteration:
                break
            self.repair.assignments_evaluated += 1
            candidate = dict(aggregate_state)
            repair_changes: list[RepairChange] = []
            for option_index, colour in changes:
                facelet, confidence, _ = options[option_index]
                candidate[facelet] = colour
                repair_changes.append(RepairChange(facelet, confidence.colour, colour))
            counts = Counter(candidate.values())
            if any(counts[colour] > 9 for colour in COLOURS):
                continue
            try:
                completed = self._complete_candidate(candidate)
                validate_cube_state_legality(completed)
            except (CubeValidationError, SolverError):
                continue
            legal.append((cost, completed, tuple(repair_changes)))
        else:
            self.repair.limit_reached = True

        legal.sort(key=lambda item: (item[0], tuple(change.facelet for change in item[2])))
        if self.repair.limit_reached:
            self.repair.ambiguous = bool(legal)
            self.repair.message = (
                f"Repair stopped at the {MAX_REPAIR_ASSIGNMENTS:,}-assignment limit; "
                "a unique trusted repair was not established."
            )
            return None, self.repair.message
        if not legal:
            self.repair.message = "No legal confidence-guided repair was found."
            return None, self.repair.message
        if len(legal) > 1 and legal[1][0] - legal[0][0] < 1.5:
            self.repair.ambiguous = True
            self.repair.message = "Multiple similarly scored legal repairs were found."
            return None, self.repair.message
        best_cost, completed, changes = legal[0]
        self.repair.selected = True
        self.repair.changes = changes
        self.repair.message = f"Selected legal repair with cost {best_cost:.3f}."
        self.state = completed
        self.sources = self._candidate_sources(completed)
        self.repaired_facelets = {change.facelet for change in changes}
        for change in changes:
            self.sources[change.facelet] = "automatic repair"
            confidence = self._confidence_for(change.facelet)
            self.log(
                "AUTOMATIC REPAIR: "
                f"{change.facelet}: {change.from_colour} -> {change.to_colour}; "
                f"aggregate probabilities: {change.from_colour} "
                f"{confidence.probabilities[change.from_colour]:.2f}, "
                f"{change.to_colour} {confidence.probabilities[change.to_colour]:.2f}; "
                "reason: lower-cost legal cube candidate accepted by Kociemba."
            )
        self._publish_state()
        self.log(
            "Reconstructed cube state is legal. Adjusting for the omitted "
            "restoration before solving..."
        )
        return self._solve_adjusted_current_state(completed)

    def _finalise_state(self) -> tuple[SolvePlan | None, str | None]:
        aggregate_state = self._physical_state()
        try:
            completed = self._complete_candidate(aggregate_state)
            validate_cube_state_legality(completed)
        except (CubeValidationError, SolverError) as exc:
            self.log(f"Aggregate-winning state was not legal: {exc}. Trying bounded repair.")
            return self._run_repair(exc)
        self.state = completed
        self.sources = self._candidate_sources(completed)
        self._publish_state()
        self.log(
            "Reconstructed cube state is legal. Adjusting for the omitted "
            "restoration before solving..."
        )
        return self._solve_adjusted_current_state(completed)

    def run(self) -> ExecutionResult:
        classification_pool: ThreadPoolExecutor | None = None
        try:
            self.controller.open()
            self.camera_reader.open()
            classification_pool = ThreadPoolExecutor(
                max_workers=1,
                thread_name_prefix="rubiks-camera-classifier",
            )
            self._classification_pool = classification_pool
            for index, action in enumerate(self.routine.actions, start=1):
                self._check_stopped()
                self.events.put(
                    (
                        "action",
                        index,
                        len(self.routine.actions),
                        action.type,
                        action.value or f"snapshot {self.camera_snapshots + 1}",
                    )
                )
                if action.type == "move":
                    command = (
                        convert_move_for_controller(action.value)
                        if self.convert_moves
                        else action.value
                    )
                    if command != action.value:
                        self.log(f"Move conversion: {action.value} -> {command}")
                    self.controller.move(command)
                    self.last_move_completed_at = time.monotonic()
                    self._collect_camera_classifications(wait=False)
                elif action.type == "camera_scan":
                    self._queue_camera_scan(action)
                else:
                    raise ControllerError(f"Unsupported routine action: {action.type}")

            self.log("All scan movements are complete; waiting for camera classifications.")
            self._collect_camera_classifications(wait=True)
            self._check_stopped()
            if self._pending_classifications:
                raise ControllerError("Pending camera classifications remain before solving.")
            if self._applied_camera_stages != set(range(1, 7)):
                raise ControllerError(
                    "Not all six camera stages were classified before reconstruction."
                )
            missing = sorted(set(OUTER_FACELETS) - set(self.observations))
            if missing:
                raise ControllerError(
                    "Camera routine ended without physical readings for: "
                    + ", ".join(missing)
                )
            if len(self.observations) != len(OUTER_FACELETS):
                raise ControllerError("Camera routine recorded unexpected facelet evidence.")
            self._rebuild_working_state()
            plan, solve_error = self._finalise_state()
            return ExecutionResult(
                cube_state=dict(self.state),
                sources=dict(self.sources),
                observations={
                    facelet: list(readings)
                    for facelet, readings in self.observations.items()
                },
                resolved_confidence=self._resolved_confidence(),
                repair=self.repair,
                solve_plan=plan,
                solve_error=solve_error,
                camera_snapshots=self.camera_snapshots,
                reconstructed_facelets=self.reconstructed_facelets,
                adjusted_current_facelets=self.adjusted_current_facelets,
                omitted_restoration_moves=OMITTED_RESTORATION_MOVES,
                omitted_restoration_inverse=self.omitted_restoration_inverse,
            )
        finally:
            try:
                if classification_pool is not None:
                    classification_pool.shutdown(wait=True, cancel_futures=False)
                self._classification_pool = None
            finally:
                try:
                    self.camera_reader.close()
                finally:
                    self.controller.close()

@dataclass(frozen=True)
class AutomaticWorkflowResult:
    scan_result: ExecutionResult
    solution_commands_completed: int
    execution_started: bool


def execute_robot_moves(
    controller: ControllerProtocol,
    moves: tuple[str, ...],
    events: queue.Queue,
    stop_event: threading.Event,
    convert_moves: bool,
    *,
    operation_name: str,
    action_name: str,
) -> int:
    """Execute one guarded logical move sequence and report completed commands."""
    if not moves:
        return 0
    if stop_event.is_set():
        raise ScanStopped(
            f"{operation_name.capitalize()} stopped by the user before any command."
        )

    completed = 0
    controller.open()
    try:
        total = len(moves)
        for index, logical_move in enumerate(moves, start=1):
            if stop_event.is_set():
                raise ScanStopped(
                    f"{operation_name.capitalize()} stopped by the user after "
                    f"{completed} completed commands."
                )
            events.put(("action", index, total, action_name, logical_move))
            command = (
                convert_move_for_controller(logical_move)
                if convert_moves
                else logical_move
            )
            if command != logical_move:
                events.put(
                    (
                        "log",
                        f"{operation_name.capitalize()} move conversion: "
                        f"{logical_move} -> {command}",
                    )
                )
            try:
                controller.move(command)
            except ScanStopped:
                raise
            except Exception as exc:
                raise ControllerError(
                    f"{operation_name.capitalize()} failed at move {index}/{total} "
                    f"({logical_move}); {completed} commands completed. Details: {exc}"
                ) from exc
            completed += 1
    finally:
        controller.close()
    return completed


def execute_solve_plan(
    controller: ControllerProtocol,
    plan: SolvePlan,
    events: queue.Queue,
    stop_event: threading.Event,
    convert_moves: bool,
) -> int:
    """Send the already-verified five-face physical solution to the ESP32."""
    if not plan.executable_moves:
        events.put(("log", "Cube is already solved; no motor moves are required."))
        return 0
    return execute_robot_moves(
        controller,
        plan.executable_moves,
        events,
        stop_event,
        convert_moves,
        operation_name="solution execution",
        action_name="solve move",
    )


def run_scan_and_execute(
    scan_executor,
    solution_controller: ControllerProtocol,
    events: queue.Queue,
    stop_event: threading.Event,
    convert_moves: bool,
) -> AutomaticWorkflowResult:
    """Run the trusted scan pipeline and immediately execute its final plan."""
    result: ExecutionResult = scan_executor.run()
    events.put(("automatic_scan_ready", result))
    plan = result.solve_plan
    if plan is None:
        events.put(
            (
                "log",
                "Automatic execution cancelled: the scan pipeline did not produce "
                "a trusted solution.",
            )
        )
        return AutomaticWorkflowResult(result, 0, False)

    if result.repair.selected:
        events.put(
            (
                "log",
                "Automatic execution will use the trusted repaired cube state "
                f"({len(result.repair.changes)} changed facelets).",
            )
        )
        for change in result.repair.changes:
            events.put(
                (
                    "log",
                    f"Automatic repair used: {change.facelet} "
                    f"{change.from_colour} -> {change.to_colour}.",
                )
            )
    else:
        events.put(("log", "Automatic execution will use the validated scan state."))

    events.put(
        (
            "automatic_execution_started",
            len(plan.executable_moves),
            result.repair.selected,
        )
    )
    completed = execute_solve_plan(
        solution_controller,
        plan,
        events,
        stop_event,
        convert_moves,
    )
    return AutomaticWorkflowResult(result, completed, True)


# ---------------------------------------------------------------------------
# Tkinter GUI
# ---------------------------------------------------------------------------

class CubeSolverApp(tk.Tk):
    """One-button scan and solve; all feedback goes to the terminal."""

    def __init__(self, roi_file=DEFAULT_ROI_FILE, camera_index=None,
                 width=None, height=None, port="COM7", convert_moves=True):
        super().__init__()
        self.title("Cube Solver")
        self.geometry("240x120")
        self.events = queue.Queue()
        self.stop_event = threading.Event()
        self.worker_thread = None
        self.closing = False
        self.roi_file = Path(roi_file)
        self.camera_index = camera_index
        self.width, self.height = width, height
        self.port, self.convert_moves = port, convert_moves
        self.solve_button = tk.Button(self, text="Solve", command=self._solve)
        self.solve_button.pack(expand=True, ipadx=35, ipady=15)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(50, self._process_events)
        print(f"Ready. ESP32: {port}; camera calibration: {self.roi_file}", flush=True)
        print("Place the cube in its starting orientation, then click Solve.", flush=True)

    def _solve(self):
        if self.worker_thread is not None or self.closing:
            return
        self.stop_event.clear()
        self.solve_button.configure(state="disabled")
        self.worker_thread = threading.Thread(target=self._run, daemon=False)
        self.worker_thread.start()

    def _run(self):
        controller = None
        camera = None
        try:
            config = load_roi_config(self.roi_file)
            _require_opencv()
            camera_index = self.camera_index
            if camera_index is None:
                camera_index = int(config.get("camera", {}).get("index", 0))
            controller = ESP32Controller(self.port, self.events, self.stop_event)
            camera = CameraColourReader(
                self.roi_file, camera_index, self.events, self.stop_event,
                self.width, self.height, config,
            )
            executor = RoutineExecutor(
                Routine.embedded(), controller, camera, self.events,
                self.stop_event, self.convert_moves,
            )
            self.events.put(("log", "Scanning, validating and solving..."))
            outcome = run_scan_and_execute(
                executor, controller, self.events, self.stop_event, self.convert_moves,
            )
            if outcome.execution_started:
                self.events.put(("log", f"Complete: {outcome.solution_commands_completed} "
                                 "solution commands executed. The cube should be solved."))
            else:
                self.events.put(("log", "ERROR: No trusted solution; execution cancelled. "
                                 + (outcome.scan_result.solve_error or "Scan needs review.")))
        except ScanStopped as exc:
            self.events.put(("log", f"STOPPED: {exc}"))
        except Exception as exc:
            self.events.put(("log", f"ERROR: {exc}"))
        finally:
            for resource in (camera, controller):
                if resource is not None:
                    try:
                        resource.close()
                    except Exception as exc:
                        self.events.put(("log", f"ERROR closing device: {exc}"))

    def _process_events(self):
        while not self.events.empty():
            event = self.events.get_nowait()
            kind = event[0]
            if kind == "log":
                print(event[1], flush=True)
            elif kind == "action":
                print(f"Action {event[1]}/{event[2]}: {event[3]} {event[4]}", flush=True)
            elif kind == "progress":
                print(f"Scan: {event[1]}/48 facelets, {event[2]}/6 snapshots", flush=True)
            elif kind == "automatic_scan_ready":
                result = event[1]
                if result.solve_plan is not None:
                    print("Standard solution:", result.solve_plan.standard_text, flush=True)
                    print("Robot solution:", result.solve_plan.executable_text, flush=True)
                else:
                    print("ERROR:", result.solve_error, flush=True)
        if self.worker_thread is not None and not self.worker_thread.is_alive():
            self.worker_thread = None
            self.solve_button.configure(state="normal")
        if self.closing and self.worker_thread is None:
            self.destroy()
            return
        self.after(50, self._process_events)

    def _on_close(self):
        self.closing = True
        self.solve_button.configure(state="disabled")
        self.stop_event.set()
        print("Closing; waiting for the active operation to stop and release devices.", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the Rubik's Cube camera scanner and solver GUI"
    )
    parser.add_argument(
        "--roi-file",
        type=Path,
        default=DEFAULT_ROI_FILE,
        help="Top-face ROI calibration JSON (default: beside this script)",
    )
    parser.add_argument("--camera", type=int, default=None, help="Override camera index")
    parser.add_argument("--width", type=int, default=None, help="Override requested width")
    parser.add_argument("--height", type=int, default=None, help="Override requested height")
    parser.add_argument("--port", default="COM7", help="ESP32 serial port (default: COM7)")
    parser.add_argument("--no-convert-moves", action="store_true",
                        help="Disable the existing motor-direction conversion")
    args = parser.parse_args()
    app = CubeSolverApp(
        roi_file=args.roi_file,
        camera_index=args.camera,
        width=args.width,
        height=args.height,
        port=args.port,
        convert_moves=not args.no_convert_moves,
    )
    app.mainloop()

if __name__ == "__main__":
    main()
