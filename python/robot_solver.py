#!/usr/bin/env python3
"""Adapt the five-face solver to a robot without a physical U-face motor.

Cube coordinates are rotated so virtual B corresponds to physical U. Returned
moves are mapped back and verified against the physical cube before execution.
"""

from __future__ import annotations

import importlib
import os
from pathlib import Path
import re
import sys
from typing import Iterable, Sequence


FACE_ORDER = "URFDLB"
SOLVED_FACELETS = "".join(face * 9 for face in FACE_ORDER)
VALID_MOVE = re.compile(r"^([URFDLB])(?:([123])|(')|)$")

# A +90-degree rotation about the physical/virtual R-L axis.  This is a
# coordinate change only; the robot does not physically rotate the cube.
#
# Virtual solver face -> physical robot face
VIRTUAL_TO_PHYSICAL_FACE = {
    "U": "F",
    "R": "R",
    "F": "D",
    "D": "B",
    "L": "L",
    "B": "U",  # The solver forbids B, so the robot receives no U moves.
}
PHYSICAL_TO_VIRTUAL_FACE = {
    physical: virtual for virtual, physical in VIRTUAL_TO_PHYSICAL_FACE.items()
}

Vector = tuple[int, int, int]
StickerSlot = tuple[Vector, Vector]  # (cubie position, sticker normal)


# Facelet rows are listed as viewed directly at that face.  These bases match
# Kociemba's conventional U1..U9, R1..R9, ..., B1..B9 ordering.
FACE_NORMAL: dict[str, Vector] = {
    "U": (0, 1, 0),
    "R": (1, 0, 0),
    "F": (0, 0, 1),
    "D": (0, -1, 0),
    "L": (-1, 0, 0),
    "B": (0, 0, -1),
}
FACE_RIGHT: dict[str, Vector] = {
    "U": (1, 0, 0),
    "R": (0, 0, -1),
    "F": (1, 0, 0),
    "D": (1, 0, 0),
    "L": (0, 0, 1),
    "B": (-1, 0, 0),
}
FACE_UP: dict[str, Vector] = {
    "U": (0, 0, -1),
    "R": (0, 1, 0),
    "F": (0, 1, 0),
    "D": (0, 0, 1),
    "L": (0, 1, 0),
    "B": (0, 1, 0),
}


class FiveFaceSolverError(RuntimeError):
    """Raised when rotation, solver loading, solving, or verification fails."""


def _add(*vectors: Vector) -> Vector:
    return tuple(sum(vector[i] for vector in vectors) for i in range(3))  # type: ignore[return-value]


def _scale(amount: int, vector: Vector) -> Vector:
    return tuple(amount * component for component in vector)  # type: ignore[return-value]


def _dot(first: Vector, second: Vector) -> int:
    return sum(a * b for a, b in zip(first, second))


def _cross(first: Vector, second: Vector) -> Vector:
    ax, ay, az = first
    bx, by, bz = second
    return (ay * bz - az * by, az * bx - ax * bz, ax * by - ay * bx)


def _clockwise_quarter_turn(vector: Vector, outward_axis: Vector) -> Vector:
    """Rotate a vector -90 degrees about an outward face normal."""
    parallel = _scale(_dot(outward_axis, vector), outward_axis)
    return _add(parallel, _scale(-1, _cross(outward_axis, vector)))


def _slot_for(face: str, position: int) -> StickerSlot:
    if face not in FACE_ORDER or not 1 <= position <= 9:
        raise ValueError(f"Invalid facelet: {face}{position}")
    row, column = divmod(position - 1, 3)
    horizontal = column - 1
    vertical = 1 - row
    cubie_position = _add(
        FACE_NORMAL[face],
        _scale(horizontal, FACE_RIGHT[face]),
        _scale(vertical, FACE_UP[face]),
    )
    return cubie_position, FACE_NORMAL[face]


FACELET_SLOTS: tuple[StickerSlot, ...] = tuple(
    _slot_for(face, position)
    for face in FACE_ORDER
    for position in range(1, 10)
)


def _validate_facelets(facelets: str) -> None:
    if len(facelets) != 54:
        raise FiveFaceSolverError(
            f"Expected 54 URFDLB facelets, received {len(facelets)}."
        )
    invalid = sorted(set(facelets) - set(FACE_ORDER))
    if invalid:
        raise FiveFaceSolverError(f"Unsupported facelet letters: {invalid}")
    counts = {face: facelets.count(face) for face in FACE_ORDER}
    if any(count != 9 for count in counts.values()):
        raise FiveFaceSolverError(
            "Each face letter must occur exactly nine times; received "
            + ", ".join(f"{face}={counts[face]}" for face in FACE_ORDER)
        )


def _facelets_to_stickers(facelets: str) -> dict[StickerSlot, str]:
    _validate_facelets(facelets)
    return dict(zip(FACELET_SLOTS, facelets))


def _stickers_to_facelets(stickers: dict[StickerSlot, str]) -> str:
    try:
        result = "".join(stickers[slot] for slot in FACELET_SLOTS)
    except KeyError as exc:
        raise FiveFaceSolverError("Internal facelet geometry is incomplete.") from exc
    _validate_facelets(result)
    return result


def _normalise_move(token: str) -> tuple[str, int]:
    token = token.strip().replace("’", "'")
    match = VALID_MOVE.fullmatch(token)
    if not match:
        raise FiveFaceSolverError(f"Unsupported move token: {token!r}")
    face, numeric_suffix, prime_suffix = match.groups()
    if numeric_suffix:
        turns = int(numeric_suffix)
    elif prime_suffix:
        turns = 3
    else:
        turns = 1
    return face, turns


