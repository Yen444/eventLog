# Event Log Analysis Toolkit

This repository contains small command-line scripts for inspecting XES event logs, converting them to CSV, running basic and advanced analyses, previewing CSV output, and discovering process models with pm4py.

## Setup

Install the project dependencies first:

```powershell
uv sync
```

Run scripts with `uv run python` from the repository root.

## Repository Layout

- `logs/`: real input event logs, for example `.xes` files.
- `results/`: generated outputs from analysis, preview preparation, and process-model discovery.
- Repository root: Python scripts, dependency files, and documentation.

## Available Actions

### 1. Basic Analysis

Use this when you want an initial overview of an XES event log and distribution charts for selected attributes.

```powershell
uv run python basic_analysis.py "logs/RequestForPayment.xes" --case-id "case:concept:name"
```

What it does:

- Reads an XES event log.
- Converts the log to a CSV file.
- Prints the first rows of the dataset.
- Prints all available columns.
- Counts total cases, total events, and total attributes.
- Counts missing values per column in the saved report.
- Creates distribution bar charts for selected attributes.
- Saves a text report with the selected parameters and output paths.

Outputs:

- Converted CSV file.
- `analysis_report.txt`.
- One PNG distribution chart per selected attribute in `visualizations/`.

Parameters:

| Parameter | Required | Default | Description |
| --- | --- | --- | --- |
| `xes_path` | Yes | None | Path to the input `.xes` event log. |
| `--output-dir` | No | `results/<xes file stem>_analysis` | Directory where all basic-analysis outputs are saved. |
| `--csv-output` | No | `<output-dir>/<xes file stem>.csv` | Custom path for the converted CSV file. |
| `--head` | No | `5` | Number of rows to print during the initial inspection preview. |
| `--case-id` | No | Interactive prompt | Column to use as the case identifier. Use this to avoid being prompted. |
| `--attributes` | No | Interactive prompt; press Enter for all columns | Space-separated list of columns to include in the distribution analysis. |
| `--report-output` | No | `<output-dir>/analysis_report.txt` | Custom path for the text analysis report. |

Example with selected attributes:

```powershell
uv run python basic_analysis.py "logs/Sepsis Cases - Event Log.xes" `
  --case-id "case:concept:name" `
  --attributes "concept:name" "time:timestamp" "org:group" `
  --head 10
```

Example with custom output paths:

```powershell
uv run python basic_analysis.py "logs/RequestForPayment.xes" `
  --case-id "case:concept:name" `
  --output-dir "results/RequestForPayment_analysis" `
  --csv-output "results/RequestForPayment_analysis/RequestForPayment.csv" `
  --report-output "results/RequestForPayment_analysis/analysis_report.txt"
```

### 2. Advanced Analysis

Use this when you need process-mining-oriented metrics such as trace variants, case arrivals, case timing, and cycle-time distributions.

```powershell
uv run python advanced_analysis.py "logs/RequestForPayment.xes"
```

What it does:

- Reads an XES event log.
- Automatically finds the case identifier column from `case:concept:name` or `concept:name`.
- Builds trace variants from each case's ordered activity sequence.
- Calculates trace-variant frequency, percentage, and variant length.
- Assigns every case to a trace variant.
- Calculates each case's arrival time, end time, cycle time, and case length.
- Summarizes earliest/latest arrivals, cycle-time statistics, and case-length statistics.
- Creates visualizations for top trace variants, case arrivals over time, and cycle-time distribution.
- Saves detailed CSV tables and a text report.

Outputs:

- `advanced_analysis_report.txt`.
- `tables/trace_variants.csv`.
- `tables/case_variants.csv`.
- `tables/case_timing.csv`.
- `visualizations/trace_variants_frequency.png`.
- `visualizations/case_arrivals_over_time.png`.
- `visualizations/cycle_time_distribution.png`.

Parameters:

| Parameter | Required | Default | Description |
| --- | --- | --- | --- |
| `xes_path` | Yes | None | Path to the input `.xes` event log. |
| `--output-dir` | No | `results/<xes file stem>_advanced_analysis` | Directory where all advanced-analysis outputs are saved. |
| `--top-variants` | No | `20` | Number of most frequent trace variants to show in the trace-variant visualization. |

Example:

```powershell
uv run python advanced_analysis.py "logs/Sepsis Cases - Event Log.xes" `
  --output-dir "results/Sepsis Cases - Event Log_advanced_analysis" `
  --top-variants 15
