#!/usr/bin/env bash
set -euo pipefail

# MD node counts and per-stage node limits (-1 means no additional limit).
NODE_MAX_MD=-1
NODE_MAX_QM=64
NODE_MAX_ML=1
readonly GPUS_PER_NODE=8

if [[ $# -ne 1 ]]; then
    echo "Usage: $0 <node count>" >&2
    exit 1
fi
NODE_COUNT="$1"

readonly TEMPLATE_DIR="FOM_template"
readonly OUTPUT_ROOT="FOM_runs"
readonly ENVIRONMENT_SCRIPT="/lustre/orion/world-shared/csc728/messerlyra/scripts/load_caar_env.bash"
readonly TMUX_SESSION="alf-FOM-$NODE_COUNT"

if ! command -v tmux >/dev/null 2>&1; then
    echo "Error: tmux is not available." >&2
    exit 1
fi
if [[ ! "$NODE_COUNT" =~ ^[1-9][0-9]*$ ]]; then
    echo "Error: invalid node count: $NODE_COUNT" >&2
    exit 1
fi
for limit in "$NODE_MAX_MD" "$NODE_MAX_QM" "$NODE_MAX_ML"; do
    if [[ ! "$limit" =~ ^-?[0-9]+$ ]] || (( limit == 0 || limit < -1 )); then
        echo "Error: node limits must be positive integers or -1." >&2
        exit 1
    fi
done
if tmux has-session -t "$TMUX_SESSION" 2>/dev/null; then
    echo "Error: tmux session already exists: $TMUX_SESSION" >&2
    exit 1
fi

function ensure_directory() {
  for dname in "$@"; do
    if [ ! -d "$dname" ]; then
      echo "Directory '$dname' does not exist." >&2
      exit 1
    fi
  done
}

function ensure_present() {
  for fname in "$@"; do
    if [ ! -s "$fname" ]; then
      echo "File '$fname' does not exist." >&2
      exit 1
    fi
  done
}


# Resolve paths before entering any ALF test directory.
readonly BASE_DIR=$(dirname $(realpath "${BASH_SOURCE[0]}"))
readonly OUTPUT_ABS="$BASE_DIR/$OUTPUT_ROOT"
readonly RUNNER="$BASE_DIR/run_FOM_worker.sh"

# Ensure config files and precomputed HDF5 files are present.
if true; then
    nnodes_md=$NODE_COUNT
    if (( NODE_MAX_MD > 0 && nnodes_md > NODE_MAX_MD )); then
        nnodes_md=$NODE_MAX_MD
    fi
    nnodes_qm=$nnodes_md
    if (( NODE_MAX_QM > 0 && nnodes_qm > NODE_MAX_QM )); then
        nnodes_qm=$NODE_MAX_QM
    fi
    nnodes_ml=$nnodes_md
    if (( NODE_MAX_ML > 0 && nnodes_ml > NODE_MAX_ML )); then
        nnodes_ml=$NODE_MAX_ML
    fi

    nconfigs_md=$((nnodes_md * GPUS_PER_NODE))
    nconfigs_qm=$((nnodes_qm * GPUS_PER_NODE))
    if (( nconfigs_md % nconfigs_qm != 0 )); then
        echo "Error: MD configurations ($nconfigs_md) must be divisible by QM configurations ($nconfigs_qm)." >&2
        exit 1
    fi
    qm_batches=$((nconfigs_md / nconfigs_qm))
    h5_copies=$((qm_batches - 1))

    test_name="nodes_${nnodes_md}MD_${nnodes_qm}QM_${nnodes_ml}ML"
    test_dir="$OUTPUT_ABS/$test_name"
    ensure_present "$test_dir"/status_FOM.txt
    ensure_present "$test_dir"/{master,builder,sampler,teacher,training}_config.json
    ensure_directory "$test_dir"/{ensembles,h5store}

    for ((h5_index = 0; h5_index < h5_copies; h5_index++)); do
        printf -v h5_name 'data-%sconfigs-copy-%04d.h5' "$nconfigs_qm" "$h5_index"
        ensure_present "$test_dir/h5store/$h5_name"
    done
fi

if [ -d $test_dir/runinfo ]; then
    echo "$test_dir/runinfo exists - refusing to re-run." >&2
    exit 1
fi

# New convention: worker derives most paths from OUTPUT_ABS; only
# output_root and parallel flag are required.
echo "Starting tmux session: $TMUX_SESSION"
tmux new-session -d -s "$TMUX_SESSION" -n "FOM_tests"
echo "Spawning: $RUNNER $test_dir"
echo "ssh $(hostname) tmux attach -t $TMUX_SESSION" >$test_dir/tmux.info
tmux send-keys -t "$TMUX_SESSION:FOM_tests" "$RUNNER $test_dir" C-m
echo "Started $NODE_COUNT-node FOM test in $test_dir"
echo "Attach on $(hostname) with: tmux attach -t $TMUX_SESSION"
