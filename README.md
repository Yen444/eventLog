# Event Log Analysis Toolkit

This repository contains small command-line scripts for inspecting XES or CSV event logs, saving normalized CSV output, running basic and advanced analyses, previewing logs, and discovering process models with pm4py.

## Setup

Install the project dependencies first:

```powershell
uv sync
```

Run scripts with `uv run python` from the repository root.

## Repository Layout

- `logs/`: real input event logs, for example `.xes` or `.csv` files.
- `results/`: generated outputs from analysis, preview preparation, and process-model discovery.
- Repository root: Python scripts, dependency files, and documentation.

## Available Actions

### 1. Basic Analysis

Use this when you want an initial overview of an XES or CSV event log and distribution charts for selected attributes.

```powershell
uv run python basic_analysis.py "logs/RequestForPayment.xes" --case-id "case:concept:name"
```

CSV input works the same way:

```powershell
uv run python basic_analysis.py "logs/BPIChallenge2019_3WayMatchingEC.csv" --case-id "case:concept:name"
```

What it does:

- Reads an XES or CSV event log.
- Saves a CSV output file. For XES input this is the converted log; for CSV input this is a copied/normalized analysis CSV.
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
| `event_log_path` | Yes | None | Path to the input `.xes` or `.csv` event log. |
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

Example with the default output paths:

```powershell
uv run python basic_analysis.py "logs/RequestForPayment.xes" `
  --case-id "case:concept:name"
```

This writes to `results/RequestForPayment_analysis/`, including `RequestForPayment.csv` and `analysis_report.txt`. Use `--output-dir`, `--csv-output`, or `--report-output` only when you want to override those defaults.

### 2. Advanced Analysis

Use this when you need process-mining-oriented metrics such as trace variants, case arrivals, case timing, and cycle-time distributions from an XES or CSV event log.

```powershell
uv run python advanced_analysis.py "logs/RequestForPayment.xes"
```

CSV input works the same way when the required event-log columns are present:

```powershell
uv run python advanced_analysis.py "logs/BPIChallenge2019_3WayMatchingEC.csv"
```

What it does:

- Reads an XES or CSV event log.
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
| `event_log_path` | Yes | None | Path to the input `.xes` or `.csv` event log. |
| `--output-dir` | No | `results/<xes file stem>_advanced_analysis` | Directory where all advanced-analysis outputs are saved. |
| `--top-variants` | No | `20` | Number of most frequent trace variants to show in the trace-variant visualization. |

Example:

```powershell
uv run python advanced_analysis.py "logs/Sepsis Cases - Event Log.xes" `
  --output-dir "results/Sepsis Cases - Event Log_advanced_analysis" `
  --top-variants 15
```

### 3. Preview Event Log

Use this whenever you want a compact XES or CSV table preview suitable for screenshots or quick inspection.

```powershell
uv run python preview_csv.py "results/RequestForPayment_analysis/RequestForPayment.csv"
```

You can also preview a raw XES log directly:

```powershell
uv run python preview_csv.py "logs/RequestForPayment.xes"
```

What it does:

- Reads an XES or CSV event log.
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
| `event_log_path` | Yes | None | Path to the `.xes` or `.csv` event log to preview. |
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

Use this when you want to discover and export a BPMN model, process tree, and Petri net from an XES or CSV event log.

```powershell
uv run python process_model.py "logs/RequestForPayment.xes"
```

The script uses these default process-mining columns unless you override them:

```powershell
uv run python process_model.py "logs/RequestForPayment.xes" `
  --case-id "case:concept:name" `
  --activity "concept:name" `
  --timestamp "time:timestamp"
```

If your log uses different column names, replace the values of `--case-id`, `--activity`, and `--timestamp` with the exact column names from your file.

CSV input works the same way when the required process-mining columns are present:

```powershell
uv run python process_model.py "logs/BPIChallenge2019_3WayMatchingEC.csv"
```

What it does:

- Reads an XES or CSV event log.
- Uses these default columns:
  - `case:concept:name`
  - `concept:name`
  - `time:timestamp`
- Allows custom case ID, activity, and timestamp column names with `--case-id`, `--activity`, and `--timestamp`.
- Discovers a process tree using Inductive Miner.
- Discovers a BPMN model using Inductive Miner.
- Discovers a Petri net using Inductive Miner.
- Exports each model in a machine-readable format.
- Exports PNG and SVG visualizations for each model.
- Optionally replaces long activity labels with short codes such as `A`, `B`, and `C`.
- Adds the noise threshold to process-model artifact names, for example `noise_0_2`.
- Saves a process-model report with model settings, artifact paths, and summary counts.

Outputs:

- `process_model_report_noise_<threshold>.txt`.
- `process_model_noise_<threshold>.bpmn`.
- `bpmn_model_noise_<threshold>.png`.
- `bpmn_model_noise_<threshold>.svg`.
- `process_tree_noise_<threshold>.ptml`.
- `process_tree_noise_<threshold>.png`.
- `process_tree_noise_<threshold>.svg`.
- `petri_net_noise_<threshold>.pnml`.
- `petri_net_noise_<threshold>.png`.
- `petri_net_noise_<threshold>.svg`.
- `activity_code_mapping_noise_<threshold>.txt` and `activity_code_mapping_noise_<threshold>.csv` when activity codes are enabled.

For example, `--noise-threshold 0.2` creates files with `noise_0_2` in their names.

Parameters:

| Parameter | Required | Default | Description |
| --- | --- | --- | --- |
| `event_log_path` | Yes | None | Path to the input `.xes` or `.csv` event log. |
| `--output-dir` | No | `results/<xes file stem>_process_model` | Directory where all process-model outputs are saved. |
| `--noise-threshold` | No | `0.2` | Noise threshold for Inductive Miner. Higher values usually produce simpler models. |
| `--case-id` | No | `case:concept:name` | Column to use as the case identifier. |
| `--activity` | No | `concept:name` | Column to use as the activity label. |
| `--timestamp` | No | `time:timestamp` | Column to use as the event timestamp. |
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

Example with custom column names from another log:

```powershell
uv run python process_model.py "logs/LoanApp_simplified_train.csv" `
  --case-id "case_id" `
  --activity "activity" `
  --timestamp "start_time" `
  --noise-threshold 0.2
```

## Suggested Workflow

1. Run basic analysis to save a CSV output and inspect columns.
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
