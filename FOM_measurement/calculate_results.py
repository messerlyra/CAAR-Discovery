#!/usr/bin/env python3
import argparse
import re
import sys
import json
import csv
from pathlib import Path

STAGES = {
    "md": "MD Sampling",
    "qm": "QM Labeling",
    "ml": "ML Training",
}

def parse_duration(value):
    """Convert HH:MM:SS.ss to seconds."""
    try:
        hours, minutes, seconds = value.strip().split(":")
        return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    except (ValueError, IndexError) as e:
        raise ValueError(f"Invalid duration format '{value}': {e}")

def extract_nodes(filename):
    """Extract node counts from filename using the project standard regex."""
    match = re.search(r'nodes_(\d+)MD_(\d+)QM_(\d+)ML', filename)
    if not match:
        raise ValueError(f"Filename {filename} does not match expected pattern 'nodes_NMD_NQM_NML'")
    return int(match.group(1)), int(match.group(2)), int(match.group(3))

def extract_results(output):
    """Extract FOM, configuration counts, and extrapolated stage times."""
    match = re.search(
        r"FOM\s*\((?:components|comp)/hour\)\s*:\s*([\d,]+(?:\.\d+)?)",
        output,
        re.I,
    )

    if not match:
        raise ValueError("Could not extract FOM from analyzer output.")

    result = {
        "fom": float(match.group(1).replace(",", ""))
    }

    section = re.search(
        r"Stage Durations:\s*(.*?)(?:\n\s*(?:Figure of Merit|Time Distribution):|\Z)",
        output,
        re.S | re.I,
    )

    if not section:
        raise ValueError("Could not find Stage Durations section.")

    for key, label in [*STAGES.items(), ("total", "Total")]:
        duration = re.search(
            r"^\s*" + re.escape(label) + r"\s*:\s*(\d+:\d+:[\d.]+)",
            section.group(1),
            re.M,
        )

        if not duration:
            raise ValueError(f"Could not extract {label} duration.")

        result[f"{key}_time"] = parse_duration(
            duration.group(1)
        )

    count_patterns = {
        "md_trajectories": (
            r"Trajectories analyzed\s*:\s*([\d,]+)"
        ),
        "qm_calcs": (
            r"Extrapolated QM calcs\s*:\s*([\d,]+)"
        ),
    }

    for key, pattern in count_patterns.items():
        count = re.search(pattern, output, re.I)

        if not count:
            raise ValueError(
                f"Could not extract {key} from analyzer output."
            )

        result[key] = int(count.group(1).replace(",", ""))

    return result

def calculate_scaling(results):
    """Calculate ideal FOM scaling and stage time percentages."""
    # Sort by MD nodes (assuming this is the primary scaling axis)
    results.sort(key=lambda r: r["nodes_md"])

    baseline = results[0]
    base_nodes = baseline["nodes_md"]
    base_fom = baseline["fom"]

    if base_fom <= 0:
        raise ValueError("Baseline FOM must be positive.")

    for row in results:
        nodes = row["nodes_md"]

        row["ideal_fom"] = (
            base_fom * nodes / base_nodes
        )

        row["efficiency_percent"] = (
            100 * row["fom"] / row["ideal_fom"]
        )

        total = row["total_time"]

        if total <= 0:
            raise ValueError(
                f"Nonpositive total time for {nodes} nodes."
            )

        row["total_time_hours"] = total / 3600

        for stage in STAGES:
            duration = row[f"{stage}_time"]

            if duration <= 0:
                raise ValueError(
                    f"Nonpositive {stage} time for {nodes} nodes."
                )

            row[f"{stage}_time_hours"] = duration / 3600

            row[f"{stage}_percent"] = (
                100 * duration / total
            )

def save_csv(results, output_file):
    """Save comparison results with controlled numeric precision."""

    columns = [
        "nodes",
        "nodes_md",
        "nodes_qm",
        "nodes_ml",
        "filename",
        "md_trajectories",
        "qm_calcs",
        "fom",
        "ideal_fom",
        "efficiency_percent",
        "md_time_hours",
        "qm_time_hours",
        "ml_time_hours",
        "total_time_hours",
        "md_percent",
        "qm_percent",
        "ml_percent",
    ]

    with output_file.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as handle:

        writer = csv.DictWriter(
            handle,
            fieldnames=columns,
        )

        writer.writeheader()

        for result in results:
            row = {}

            for key in columns:
                value = result[key]

                # FOM: no decimal places
                if key in ("fom", "ideal_fom"):
                    row[key] = f"{value:.0f}"

                # Percentages: 5 significant figures
                elif key.endswith("_percent"):
                    row[key] = f"{value:.5g}"

                # Hours: 3 significant figures
                elif key.endswith("_hours"):
                    row[key] = f"{value:.3g}"

                else:
                    row[key] = value

            writer.writerow(row)


def main():
    parser = argparse.ArgumentParser(description="Parse multiple ALF FOM result files and calculate scaling.")
    parser.add_argument(
        "--results",
        type=Path,
        default=Path("FOM_runs/results"),
        help="Results directory (default: FOM_runs/results).",
    )
    args = parser.parse_args()

    results = []

    for file_path in args.results.glob("*.txt"):
        if not file_path.is_file():
            print(f"Warning: File not found: {file_path}", file=sys.stderr)
            continue

        try:
            # Extract nodes from filename
            md_nodes, qm_nodes, ml_nodes = extract_nodes(file_path.name)
            
            # Read and parse content
            content = file_path.read_text(encoding="utf-8")
            data = extract_results(content)
            
            # Combine
            entry = {
                "filename": file_path.name,
                "nodes_md": md_nodes,
                "nodes_qm": qm_nodes,
                "nodes_ml": ml_nodes,
                "nodes": md_nodes, # For compatibility with calculate_scaling if needed
                **data
            }
            results.append(entry)
            print(f"Parsed {file_path.name}")

        except Exception as e:
            print(f"Error parsing {file_path.name}: {e}", file=sys.stderr)

    if not results:
        print("No valid results parsed.", file=sys.stderr)
        sys.exit(1)

    try:
        calculate_scaling(results)
    except Exception as e:
        print(f"Error calculating scaling: {e}", file=sys.stderr)
        sys.exit(1)
    with open(args.results / "results.json", "w", encoding="utf-8") as f:
        f.write(json.dumps(results, indent=2))

    save_csv(
        results,
        args.results / "FOM_comparison.csv",
    )
    
    print(f"json results: {args.results/'results.json'}")
    print(f"CSV results: {args.results/'FOM_comparison.csv'}")

if __name__ == "__main__":
    main()
