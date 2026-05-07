from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

import matplotlib
import pandas as pd
from pm4py import convert_to_dataframe, read_xes

matplotlib.use("Agg")
import matplotlib.pyplot as plt

CASE_ID_CANDIDATES = ["case:concept:name", "concept:name"]
ACTIVITY_COLUMN = "concept:name"
TIME_COLUMN = "time:timestamp"
DEFAULT_TOP_VARIANTS = 20


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run advanced analysis on an XES or CSV event log."
    )
    parser.add_argument("event_log_path", type=Path, help="Path to the input XES or CSV event log.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Optional directory where all advanced-analysis outputs will be saved.",
    )
    parser.add_argument(
        "--top-variants",
        type=int,
        default=DEFAULT_TOP_VARIANTS,
        help="Number of most frequent trace variants to show in the visualization.",
    )
    return parser.parse_args()


def sanitize_name(value: str) -> str:
    safe = "".join(character if character.isalnum() or character in {"-", "_"} else "_" for character in value)
    return safe.strip("_") or "output"


def load_event_log_as_dataframe(event_log_path: Path) -> pd.DataFrame:
    suffix = event_log_path.suffix.lower()
    if suffix == ".xes":
        log = read_xes(str(event_log_path))
        return convert_to_dataframe(log)
    if suffix == ".csv":
        return pd.read_csv(event_log_path)
    raise ValueError(f"Unsupported event log format: {event_log_path.suffix}. Use .xes or .csv.")


def resolve_output_dir(event_log_path: Path, output_dir: Path | None) -> Path:
    if output_dir is not None:
        return output_dir
    return Path("results") / f"{event_log_path.stem}_advanced_analysis"


def resolve_images_dir(output_dir: Path) -> Path:
    return output_dir / "visualizations"


def resolve_tables_dir(output_dir: Path) -> Path:
    return output_dir / "tables"


def resolve_case_id_column(df: pd.DataFrame) -> str:
    for candidate in CASE_ID_CANDIDATES:
        if candidate in df.columns:
            return candidate
    raise ValueError(
        "Could not find a case identifier column. Expected one of: "
        + ", ".join(CASE_ID_CANDIDATES)
    )


def validate_required_columns(df: pd.DataFrame, columns: list[str]) -> None:
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")


def analyze_log(df: pd.DataFrame, case_id_column: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    variant_counter: Counter[tuple[str, ...]] = Counter()
    variant_case_rows: list[dict[str, object]] = []
    case_timing_rows: list[dict[str, object]] = []

    working_df = df.copy()
    working_df[TIME_COLUMN] = pd.to_datetime(working_df[TIME_COLUMN], utc=True, errors="coerce")
    working_df["_activity_for_variant"] = working_df[ACTIVITY_COLUMN].fillna("<missing>").astype(str)
    sorted_df = working_df.sort_values([case_id_column, TIME_COLUMN, "_activity_for_variant"], na_position="last")

    grouped = sorted_df.groupby(case_id_column, dropna=False, sort=False)
    for case_id_value, case_df in grouped:
        case_id = str(case_id_value)
        activities = case_df["_activity_for_variant"].tolist()
        variant = tuple(activities)
        variant_counter[variant] += 1

        valid_timestamps = case_df[TIME_COLUMN].dropna()

        if not valid_timestamps.empty:
            start_time = valid_timestamps.iloc[0]
            end_time = valid_timestamps.iloc[-1]
            cycle_time = end_time - start_time
        else:
            start_time = None
            end_time = None
            cycle_time = pd.NaT

        variant_case_rows.append(
            {
                "case_id": case_id,
                "trace_variant": " > ".join(variant),
                "variant_length": len(variant),
            }
        )
        case_timing_rows.append(
            {
                "case_id": case_id,
                "arrival_time": start_time,
                "end_time": end_time,
                "cycle_time": cycle_time,
                "case_length": len(case_df),
            }
        )

    total_cases = len(case_timing_rows) if case_timing_rows else 0
    variant_rows: list[dict[str, object]] = []
    for variant_id, (variant, frequency) in enumerate(
        sorted(variant_counter.items(), key=lambda item: (-item[1], item[0])),
        start=1,
    ):
        variant_rows.append(
            {
                "variant_id": variant_id,
                "frequency": frequency,
                "percentage": (frequency / total_cases * 100) if total_cases else 0.0,
                "variant_length": len(variant),
                "trace_variant": " > ".join(variant),
            }
        )

    variants_df = pd.DataFrame(variant_rows)
    case_variants_df = pd.DataFrame(variant_case_rows)
    case_times_df = pd.DataFrame(case_timing_rows)

    if not case_times_df.empty:
        case_times_df["cycle_time_seconds"] = case_times_df["cycle_time"].dt.total_seconds()
        case_times_df["cycle_time_hours"] = case_times_df["cycle_time_seconds"] / 3600
        case_times_df["cycle_time_days"] = case_times_df["cycle_time_seconds"] / 86400

    return variants_df, case_variants_df, case_times_df


def save_tables(
    variants_df: pd.DataFrame,
    case_variants_df: pd.DataFrame,
    case_times_df: pd.DataFrame,
    tables_dir: Path,
) -> dict[str, Path]:
    tables_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "trace_variants": tables_dir / "trace_variants.csv",
        "case_variants": tables_dir / "case_variants.csv",
        "case_timing": tables_dir / "case_timing.csv",
    }
    variants_df.to_csv(paths["trace_variants"], index=False)
    case_variants_df.to_csv(paths["case_variants"], index=False)
    case_times_df.to_csv(paths["case_timing"], index=False)
    return paths