def _format_move(face: str, turns: int) -> str:
    suffix = {1: "", 2: "2", 3: "'"}[turns]
    return face + suffix


def parse_moves(text: str) -> tuple[str, ...]:
    """Accept standard moves (R/R2/R') or numeric moves (R1/R2/R3)."""
    if not text.strip():
        return ()
    return tuple(_format_move(*_normalise_move(token)) for token in text.split())


def apply_moves(facelets: str, moves: Iterable[str]) -> str:
    """Apply standard or numeric moves to a URFDLB facelet string."""
    stickers = _facelets_to_stickers(facelets)
    for token in moves:
        face, turns = _normalise_move(token)
        axis = FACE_NORMAL[face]
        for _ in range(turns):
            updated: dict[StickerSlot, str] = {}
            for (position, normal), label in stickers.items():
                if _dot(position, axis) == 1:
                    destination = (
                        _clockwise_quarter_turn(position, axis),
                        _clockwise_quarter_turn(normal, axis),
                    )
                else:
                    destination = (position, normal)
                updated[destination] = label
            stickers = updated
    return _stickers_to_facelets(stickers)


def _virtual_vector_to_physical(vector: Vector) -> Vector:
    """Apply +90 degrees about R: (x, y, z) -> (x, -z, y)."""
    x, y, z = vector
    return x, -z, y


def rotate_physical_facelets_to_solver(physical_facelets: str) -> str:
    """Return a virtual URFDLB state where solver B is physical U."""
    physical = _facelets_to_stickers(physical_facelets)
    virtual: dict[StickerSlot, str] = {}

    for virtual_slot in FACELET_SLOTS:
        virtual_position, virtual_normal = virtual_slot
        physical_slot = (
            _virtual_vector_to_physical(virtual_position),
            _virtual_vector_to_physical(virtual_normal),
        )
        physical_label = physical[physical_slot]
        virtual[virtual_slot] = PHYSICAL_TO_VIRTUAL_FACE[physical_label]

    return _stickers_to_facelets(virtual)


def map_solver_moves_to_physical(solver_moves: Sequence[str]) -> tuple[str, ...]:
    """Map virtual moves back to standard physical moves without physical U."""
    physical_moves: list[str] = []
    for token in solver_moves:
        virtual_face, turns = _normalise_move(token)
        physical_face = VIRTUAL_TO_PHYSICAL_FACE[virtual_face]
        physical_moves.append(_format_move(physical_face, turns))

    if any(move.startswith("U") for move in physical_moves):
        raise FiveFaceSolverError(
            "The five-face solver returned virtual B, producing a forbidden physical U move."
        )
    return tuple(physical_moves)


def _load_solver(solver_directory: str | Path):
    directory = Path(solver_directory).expanduser().resolve()
    if not (directory / "solver.py").is_file():
        raise FiveFaceSolverError(
            f"Could not find solver.py in {directory}. Pass solver_directory if the "
            "five_face_solver folder is somewhere else."
        )

    # This repository stores and opens its generated tables relative to the
    # current working directory, so import it while inside its own directory.
    old_directory = Path.cwd()
    sys.path.insert(0, str(directory))
    try:
        os.chdir(directory)
        return importlib.import_module("solver")
    except Exception as exc:
        raise FiveFaceSolverError(
            "The five-face solver could not be imported. Confirm that all table "
            f"files remain in {directory}. Details: {exc}"
        ) from exc
    finally:
        os.chdir(old_directory)
        if sys.path and sys.path[0] == str(directory):
            sys.path.pop(0)


def _parse_solver_result(raw_result: object) -> tuple[str, ...]:
    text = str(raw_result).strip()
    if not text:
        return ()
    if text.lower().startswith("error"):
        raise FiveFaceSolverError(f"The five-face solver rejected the cube: {text}")

    # Some Kociemba variants append a move-count marker such as "(20f)".
    text = re.sub(r"\s*\(\d+f\)\s*$", "", text)
    return parse_moves(text)


def solve_physical_facelets_without_u(
    physical_facelets: str,
    solver_directory: str | Path | None = None,
    max_depth: int = 22,
    timeout_seconds: int = 3,
) -> tuple[str, ...]:
    """Solve physical URFDLB facelets and return standard moves containing no U."""
    _validate_facelets(physical_facelets)
    if physical_facelets == SOLVED_FACELETS:
        return ()

    directory = (
        Path(solver_directory)
        if solver_directory is not None
        else Path(__file__).resolve().parent / "five_face_solver"
    )
    solver_facelets = rotate_physical_facelets_to_solver(physical_facelets)
    five_face_solver = _load_solver(directory)

    try:
        raw_solution = five_face_solver.solve(
            solver_facelets, max_depth, timeout_seconds
        )
    except Exception as exc:
        raise FiveFaceSolverError(f"Five-face search failed: {exc}") from exc

    virtual_moves = _parse_solver_result(raw_solution)
    physical_moves = map_solver_moves_to_physical(virtual_moves)

    verified = apply_moves(physical_facelets, physical_moves)
    if verified != SOLVED_FACELETS:
        raise FiveFaceSolverError(
            "The mapped solution did not solve the original physical cube; it "
            "has been rejected and must not be sent to the robot."
        )
    return physical_moves
