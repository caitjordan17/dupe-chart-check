"""
DupeChartCheck - Duplicate Chart Identifier
=========================================
Detects duplicate charts based on:
  - Same patient_id
  - Same page_count
  - File sizes within 99% of each other (i.e. ratio >= 0.99)

Outputs:
  1. unique_charts.csv       — One representative chart per duplicate group (plus all singletons)
  2. duplicate_groups.csv    — Each unique chart alongside all its duplicates
"""

import csv
import sys
import os
from itertools import combinations


# ── Config ────────────────────────────────────────────────────────────────────

INPUT_FILE = "charts.csv"           # Change to your input file path
UNIQUE_OUTPUT = "unique_charts.csv"
DUPLICATES_OUTPUT = "duplicate_groups.csv"

REQUIRED_HEADERS = {"project_name", "chart_id",
                    "page_count", "file_size", "patient_id"}
# file sizes must be within 99% of each other
FILE_SIZE_SIMILARITY_THRESHOLD = 0.99
# threshold can be changed, the lower the threshold the higher the chance of non-dupes
# script sorts by file size desc so the identified unique record will be largest


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_csv(filepath):
    """Load CSV and validate headers."""
    if not os.path.exists(filepath):
        print(f"[ERROR] File not found: {filepath}")
        sys.exit(1)

    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        headers = set(reader.fieldnames or [])
        missing = REQUIRED_HEADERS - headers
        if missing:
            print(f"[ERROR] Missing required columns: {missing}")
            sys.exit(1)
        rows = list(reader)

    print(f"[INFO] Loaded {len(rows)} rows from '{filepath}'")
    return rows, list(reader.fieldnames or [])


def parse_row(row):
    """Convert numeric fields; return None on parse failure."""
    try:
        row["page_count"] = int(row["page_count"])
        row["file_size"] = float(row["file_size"])
    except (ValueError, KeyError) as e:
        print(f"[WARN] Skipping row due to parse error ({e}): {row}")
        return None
    return row


def sizes_within_threshold(size_a, size_b, threshold=FILE_SIZE_SIMILARITY_THRESHOLD):
    """Return True if both file sizes are within `threshold` ratio of each other."""
    if size_a == 0 and size_b == 0:
        return True
    if size_a == 0 or size_b == 0:
        return False
    ratio = min(size_a, size_b) / max(size_a, size_b)
    return ratio >= threshold


def find_duplicate_groups(rows):
    """
    Group rows into duplicate sets.
    Two charts are duplicates if:
      - Same patient_id
      - Same page_count
      - File sizes within 99% of each other

    Uses Union-Find to handle transitive duplicates (A~B, B~C → {A,B,C}).
    """
    n = len(rows)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        parent[find(x)] = find(y)

    # Index by (patient_id, page_count) for efficient lookup
    bucket = {}
    for i, row in enumerate(rows):
        key = (row["patient_id"], row["page_count"])
        bucket.setdefault(key, []).append(i)

    for key, indices in bucket.items():
        for i, j in combinations(indices, 2):
            if sizes_within_threshold(rows[i]["file_size"], rows[j]["file_size"]):
                union(i, j)

    # Build groups {root_index: [row_indices]}
    groups = {}
    for i in range(n):
        root = find(i)
        groups.setdefault(root, []).append(i)

    return groups


def sort_rows(rows):
    """Sort by patient_id ASC, then page_count DESC, then file_size DESC."""
    return sorted(
        rows,
        key=lambda r: (r["patient_id"], -r["page_count"], -r["file_size"])
    )


def write_csv(filepath, fieldnames, rows):
    """Write rows to a CSV file."""
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"[INFO] Written {len(rows)} rows → '{filepath}'")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    input_file = sys.argv[1] if len(sys.argv) > 1 else INPUT_FILE

    # Load & parse
    raw_rows, fieldnames = load_csv(input_file)
    rows = [r for r in (parse_row(row) for row in raw_rows) if r is not None]

    # Sort FIRST before any duplicate detection
    rows = sort_rows(rows)

    # Detect duplicates on the sorted rows
    groups = find_duplicate_groups(rows)

    # ── Output 1: unique_charts.csv ──────────────────────────────────────────
    # Pick the chart with the largest file_size from each group as the "unique" representative
    unique_rows = []
    for root, indices in groups.items():
        group_rows = [rows[i] for i in indices]
        representative = max(group_rows, key=lambda r: r["file_size"])
        unique_rows.append(representative)

    write_csv(UNIQUE_OUTPUT, fieldnames, unique_rows)

    # ── Output 2: duplicate_groups.csv ───────────────────────────────────────
    # Extra columns to help analysts understand grouping
    dup_fieldnames = fieldnames + ["duplicate_group_id", "role"]
    dup_rows = []

    duplicate_group_counter = 0
    singletons = 0

    for root, indices in sorted(groups.items()):
        group_rows = [rows[i] for i in indices]

        if len(group_rows) == 1:
            # Singleton — no duplicates, still include it
            row = dict(group_rows[0])
            row["duplicate_group_id"] = ""
            row["role"] = "unique"
            dup_rows.append(row)
            singletons += 1
        else:
            duplicate_group_counter += 1
            group_id = f"GRP-{duplicate_group_counter:04d}"
            representative = max(group_rows, key=lambda r: r["file_size"])

            for r in group_rows:
                enriched = dict(r)
                enriched["duplicate_group_id"] = group_id
                enriched["role"] = "unique" if r is representative else "duplicate"
                dup_rows.append(enriched)

    write_csv(DUPLICATES_OUTPUT, dup_fieldnames, dup_rows)

    # ── Summary ───────────────────────────────────────────────────────────────
    total_groups = len(groups)
    dup_groups = total_groups - singletons
    total_duplicates = len(rows) - len(unique_rows)

    print()
    print("=" * 45)
    print("  DupeChartCheck — Analysis Complete")
    print("=" * 45)
    print(f"  Total lines analyzed   : {len(rows)}")
    print(f"  Unique charts          : {len(unique_rows)}")
    print(f"  Duplicate charts found : {total_duplicates}")
    print(f"  Duplicate groups       : {dup_groups}")
    print(f"  Singleton charts       : {singletons}")
    print("=" * 45)
    print(f"  → {UNIQUE_OUTPUT}")
    print(f"  → {DUPLICATES_OUTPUT}")
    print("=" * 45)


if __name__ == "__main__":
    main()