```

### 3. Preview CSV Log

Use this after basic analysis has produced a CSV, or whenever you want a compact table preview suitable for screenshots or quick inspection.

```powershell
uv run python preview_csv.py "results/RequestForPayment_analysis/RequestForPayment.csv"
```

What it does:

- Reads a CSV file.
- Selects useful event-log columns by default when they exist.
- Prints a clean, fixed-width table in the terminal.
- Truncates long cell values so the preview remains readable.

Default preview columns, when available:

- `case:concept:name`
- `concept:name`
- `time:timestamp`
- `lifecycle:transition`
- `org:group`

If none of those columns exist, the script shows the first six columns.

Parameters:

| Parameter | Required | Default | Description |
| --- | --- | --- | --- |
| `csv_path` | Yes | None | Path to the CSV file to preview. |
| `--rows` | No | `8` | Number of rows to print. |
| `--columns` | No | Default event-log columns when available; otherwise first six columns | Space-separated list of specific columns to show. |
| `--max-width` | No | `28` | Maximum width of each cell before truncation. |

Example with selected columns:

```powershell
uv run python preview_csv.py "results/RequestForPayment_analysis/RequestForPayment.csv" `
  --rows 12 `
  --columns "case:concept:name" "concept:name" "time:timestamp" `
  --max-width 36
```

### 4. Create Process Model

Use this when you want to discover and export a BPMN model, process tree, and Petri net from an XES event log.

```powershell
uv run python process_model.py "logs/RequestForPayment.xes"
```

What it does:

- Reads an XES event log.
- Requires these columns:
  - `case:concept:name`
  - `concept:name`
  - `time:timestamp`
- Discovers a process tree using Inductive Miner.
- Discovers a BPMN model using Inductive Miner.
- Discovers a Petri net using Inductive Miner.
- Exports each model in a machine-readable format.
- Exports PNG and SVG visualizations for each model.
- Optionally replaces long activity labels with short codes such as `A`, `B`, and `C`.
- Saves a process-model report with model settings, artifact paths, and summary counts.

Outputs:

- `process_model_report.txt`.
- `process_model.bpmn`.
- `bpmn_model.png`.
- `bpmn_model.svg`.
- `process_tree.ptml`.
- `process_tree.png`.
- `process_tree.svg`.
- `petri_net.pnml`.
- `petri_net.png`.
- `petri_net.svg`.
- `activity_code_mapping.txt` and `activity_code_mapping.csv` when activity codes are enabled.

Parameters:

| Parameter | Required | Default | Description |
| --- | --- | --- | --- |
| `xes_path` | Yes | None | Path to the input `.xes` event log. |
| `--output-dir` | No | `results/<xes file stem>_process_model` | Directory where all process-model outputs are saved. |
| `--noise-threshold` | No | `0.2` | Noise threshold for Inductive Miner. Higher values usually produce simpler models. |
| `--use-activity-codes` | No | `false` | Use `true` to replace activity names with short codes in exported models and images. |

Example with activity codes:

```powershell
uv run python process_model.py "logs/RequestForPayment.xes" `
  --output-dir "results/RequestForPayment_process_model" `
  --noise-threshold 0.2 `
  --use-activity-codes true
```

Example with a simpler model:

```powershell
uv run python process_model.py "logs/Sepsis Cases - Event Log.xes" `
  --noise-threshold 0.4
```

## Suggested Workflow

1. Run basic analysis to convert the XES file to CSV and inspect columns.
2. Preview the generated CSV when you need a compact table view.
3. Run advanced analysis to study trace variants, arrivals, and cycle times.
4. Create the process model when the log structure is clear and the required columns are available.

Example end-to-end workflow:

```powershell
uv run python basic_analysis.py "logs/RequestForPayment.xes" --case-id "case:concept:name"
uv run python preview_csv.py "results/RequestForPayment_analysis/RequestForPayment.csv"
uv run python advanced_analysis.py "logs/RequestForPayment.xes"
uv run python process_model.py "logs/RequestForPayment.xes" --use-activity-codes true
```
