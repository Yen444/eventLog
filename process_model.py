from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import pm4py

ACTIVITY_COLUMN = "concept:name"
TIME_COLUMN = "time:timestamp"
CASE_ID_COLUMN = "case:concept:name"
DISCOVERY_ALGORITHM = "Inductive Miner"
DEFAULT_NOISE_THRESHOLD = 0.2
SLIDE_LAYOUT_DIRECTION = "LR"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Discover a process model from an XES event log using pm4py."
    )
    parser.add_argument("xes_path", type=Path, help="Path to the input XES file.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Optional directory where all process-model outputs will be saved.",
    )
    parser.add_argument(
        "--noise-threshold",
        type=float,
        default=DEFAULT_NOISE_THRESHOLD,
        help="Noise threshold for inductive discovery. Higher values typically simplify the discovered model.",
    )
    parser.add_argument(
        "--use-activity-codes",
        type=lambda value: str(value).lower() == "true",
        default=False,
        help="Whether to replace activity labels with short codes in the exported models. Use true or false.",
    )
    return parser.parse_args()


def resolve_output_dir(xes_path: Path, output_dir: Path | None) -> Path:
    if output_dir is not None:
        return output_dir
    return Path("results") / f"{xes_path.stem}_process_model"


def validate_required_columns(df: pd.DataFrame) -> None:
    required_columns = [CASE_ID_COLUMN, ACTIVITY_COLUMN, TIME_COLUMN]
    missing = [column for column in required_columns if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")


def generate_activity_code(index: int) -> str:
    code = ""
    current = index
    while True:
        current, remainder = divmod(current, 26)
        code = chr(ord("A") + remainder) + code
        if current == 0:
            return code
        current -= 1


def build_activity_code_mapping(df: pd.DataFrame) -> dict[str, str]:
    unique_activities = pd.Series(df[ACTIVITY_COLUMN]).dropna().astype(str).drop_duplicates().tolist()
    return {
        activity: generate_activity_code(index)
        for index, activity in enumerate(unique_activities)
    }


def apply_activity_codes(df: pd.DataFrame, activity_code_map: dict[str, str]) -> pd.DataFrame:
    coded_df = df.copy()
    coded_df[ACTIVITY_COLUMN] = coded_df[ACTIVITY_COLUMN].map(
        lambda value: activity_code_map.get(str(value), str(value)) if pd.notna(value) else value
    )
    return coded_df


def write_activity_code_files(output_dir: Path, activity_code_map: dict[str, str]) -> tuple[Path, Path]:
    txt_path = output_dir / "activity_code_mapping.txt"
    csv_path = output_dir / "activity_code_mapping.csv"

    lines = ["Activity code mapping:"]
    for activity, code in activity_code_map.items():
        lines.append(f"- {code}: {activity}")
    txt_path.write_text("\n".join(lines), encoding="utf-8")

    mapping_df = pd.DataFrame(
        [{"code": code, "activity": activity} for activity, code in activity_code_map.items()]
    )
    mapping_df.to_csv(csv_path, index=False)
    return txt_path, csv_path


def write_report(
    report_path: Path,
    xes_path: Path,
    case_id_column: str,
    noise_threshold: float,
    use_activity_codes: bool,
    mapping_txt_path: Path,
    mapping_csv_path: Path,
    bpmn_path: Path,
    bpmn_png_path: Path,
    bpmn_svg_path: Path,
    process_tree_path: Path,
    process_tree_png_path: Path,
    process_tree_svg_path: Path,
    petri_net_path: Path,
    petri_net_png_path: Path,
    petri_net_svg_path: Path,
    bpmn_model,
    process_tree,
    petri_net,
) -> None:
    transition_count = len(petri_net.transitions)
    place_count = len(petri_net.places)
    arc_count = len(petri_net.arcs)
    bpmn_node_count = len(bpmn_model.get_nodes())
    bpmn_flow_count = len(bpmn_model.get_flows())

    lines = [
        f"Source XES file: {xes_path}",
        f"Case ID column: {case_id_column}",
        f"Activity column: {ACTIVITY_COLUMN}",
        f"Time column: {TIME_COLUMN}",
        f"Discovery algorithm: {DISCOVERY_ALGORITHM}",
        f"Noise threshold: {noise_threshold}",
        f"Presentation layout direction: {SLIDE_LAYOUT_DIRECTION}",
        f"Use activity codes: {use_activity_codes}",
        f"Activity labels in models/images: {'coded abbreviations' if use_activity_codes else 'original activity names'}",
        "",
        "Generated artifacts:",
        f"- BPMN model: {bpmn_path}",
        f"- BPMN PNG image: {bpmn_png_path}",
        f"- BPMN SVG image: {bpmn_svg_path}",
        f"- Process tree model: {process_tree_path}",
        f"- Process tree PNG image: {process_tree_png_path}",
        f"- Process tree SVG image: {process_tree_svg_path}",
        f"- Petri net model: {petri_net_path}",
        f"- Petri net PNG image: {petri_net_png_path}",
        f"- Petri net SVG image: {petri_net_svg_path}",
        "",
        "BPMN summary:",
        f"- Nodes: {bpmn_node_count}",
        f"- Flows: {bpmn_flow_count}",
        "",
        "Petri net summary:",
        f"- Places: {place_count}",
        f"- Transitions: {transition_count}",
        f"- Arcs: {arc_count}",
        "",
        "Process tree summary:",
        f"- Root: {process_tree.operator if process_tree.operator is not None else 'leaf'}",
        f"- Representation: {process_tree}",
    ]
    if use_activity_codes:
        lines.insert(lines.index("Generated artifacts:") + 1, f"- Activity code mapping text: {mapping_txt_path}")
        lines.insert(lines.index("Generated artifacts:") + 2, f"- Activity code mapping CSV: {mapping_csv_path}")
    report_path.write_text("\n".join(lines), encoding="utf-8")


def export_process_tree(process_tree, process_tree_path: Path, png_path: Path, svg_path: Path) -> None:
    pm4py.write_ptml(process_tree, str(process_tree_path))
    pm4py.save_vis_process_tree(process_tree, str(png_path), rankdir=SLIDE_LAYOUT_DIRECTION)
    pm4py.save_vis_process_tree(process_tree, str(svg_path), rankdir=SLIDE_LAYOUT_DIRECTION)


def export_bpmn(bpmn_model, bpmn_path: Path, png_path: Path, svg_path: Path) -> None:
    pm4py.write_bpmn(bpmn_model, str(bpmn_path))
    pm4py.save_vis_bpmn(bpmn_model, str(png_path), rankdir=SLIDE_LAYOUT_DIRECTION)
    pm4py.save_vis_bpmn(bpmn_model, str(svg_path), rankdir=SLIDE_LAYOUT_DIRECTION)


def export_petri_net(
    petri_net,
    initial_marking,
    final_marking,
    df: pd.DataFrame,
    petri_net_path: Path,
    png_path: Path,
    svg_path: Path,
) -> None:
    pm4py.write_pnml(petri_net, initial_marking, final_marking, str(petri_net_path))
    pm4py.save_vis_petri_net(
        petri_net,
        initial_marking,
        final_marking,
        str(png_path),
        rankdir=SLIDE_LAYOUT_DIRECTION,
        log=df,
    )
    pm4py.save_vis_petri_net(
        petri_net,
        initial_marking,
        final_marking,
        str(svg_path),
        rankdir=SLIDE_LAYOUT_DIRECTION,
        log=df,
    )


def main() -> None:
    args = parse_args()
    xes_path = args.xes_path
    if not xes_path.exists():
        raise FileNotFoundError(f"XES file not found: {xes_path}")

    output_dir = resolve_output_dir(xes_path, args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    df = pm4py.read_xes(str(xes_path))
    validate_required_columns(df)
    working_df = df
    mapping_txt_path = output_dir / "activity_code_mapping.txt"
    mapping_csv_path = output_dir / "activity_code_mapping.csv"
    if args.use_activity_codes:
        activity_code_map = build_activity_code_mapping(df)
        working_df = apply_activity_codes(df, activity_code_map)
        mapping_txt_path, mapping_csv_path = write_activity_code_files(output_dir, activity_code_map)

    process_tree = pm4py.discover_process_tree_inductive(
        working_df,
        noise_threshold=args.noise_threshold,
        activity_key=ACTIVITY_COLUMN,
        timestamp_key=TIME_COLUMN,
        case_id_key=CASE_ID_COLUMN,
    )
    bpmn_model = pm4py.discover_bpmn_inductive(
        working_df,
        noise_threshold=args.noise_threshold,
        activity_key=ACTIVITY_COLUMN,
        timestamp_key=TIME_COLUMN,
        case_id_key=CASE_ID_COLUMN,
    )
    petri_net, initial_marking, final_marking = pm4py.discover_petri_net_inductive(
        working_df,
        noise_threshold=args.noise_threshold,
        activity_key=ACTIVITY_COLUMN,
        timestamp_key=TIME_COLUMN,
        case_id_key=CASE_ID_COLUMN,
    )

    bpmn_path = output_dir / "process_model.bpmn"
    bpmn_png_path = output_dir / "bpmn_model.png"
    bpmn_svg_path = output_dir / "bpmn_model.svg"
    process_tree_path = output_dir / "process_tree.ptml"
    process_tree_png_path = output_dir / "process_tree.png"
    process_tree_svg_path = output_dir / "process_tree.svg"
    petri_net_path = output_dir / "petri_net.pnml"
    petri_net_png_path = output_dir / "petri_net.png"
    petri_net_svg_path = output_dir / "petri_net.svg"
    report_path = output_dir / "process_model_report.txt"

    export_bpmn(bpmn_model, bpmn_path, bpmn_png_path, bpmn_svg_path)
    export_process_tree(process_tree, process_tree_path, process_tree_png_path, process_tree_svg_path)
    export_petri_net(
        petri_net,
        initial_marking,
        final_marking,
        working_df,
        petri_net_path,
        petri_net_png_path,
        petri_net_svg_path,
    )
    write_report(
        report_path,
        xes_path,
        CASE_ID_COLUMN,
        args.noise_threshold,
        args.use_activity_codes,
        mapping_txt_path,
        mapping_csv_path,
        bpmn_path,
        bpmn_png_path,
        bpmn_svg_path,
        process_tree_path,
        process_tree_png_path,
        process_tree_svg_path,
        petri_net_path,
        petri_net_png_path,
        petri_net_svg_path,
        bpmn_model,
        process_tree,
        petri_net,
    )

    print(f"Process model discovery completed for '{xes_path}'.")
    print(f"Outputs saved in '{output_dir}'.")
    print(f"Discovery algorithm: '{DISCOVERY_ALGORITHM}'")
    print(f"Noise threshold: {args.noise_threshold}")
    print(f"Use activity codes: {args.use_activity_codes}")
    if args.use_activity_codes:
        print(f"Activity code mapping: '{mapping_txt_path}'")
    print(f"Report: '{report_path}'")
    print(f"BPMN SVG image: '{bpmn_svg_path}'")
    print(f"Process tree SVG image: '{process_tree_svg_path}'")
    print(f"Petri net SVG image: '{petri_net_svg_path}'")


if __name__ == "__main__":
    main()
