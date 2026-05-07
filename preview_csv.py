from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from pm4py import convert_to_dataframe, read_xes

DEFAULT_COLUMNS = [
    "case:concept:name",
    "concept:name",
    "time:timestamp",
    "lifecycle:transition",
    "org:group",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Print a clean XES or CSV event-log preview suitable for screenshots."
    )
    parser.add_argument("event_log_path", type=Path, help="Path to the XES or CSV event log to preview.")
    parser.add_argument(
        "--rows",
        type=int,
        default=8,
        help="Number of rows to print.",
    )
    parser.add_argument(
        "--columns",
        nargs="*",
        help="Optional list of columns to show. Defaults to a compact event-oriented set when available.",
    )
    parser.add_argument(
        "--max-width",
        type=int,
        default=28,
        help="Maximum width per cell before truncation.",
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


def pick_columns(df: pd.DataFrame, requested: list[str] | None) -> list[str]:
    if requested:
        missing = [column for column in requested if column not in df.columns]
        if missing:
            raise ValueError(f"Unknown columns: {', '.join(missing)}")
        return requested

    columns = [column for column in DEFAULT_COLUMNS if column in df.columns]
    if columns:
        return columns

    return df.columns[: min(6, len(df.columns))].tolist()


def truncate(value: object, max_width: int) -> str:
    text = "<missing>" if pd.isna(value) else str(value)
    if len(text) <= max_width:
        return text
    return text[: max_width - 3] + "..."


def build_table(df: pd.DataFrame, columns: list[str], rows: int, max_width: int) -> str:
    preview = df.loc[:, columns].head(rows).copy()
    rendered_rows = []
    for _, row in preview.iterrows():
        rendered_rows.append([truncate(row[column], max_width) for column in columns])

    widths = []
    for index, column in enumerate(columns):
        content_width = max((len(row[index]) for row in rendered_rows), default=0)
        widths.append(max(len(column), content_width))

    def render_line(values: list[str]) -> str:
        cells = [value.ljust(widths[index]) for index, value in enumerate(values)]
        return "| " + " | ".join(cells) + " |"

    border = "+-" + "-+-".join("-" * width for width in widths) + "-+"
    lines = [border, render_line(columns), border]
    lines.extend(render_line(row) for row in rendered_rows)
    lines.append(border)
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    if not args.event_log_path.exists():
        raise FileNotFoundError(f"Event log file not found: {args.event_log_path}")

    df = load_event_log_as_dataframe(args.event_log_path)
    columns = pick_columns(df, args.columns)
    table = build_table(df, columns, args.rows, args.max_width)

    print(f"Event log preview: {args.event_log_path}")
    print(f"Rows shown: {min(args.rows, len(df))} of {len(df)}")
    print(f"Columns shown: {', '.join(columns)}")
    print()
    print(table)


if __name__ == "__main__":
    main()