def plot_trace_variants(variants_df: pd.DataFrame, images_dir: Path, top_variants: int) -> Path:
    images_dir.mkdir(parents=True, exist_ok=True)
    plot_df = variants_df.head(top_variants).copy()
    labels = [f"V{row.variant_id}" for row in plot_df.itertuples()]
    fig_height = max(4, 0.45 * len(plot_df) + 1.5)
    fig, ax = plt.subplots(figsize=(12, fig_height))
    ax.barh(labels, plot_df["frequency"], color="#4C78A8")
    ax.set_title(f"Top {min(top_variants, len(variants_df))} Trace Variants by Frequency")
    ax.set_xlabel("Frequency")
    ax.set_ylabel("Variant ID")
    ax.invert_yaxis()
    fig.tight_layout()

    output_path = images_dir / "trace_variants_frequency.png"
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return output_path


def plot_case_arrivals(case_times_df: pd.DataFrame, images_dir: Path) -> Path:
    images_dir.mkdir(parents=True, exist_ok=True)
    arrivals = case_times_df.dropna(subset=["arrival_time"]).copy()
    arrivals["arrival_time"] = pd.to_datetime(arrivals["arrival_time"], utc=True)
    arrivals["arrival_date"] = arrivals["arrival_time"].dt.tz_convert("UTC").dt.tz_localize(None).dt.floor("D")
    daily_arrivals = arrivals.groupby("arrival_date").size().sort_index()

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(daily_arrivals.index, daily_arrivals.values, color="#59A14F", linewidth=2)
    ax.set_title("Case Arrivals Over Time")
    ax.set_xlabel("Arrival date")
    ax.set_ylabel("Number of new cases")
    ax.grid(True, axis="y", alpha=0.3)
    fig.autofmt_xdate()
    fig.tight_layout()

    output_path = images_dir / "case_arrivals_over_time.png"
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return output_path


