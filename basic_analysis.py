from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

import matplotlib
import pandas as pd
from pm4py import convert_to_dataframe, read_xes

matplotlib.use("Agg")
import matplotlib.pyplot as plt

MAX_PLOT_VALUES = 20


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Load an XES or CSV event log and run basic exploratory analysis."
    )
    parser.add_argument("event_log_path", type=Path, help="Path to the input XES or CSV event log.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Optional directory where all outputs for this event log will be saved.",
    )
    parser.add_argument(
        "--csv-output",
        type=Path,
        help="Optional path for the converted CSV file. Defaults to the event log output directory.",
    )
    parser.add_argument(
        "--head",
        type=int,
        default=5,
        help="Number of rows to show in the initial inspection preview.",
    )
    parser.add_argument(
        "--case-id",
        dest="case_id",
        help="Column name to use as the case identifier. If omitted, you will be prompted after inspection.",
    )
    parser.add_argument(
        "--attributes",
        nargs="*",
        help="Optional list of attributes to include in the distribution analysis. Defaults to all columns.",
    )
    parser.add_argument(
        "--report-output",
        type=Path,
        help="Optional path for a text file containing the analysis results. Defaults to the event log output directory.",
    )
    return parser.parse_args()


def load_event_log_as_dataframe(event_log_path: Path) -> pd.DataFrame:
    suffix = event_log_path.suffix.lower()
    if suffix == ".xes":
        log = read_xes(str(event_log_path))
        return convert_to_dataframe(log)
    if suffix == ".csv":
        return pd.read_csv(event_log_path)
    raise ValueError(f"Unsupported event log format: {event_log_path.suffix}. Use .xes or .csv.")


def save_csv(df: pd.DataFrame, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)


def print_head(df: pd.DataFrame, rows: int) -> None:
    print(f"\nDataset head ({min(rows, len(df))} rows):")
    print(df.head(rows).to_string(index=False))


def print_columns(columns: Iterable[str]) -> None:
    print("\nAvailable columns:")
    for column in columns:
        print(f"- {column}")


def validate_columns(df: pd.DataFrame, columns: list[str], label: str) -> None:
    missing = [column for column in columns if column not in df.columns]
    if missing:
        missing_text = ", ".join(missing)
        raise ValueError(f"Unknown {label}: {missing_text}")


def prompt_for_case_id(columns: list[str]) -> str:
    while True:
        selected = input("\nSelect the case_id column: ").strip()
        if selected in columns:
            return selected
        print("Please enter one of the listed columns.")


def prompt_for_attributes(columns: list[str]) -> list[str]:
    response = input(
        "\nEnter attributes for distribution analysis separated by commas, or press Enter for all columns: "
    ).strip()
    if not response:
        return columns

    selected = [item.strip() for item in response.split(",") if item.strip()]
    validate_columns(pd.DataFrame(columns=columns), selected, "attributes")
    return selected


def print_basic_counts(df: pd.DataFrame, case_id_column: str) -> None:
    total_cases = df[case_id_column].nunique(dropna=True)
    total_events = len(df)
    total_attributes = len(df.columns)

    print("\nBasic analysis:")
    print(f"- Total number of cases: {total_cases}")
    print(f"- Total number of events: {total_events}")
    print(f"- Total number of attributes: {total_attributes}")


def build_basic_counts_lines(df: pd.DataFrame, case_id_column: str) -> list[str]:
    total_cases = df[case_id_column].nunique(dropna=True)
    total_events = len(df)
    total_attributes = len(df.columns)
    return [
        "Basic analysis:",
        f"- Total number of cases: {total_cases}",
        f"- Total number of events: {total_events}",
        f"- Total number of attributes: {total_attributes}",
    ]


def build_column_summary_lines(df: pd.DataFrame) -> list[str]:
    total_rows = len(df)
    lines = ["Available columns and missing-value counts:"]
    for column in df.columns:
        nan_count = int(df[column].isna().sum())
        lines.append(f"- {column}: {nan_count}/{total_rows} NaN values")
    return lines


def print_distribution_images(image_paths: dict[str, Path]) -> None:
    print("\nDistribution visualizations:")
    for attribute, image_path in image_paths.items():
        print(f"- {attribute}: {image_path}")


def sanitize_name(value: str) -> str:
    safe = "".join(character if character.isalnum() or character in {"-", "_"} else "_" for character in value)
    return safe.strip("_") or "attribute"


