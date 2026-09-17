from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable


def write_judged_csv(rows: Iterable, path: str | Path) -> None:
    """Writes judged results (anything with `.instruction`, `.verdict`,
    and `.rationale` attributes, e.g. JudgedCase or JudgedComparison) to
    a CSV file with columns: instruction, verdict, rationale."""
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["instruction", "verdict", "rationale"])
        for row in rows:
            writer.writerow([row.instruction, row.verdict.value, row.rationale])
