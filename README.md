# 🔍 DupeChartCheck

**Duplicate Chart Identifier** — You are likely coding more duplicate medical charts than you'd like due to how charts are stored across your network. Retrieving duplicate charts with different chart names and IDs is quite common across many in-house retrieval systems and even chart retrieval vendors. Accidentally coding duplicate charts - especially ones with larger page counts - is costly, inefficient, and can create coder burnout. 

DupeChartCheck detects near-duplicate medical charts in a CSV file and separates them into clean output files for review so you're only coding unique charts.

App is a python script to use on your local drive to handle non-phi information to make identifying duplicate charts easy & safe. 

---

## Requirements

- Python 3.6+
- No third-party dependencies — uses only the Python standard library

---

## Input

A `.csv` file with the following required headers (additional columns are preserved):

| Column | Type | Description |
|---|---|---|
| `project_name` | string | Name of the project |
| `chart_id` | string | Unique chart identifier |
| `page_count` | integer | Number of pages in the chart |
| `file_size` | float | Size of the chart file |
| `patient_id` | string | Patient identifier |

---

## Usage

```bash
python dupechartcheck.py your_file.csv
```

If no file argument is provided, the script defaults to `charts.csv` in the same directory.

You can also update the `INPUT_FILE` constant at the top of the script to hardcode a path.

---

## How It Works

1. **Load & validate** — reads the CSV and confirms all required headers are present
2. **Parse** — converts `page_count` to `int` and `file_size` to `float`; rows with parse errors are skipped with a warning
3. **Sort** — sorts all rows by `patient_id` ASC → `page_count` DESC → `file_size` DESC before any processing
4. **Detect duplicates** — two charts are considered duplicates if they share the same `patient_id`, the same `page_count`, and their file sizes are within 99% of each other (`min / max >= 0.99`)
5. **Group transitively** — uses Union-Find so if Chart A matches B and B matches C, all three land in the same duplicate group (not just pairwise pairs)
6. **Select representative** — within each duplicate group, the chart with the largest `file_size` is designated as the `unique` representative
7. **Output** — writes two CSV files (see below)

---

## Outputs

### `unique_charts.csv`
One row per chart group — the representative chart from each duplicate group, plus all charts that had no duplicates. Use this as your clean, deduplicated chart list.

Contains the same columns as the input file.

### `duplicate_groups.csv`
Every chart in the input, annotated with two extra columns:

| Column | Description |
|---|---|
| `duplicate_group_id` | Group label (e.g. `GRP-0001`) for charts with duplicates; blank for singletons |
| `role` | `unique` for the representative chart; `duplicate` for the others |

Use this file to audit what was grouped together and verify the duplicate detection results.

---

## Console Output

When the script finishes, it prints a summary:

```
=============================================
  DupeChartCheck — Scan Complete
=============================================
  Total lines analyzed   : 1500
  Unique charts          : 1312
  Duplicate charts found : 188
  Duplicate groups       : 74
  Singleton charts       : 1238
=============================================
  → unique_charts.csv
  → duplicate_groups.csv
=============================================
```

---

## Configuration

At the top of `dupechartcheck.py`, three constants can be adjusted:

| Constant | Default | Description |
|---|---|---|
| `INPUT_FILE` | `"charts.csv"` | Default input path if no CLI argument is passed |
| `UNIQUE_OUTPUT` | `"unique_charts.csv"` | Output path for the deduplicated chart list |
| `DUPLICATES_OUTPUT` | `"duplicate_groups.csv"` | Output path for the full annotated duplicate report |
| `FILE_SIZE_SIMILARITY_THRESHOLD` | `0.99` | Minimum file size ratio to consider two charts duplicates |

To tighten or loosen the file size match, adjust `FILE_SIZE_SIMILARITY_THRESHOLD` — `1.0` requires exact file size matches, while `0.95` allows up to a 5% difference.