def plot_cycle_time_distribution(case_times_df: pd.DataFrame, images_dir: Path) -> Path:
    images_dir.mkdir(parents=True, exist_ok=True)
    cycle_hours = case_times_df["cycle_time_hours"].dropna()

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.hist(cycle_hours, bins=min(30, max(10, len(cycle_hours) // 20 or 10)), color="#E15759", edgecolor="white")
    ax.set_title("Cycle Time Distribution")
    ax.set_xlabel("Cycle time (hours)")
    ax.set_ylabel("Number of cases")
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()

    output_path = images_dir / "cycle_time_distribution.png"
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return output_path


def format_timestamp(value) -> str:
    if pd.isna(value):
        return "N/A"
    timestamp = pd.to_datetime(value, utc=True)
    return timestamp.isoformat()


def format_duration_hours(value) -> str:
    if pd.isna(value):
        return "N/A"
    return f"{float(value):.2f} hours"


def build_summary_lines(variants_df: pd.DataFrame, case_times_df: pd.DataFrame) -> list[str]:
    cycle_hours = case_times_df["cycle_time_hours"].dropna()
    arrivals = case_times_df["arrival_time"].dropna()
    case_lengths = case_times_df["case_length"].dropna()

    lines = [
        "Advanced analysis summary:",
        f"- Total cases: {len(case_times_df)}",
        f"- Total number of trace variants: {len(variants_df)}",
        f"- Earliest case arrival: {format_timestamp(arrivals.min()) if not arrivals.empty else 'N/A'}",
        f"- Latest case arrival: {format_timestamp(arrivals.max()) if not arrivals.empty else 'N/A'}",
        f"- Mean cycle time: {format_duration_hours(cycle_hours.mean()) if not cycle_hours.empty else 'N/A'}",
        f"- Median cycle time: {format_duration_hours(cycle_hours.median()) if not cycle_hours.empty else 'N/A'}",
        f"- Minimum cycle time: {format_duration_hours(cycle_hours.min()) if not cycle_hours.empty else 'N/A'}",
        f"- Maximum cycle time: {format_duration_hours(cycle_hours.max()) if not cycle_hours.empty else 'N/A'}",
        f"- Mean case length: {float(case_lengths.mean()):.2f}" if not case_lengths.empty else "- Mean case length: N/A",
        f"- Median case length: {float(case_lengths.median()):.2f}" if not case_lengths.empty else "- Median case length: N/A",
        f"- Minimum case length: {int(case_lengths.min())}" if not case_lengths.empty else "- Minimum case length: N/A",
        f"- Maximum case length: {int(case_lengths.max())}" if not case_lengths.empty else "- Maximum case length: N/A",
    ]
    return lines


def build_variant_lines(variants_df: pd.DataFrame) -> list[str]:
    lines = ["Trace variants:"]
    for row in variants_df.itertuples():
        lines.append(
            f"- V{row.variant_id}: frequency={row.frequency}, percentage={row.percentage:.2f}%, "
            f"length={row.variant_length}, variant={row.trace_variant}"
        )
    return lines


def build_case_arrival_lines(case_times_df: pd.DataFrame) -> list[str]:
    arrival_rows = case_times_df[["case_id", "arrival_time"]].sort_values("arrival_time", na_position="last")
    lines = ["Case arrivals (first activity timestamp per case):"]
    for row in arrival_rows.itertuples():
        lines.append(f"- {row.case_id}: {format_timestamp(row.arrival_time)}")
    return lines


def build_cycle_time_lines(case_times_df: pd.DataFrame) -> list[str]:
    cycle_rows = case_times_df.sort_values("cycle_time_hours", na_position="last")
    lines = ["Cycle times by case:"]
    for row in cycle_rows.itertuples():
        lines.append(
            f"- {row.case_id}: start={format_timestamp(row.arrival_time)}, "
            f"end={format_timestamp(row.end_time)}, cycle_time={format_duration_hours(row.cycle_time_hours)}"
        )
    return lines


def write_report(
    report_path: Path,
    event_log_path: Path,
    case_id_column: str,
    tables: dict[str, Path],
    images: dict[str, Path],
    variants_df: pd.DataFrame,
    case_times_df: pd.DataFrame,
) -> None:
    lines = [
        f"Source event log file: {event_log_path}",
        f"Case ID column: {case_id_column}",
        f"Activity column: {ACTIVITY_COLUMN}",
        f"Time column: {TIME_COLUMN}",
        f"Visualization folder: {next(iter(images.values())).parent if images else report_path.parent / 'visualizations'}",
        f"Tables folder: {next(iter(tables.values())).parent if tables else report_path.parent / 'tables'}",
        "",
    ]
    lines.extend(build_summary_lines(variants_df, case_times_df))
    lines.append("")
    lines.append("Output tables:")
    for name, path in tables.items():
        lines.append(f"- {name}: {path}")
    lines.append("")
    lines.append("Output visualizations:")
    for name, path in images.items():
        lines.append(f"- {name}: {path}")
    lines.append("")
    lines.extend(build_variant_lines(variants_df))
    lines.append("")
    lines.extend(build_case_arrival_lines(case_times_df))
    lines.append("")
    lines.extend(build_cycle_time_lines(case_times_df))

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    event_log_path = args.event_log_path
    if not event_log_path.exists():
        raise FileNotFoundError(f"Event log file not found: {event_log_path}")

    output_dir = resolve_output_dir(event_log_path, args.output_dir)
    images_dir = resolve_images_dir(output_dir)
    tables_dir = resolve_tables_dir(output_dir)
    report_path = output_dir / "advanced_analysis_report.txt"

    log_df = load_event_log_as_dataframe(event_log_path)
    case_id_column = resolve_case_id_column(log_df)
    validate_required_columns(log_df, [case_id_column, ACTIVITY_COLUMN, TIME_COLUMN])
    variants_df, case_variants_df, case_times_df = analyze_log(log_df, case_id_column)

    table_paths = save_tables(variants_df, case_variants_df, case_times_df, tables_dir)
    image_paths = {
        "trace_variants": plot_trace_variants(variants_df, images_dir, args.top_variants),
        "case_arrivals": plot_case_arrivals(case_times_df, images_dir),
        "cycle_time_distribution": plot_cycle_time_distribution(case_times_df, images_dir),
    }
    write_report(report_path, event_log_path, case_id_column, table_paths, image_paths, variants_df, case_times_df)

    print(f"Advanced analysis completed for '{event_log_path}'.")
    print(f"Outputs saved in '{output_dir}'.")
    print(f"Case ID column used: '{case_id_column}'")
    print(f"Report: '{report_path}'")
    print("Visualizations:")
    for name, path in image_paths.items():
        print(f"- {name}: {path}")


if __name__ == "__main__":
    main()