def resolve_output_dir(event_log_path: Path, output_dir: Path | None) -> Path:
    if output_dir is not None:
        return output_dir
    return Path("results") / f"{event_log_path.stem}_analysis"


def resolve_csv_output(event_log_path: Path, output_dir: Path, csv_output: Path | None) -> Path:
    if csv_output is not None:
        return csv_output
    return output_dir / f"{event_log_path.stem}.csv"


def resolve_report_output(event_log_path: Path, output_dir: Path, report_output: Path | None) -> Path:
    if report_output is not None:
        return report_output
    return output_dir / "analysis_report.txt"


def resolve_images_dir(output_dir: Path) -> Path:
    return output_dir / "visualizations"


def create_distribution_plots(df: pd.DataFrame, attributes: list[str], images_dir: Path) -> dict[str, Path]:
    images_dir.mkdir(parents=True, exist_ok=True)
    image_paths: dict[str, Path] = {}

    for attribute in attributes:
        distribution = df[attribute].value_counts(dropna=False)
        display_distribution = distribution.head(MAX_PLOT_VALUES)
        labels = ["<missing>" if pd.isna(value) else str(value) for value in display_distribution.index]

        fig_height = max(4, 0.4 * len(display_distribution) + 1.5)
        fig, ax = plt.subplots(figsize=(12, fig_height))
        ax.barh(labels, display_distribution.values, color="#4C78A8")
        ax.set_title(f"Distribution of {attribute}")
        ax.set_xlabel("Count")
        ax.set_ylabel(attribute)
        ax.invert_yaxis()

        if len(distribution) > MAX_PLOT_VALUES:
            ax.text(
                1.0,
                -0.12,
                f"Showing top {MAX_PLOT_VALUES} of {len(distribution)} values",
                transform=ax.transAxes,
                ha="right",
                va="top",
            )

        fig.tight_layout()
        image_path = images_dir / f"{sanitize_name(attribute)}_distribution.png"
        fig.savefig(image_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        image_paths[attribute] = image_path

    return image_paths


def write_analysis_report(
    report_path: Path,
    event_log_path: Path,
    csv_output: Path,
    case_id_column: str,
    attributes: list[str],
    df: pd.DataFrame,
    image_paths: dict[str, Path],
) -> None:
    lines = [
        f"Source event log file: {event_log_path}",
        f"CSV output file: {csv_output}",
        f"Selected case_id column: {case_id_column}",
        f"Attributes analyzed: {', '.join(attributes)}",
        f"Visualization folder: {next(iter(image_paths.values())).parent if image_paths else report_path.parent / 'visualizations'}",
        "",
    ]
    lines.extend(build_column_summary_lines(df))
    lines.append("")
    lines.extend(build_basic_counts_lines(df, case_id_column))
    lines.append("")
    lines.append("Distribution images:")
    for attribute, image_path in image_paths.items():
        lines.append(f"- {attribute}: {image_path}")
    lines.append("")
    lines.append(f"Each chart shows up to the top {MAX_PLOT_VALUES} values for readability.")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    event_log_path = args.event_log_path
    if not event_log_path.exists():
        raise FileNotFoundError(f"Event log file not found: {event_log_path}")

    df = load_event_log_as_dataframe(event_log_path)
    output_dir = resolve_output_dir(event_log_path, args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    images_dir = resolve_images_dir(output_dir)
    csv_output = resolve_csv_output(event_log_path, output_dir, args.csv_output)
    report_output = resolve_report_output(event_log_path, output_dir, args.report_output)
    save_csv(df, csv_output)

    print(f"Saved CSV output for '{event_log_path}' to '{csv_output}'.")
    print(f"All analysis artifacts will be saved in '{output_dir}'.")
    print_head(df, args.head)
    print_columns(df.columns.tolist())

    if args.case_id:
        validate_columns(df, [args.case_id], "case_id column")
        case_id_column = args.case_id
    else:
        case_id_column = prompt_for_case_id(df.columns.tolist())

    if args.attributes:
        validate_columns(df, args.attributes, "attributes")
        attributes = args.attributes
    else:
        attributes = prompt_for_attributes(df.columns.tolist())

    print_basic_counts(df, case_id_column)
    image_paths = create_distribution_plots(df, attributes, images_dir)
    print_distribution_images(image_paths)
    write_analysis_report(
        report_output,
        event_log_path,
        csv_output,
        case_id_column,
        attributes,
        df,
        image_paths,
    )
    print(f"\nAnalysis report saved to '{report_output}'.")


if __name__ == "__main__":
    main()
