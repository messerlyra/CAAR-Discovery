#!/usr/bin/env bash
# run_FOM_worker.sh — execute FOM tests from a manifest and run comparison
#
# Usage:
#   run_FOM_worker.sh <test_dir>
#
# Conventions: The location of this script is $BASE_DIR
#              The top-level output directory is $BASE_DIR/FOM_runs
#
#   BASE_DIR         = $(dirname "$0")  — FOM_measurement
#   OUTPUT_ROOT      = $BASE_DIR/FOM_runs
#   ENVIRONMENT_SCRIPT — from env or default CAAR loader

set -uo pipefail

if [ $# -ne 1 ]; then
    echo "Usage: $0 <test_dir>" >&2
    exit 1
fi

readonly test_dir="$1"

# nodes=(nnodes_md nnodes_qm nnodes_ml)
read -a nodes < <(python3 -c "import re, sys; m = re.search(r'nodes_(\d+)MD_(\d+)QM_(\d+)ML', sys.argv[1]); print(*(m.groups())) if m else sys.exit(1)" "$test_dir")
export NNODES_MD=${nodes[0]}
export NNODES_QM=${nodes[1]}
export NNODES_ML=${nodes[2]}

readonly BASE_DIR=$(dirname $(realpath "${BASH_SOURCE[0]}"))
readonly OUTPUT_ROOT="$BASE_DIR/FOM_runs"

# Re-export derived vars for start_timing_server.sh and run_one
export ENVIRONMENT_SCRIPT="${ENVIRONMENT_SCRIPT:-/lustre/orion/world-shared/csc728/messerlyra/scripts/load_caar_env.bash}"

# Start timing collector.
# shellcheck disable=SC1090
TIMING_LOG="$test_dir/timings.csv" source "$BASE_DIR/start_timing_server.sh"

log_path="$test_dir/alf_FOM.log"

failure=0

(
    cd "$test_dir" || exit 1
    # shellcheck disable=SC1090
    source "$ENVIRONMENT_SCRIPT" || exit 1
    export PYTHONPATH="$BASE_DIR/../src:$PYTHONPATH"
    export FOM_NODE_COUNT="$NNODES_MD"
    echo "Starting FOM test: $NNODES_MD MD node(s), $NNODES_QM QM node(s), $NNODES_ML ML node(s) at $(date -Is)"
    python -u -m alframework --master master_config.json
    status=$?
    echo "ALF exit code: $status"
    exit "$status"
) > "$log_path" 2>&1
failure=$?

# Preserve cleanup of leftover ML Slurm jobs after sequential tests.
job_name="ML_${NNODES_ML}nodes"
mapfile -t job_ids < <(squeue -h -u "$USER" -n "$job_name" -o '%A')
if (( ${#job_ids[@]} > 0 )); then
    scancel "${job_ids[@]}"
fi

echo "FOM test $test_dir finished with status $failure"
