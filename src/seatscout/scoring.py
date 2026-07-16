"""
Seat-quality scoring: given a seat map and a party size, find the best
contiguous block of that many seats and score how "center" it is (0-100).

The score combines two penalties, each 0 (perfect) to 1 (worst):
  - horizontal: distance of the block's center from the row's midpoint
  - vertical:   distance of the row from the ideal depth in the auditorium

Weighting favors horizontal centering (people care most about not being off
to the side), with a lighter preference for sitting a bit behind mid-depth.
"""

from __future__ import annotations

from typing import List, Optional

from .models import Seat, SeatBlock

# Rows are assumed numbered from the screen (lowest row = front). AMC does
# this; verify the convention when adding a provider.
IDEAL_ROW_FRAC = 0.62  # 0 = front row, 1 = back row; ~62% back reads best
W_HORIZONTAL = 0.6
W_VERTICAL = 0.4


def best_block(seats: List[Seat], party: int) -> Optional[SeatBlock]:
    """Best contiguous run of `party` reservable seats, or None if none fit."""
    if party < 1:
        return None
    real = [s for s in seats if s.display and s.type != "NotASeat"]
    if not real:
        return None

    rows = sorted({s.row for s in real})
    front, back = rows[0], rows[-1]
    row_span = back - front
    v_norm = max(IDEAL_ROW_FRAC, 1 - IDEAL_ROW_FRAC)

    best: Optional[SeatBlock] = None
    for row in rows:
        rseats = sorted((s for s in real if s.row == row), key=lambda s: s.col)
        cols = [s.col for s in rseats]
        mid = (cols[0] + cols[-1]) / 2
        half = max(mid - cols[0], 1)
        if row_span:
            rfrac = (row - front) / row_span
            vpen = min(abs(rfrac - IDEAL_ROW_FRAC) / v_norm, 1.0)
        else:
            vpen = 0.0  # single-row map: no depth information, no penalty

        # Walk the row accumulating runs of physically adjacent reservable
        # seats. Any taken seat, aisle, or column gap breaks the run.
        run: List[Seat] = []
        prev_col = None
        for s in rseats + [None]:
            usable = s is not None and s.reservable
            adjacent = usable and prev_col is not None and s.col == prev_col + 1
            if usable and (not run or adjacent):
                run.append(s)
            else:
                best = _consider_run(run, party, mid, half, vpen, row, best)
                run = [s] if usable else []
            prev_col = s.col if s is not None else None
    return best


def _consider_run(run, party, mid, half, vpen, row, best):
    """Slide a window of `party` across a run; keep the best-centered window."""
    if len(run) < party:
        return best
    for i in range(len(run) - party + 1):
        window = run[i : i + party]
        center = sum(w.col for w in window) / party
        hpen = min(abs(center - mid) / half, 1.0)
        score = round(100 * (1 - W_HORIZONTAL * hpen - W_VERTICAL * vpen), 1)
        if best is None or score > best.score:
            best = SeatBlock(seats=tuple(w.name for w in window), row=row, score=score)
    return best
