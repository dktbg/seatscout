"""Scoring tests — pure logic, no network."""

from seatscout.models import Seat
from seatscout.scoring import best_block


def row(row_idx, n, taken=(), start_col=1, kind="CanReserve"):
    """Build a straight row of n seats named R1..Rn, some marked taken."""
    letter = chr(ord("A") + row_idx - 1)
    seats = []
    for i in range(n):
        col = start_col + i
        name = f"{letter}{i + 1}"
        avail = (i + 1) not in taken
        seats.append(
            Seat(
                col=col,
                row=row_idx,
                name=name,
                type=kind,
                tier="Regular",
                avail=avail,
                display=True,
            )
        )
    return seats


def test_prefers_center_over_edge():
    seats = row(5, 11)  # all open, columns 1..11, center = seat 6
    block = best_block(seats, 2)
    assert block is not None
    # best-centered pair straddles the middle
    assert set(block.seats) & {"E6", "E5", "E7"}


def test_requires_contiguity_across_taken_seats():
    # Only seats 1,2 and 10,11 open; a pair must be adjacent within one gap-free run
    seats = row(5, 11, taken=(3, 4, 5, 6, 7, 8, 9))
    block = best_block(seats, 2)
    assert block is not None
    assert block.seats in (("E1", "E2"), ("E10", "E11"))


def test_aisle_gap_breaks_runs():
    # Columns 1-3 and 5-7 with column 4 missing (an aisle): no block may span it
    seats = [s for s in row(5, 7) if s.col != 4]
    block = best_block(seats, 2)
    assert block.seats in (("E2", "E3"), ("E5", "E6"))
    # 6 seats are open, but no contiguous run holds 4
    assert best_block(seats, 4) is None


def test_single_row_map_has_no_vertical_penalty():
    seats = row(1, 11)  # one row, dead-center seat available
    block = best_block(seats, 1)
    assert block.score == 100.0


def test_no_block_when_party_too_big():
    seats = row(5, 11, taken=tuple(range(3, 12)))  # only 1,2 open
    assert best_block(seats, 3) is None


def test_excludes_non_reservable_types():
    seats = row(1, 5, kind="Wheelchair")
    assert best_block(seats, 2) is None


def test_deeper_row_beats_front_row_when_both_centered():
    front = row(1, 11)  # row A, front
    back = row(8, 11)  # row H, ~62% back in a 1-8 house
    block = best_block(front + back, 2)
    assert block.row == 8
