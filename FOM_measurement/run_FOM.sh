#!/usr/bin/env bash
set -euo pipefail

# MD node counts and per-stage node limits (-1 means no additional limit).
NODE_COUNTS=(1 2 4 8)
NODE_MAX_MD=-1
NODE_MAX_QM=64
NODE_MAX_ML=1
readonly GPUS_PER_NODE=8

PARALLEL=0
if [[ $# -gt 1 || ( $# -eq 1 && "$1" != "--parallel" ) ]]; then
    echo "Usage: $0 [--parallel]" >&2
    exit 1
fi
if [[ $# -eq 1 ]]; then PARALLEL=1; fi

readonly TEMPLATE_DIR="FOM_template"
readonly OUTPUT_ROOT="FOM_runs"
readonly ENVIRONMENT_SCRIPT="/lustre/orion/world-shared/csc728/messerlyra/scripts/load_caar_env.bash"
readonly TMUX_SESSION="alf_FOM"
readonly MASTER_TEMPLATE="master_template.json"
readonly MASTER_CONFIG="master_FOM.json"
readonly H5_PRECOMPUTED_DIR="h5store_precomputed"

for path in "$TEMPLATE_DIR/$MASTER_TEMPLATE" "$ENVIRONMENT_SCRIPT"; do
    if [[ ! -f "$path" ]]; then
        echo "Error: required file not found: $path" >&2
        exit 1
    fi
done
if ! command -v tmux >/dev/null 2>&1; then
    echo "Error: tmux is not available." >&2
    exit 1
fi
if [[ ${#NODE_COUNTS[@]} -eq 0 ]]; then
    echo "Error: NODE_COUNTS is empty." >&2
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

# Resolve paths before entering any ALF test directory.
readonly BASE_DIR="$PWD"
mkdir -p "$OUTPUT_ROOT"
readonly OUTPUT_ABS="$BASE_DIR/$OUTPUT_ROOT"
readonly RESULTS_DIR="$OUTPUT_ABS/results"
readonly FIGURES_DIR="$OUTPUT_ABS/figures"
mkdir -p "$RESULTS_DIR" "$FIGURES_DIR"
readonly MANIFEST="$OUTPUT_ABS/FOM_manifest.tsv"
readonly RUNNER="$OUTPUT_ABS/run_FOM_worker.sh"
readonly COMPARE_SCRIPT="$BASE_DIR/compare_FOM.py"
if [[ ! -f "$COMPARE_SCRIPT" ]]; then
    echo "Error: comparison script not found: $COMPARE_SCRIPT" >&2
    exit 1
fi
: > "$MANIFEST"

# Prepare configurations and precomputed HDF5 copies for every test.
for nodes in "${NODE_COUNTS[@]}"; do
    if [[ ! "$nodes" =~ ^[1-9][0-9]*$ ]]; then
        echo "Error: invalid node count: $nodes" >&2
        exit 1
    fi

    nnodes_md=$nodes
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
    h5_precomputed_file="data-${nconfigs_qm}configs.h5"
    if (( h5_copies > 0 )) && [[ ! -f "$H5_PRECOMPUTED_DIR/$h5_precomputed_file" ]]; then
        echo "Error: missing precomputed HDF5 file: $H5_PRECOMPUTED_DIR/$h5_precomputed_file" >&2
        exit 1
    fi

    test_name="nodes_${nnodes_md}MD_${nnodes_qm}QM_${nnodes_ml}ML"
    test_dir="$OUTPUT_ABS/$test_name"
    mkdir -p "$test_dir"
    cp -a "$TEMPLATE_DIR/." "$test_dir/"
    mv -f "$test_dir/$MASTER_TEMPLATE" "$test_dir/$MASTER_CONFIG"

    sed -i \
        -e "s/NNODES_QM/${nnodes_qm}/g" \
        -e "s/NNODES_MD/${nnodes_md}/g" \
        -e "s/NNODES_ML/${nnodes_ml}/g" \
        -e "s/NNODES/${nnodes_md}/g" \
        -e "s/NCONFIGS_QM_MINUS_ONE/$((nconfigs_qm - 1))/g" \
        -e "s/NCONFIGS_QM_PLUS_ONE/$((nconfigs_qm + 1))/g" \
        -e "s/NCONFIGS_QM/${nconfigs_qm}/g" \
        -e "s/NCONFIGS_MD_MINUS_ONE/$((nconfigs_md - 1))/g" \
        -e "s/NCONFIGS_MD_PLUS_ONE/$((nconfigs_md + 1))/g" \
        -e "s/NCONFIGS_MD/${nconfigs_md}/g" \
        "$test_dir/$MASTER_CONFIG"

    mkdir -p "$test_dir/h5store"
    for ((h5_index = 0; h5_index < h5_copies; h5_index++)); do
        printf -v h5_name 'data-%sconfigs-copy-%04d.h5' "$nconfigs_qm" "$h5_index"
        cp "$H5_PRECOMPUTED_DIR/$h5_precomputed_file" "$test_dir/h5store/$h5_name"
    done

    printf '%s\t%s\t%s\t%s\n' "$test_name" "$nnodes_md" "$nnodes_qm" "$nnodes_ml" >> "$MANIFEST"
    echo "Prepared $test_name: MD=$nconfigs_md, QM/batch=$nconfigs_qm, QM batches=$qm_batches, HDF5 copies=$h5_copies"
done

# Keep the tmux command short and reuse the prepared resource manifest.
cat > "$RUNNER" <<'WORKER'
#!/usr/bin/env bash
set -uo pipefail
manifest=$1
output_root=$2
environment_script=$3
parallel=$4
compare_script=$5
results_dir=$6
figures_dir=$7

run_one() {
    local test_name=$1 nnodes_md=$2 nnodes_qm=$3 nnodes_ml=$4
    local test_dir="$output_root/$test_name"
    local log_path="$test_dir/alf_FOM_${test_name}.log"

    export NNODES_MD=$nnodes_md
    export NNODES_QM=$nnodes_qm
    export NNODES_ML=$nnodes_ml

    (
        cd "$test_dir" || exit 1
        source "$environment_script" || exit 1
        export PYTHONPATH="/lustre/orion/csc728/proj-shared/rogersdd/CAAR-Discovery/src:$PYTHONPATH"
        export FOM_NODE_COUNT="$nnodes_md"
        echo "Starting FOM test: $nnodes_md MD node(s), $nnodes_qm QM node(s), $nnodes_ml ML node(s) at $(date -Is)"
        python -u -m alframework --master master_FOM.json
        status=$?
        echo "ALF exit code: $status"
        exit "$status"
    ) > "$log_path" 2>&1
    return $?
}

failure=0
if (( parallel )); then
    pids=()
    while IFS=$'\t' read -r test_name nnodes_md nnodes_qm nnodes_ml; do
        run_one "$test_name" "$nnodes_md" "$nnodes_qm" "$nnodes_ml" &
        pids+=("$!")
    done < "$manifest"
    for pid in "${pids[@]}"; do
        wait "$pid" || failure=1
    done
else
    while IFS=$'\t' read -r test_name nnodes_md nnodes_qm nnodes_ml; do
        run_one "$test_name" "$nnodes_md" "$nnodes_qm" "$nnodes_ml" || failure=1
        # Preserve cleanup of leftover ML Slurm jobs after sequential tests.
        job_name="ML_${nnodes_md}nodes"
        mapfile -t job_ids < <(squeue -h -u $USER -n "$job_name" -o '%A')
        if (( ${#job_ids[@]} > 0 )); then
            scancel "${job_ids[@]}"
        fi
        sleep 2
        if (( failure != 0 )); then break; fi
    done < "$manifest"
fi
printf 'FOM tests finished with status %s\n' "$failure"

# Compare results only after every ALF run has finished successfully.
comparison_log="$results_dir/FOM_comparison.log"
if (( failure == 0 )); then
    echo "All ALF tests completed successfully. Starting FOM comparison..."
    node_counts=()
    while IFS=$'\t' read -r test_name nnodes_md nnodes_qm nnodes_ml; do
        node_counts+=("$nnodes_md")
    done < "$manifest"

    (
        source "$environment_script" || exit 1
        export PYTHONPATH="/lustre/orion/csc728/proj-shared/rogersdd/CAAR-Discovery/src:$PYTHONPATH"
        python -u "$compare_script" --alf_path "$output_root" --nodes "${node_counts[@]}" \
            --results-dir "$results_dir" --figures-dir "$figures_dir"
    ) > "$comparison_log" 2>&1
    analysis_status=$?
    if (( analysis_status != 0 )); then
        echo "ERROR: FOM comparison failed (exit code $analysis_status). See: $comparison_log"
        failure=$analysis_status
    else
        echo "FOM comparison completed successfully. See: $comparison_log"
    fi
else
    echo "WARNING: One or more ALF tests failed. Skipping FOM comparison."
fi
printf 'Final FOM workflow status: %s\n' "$failure"
exec bash --noprofile --norc
WORKER
chmod +x "$RUNNER"

printf -v tmux_command '%q ' \
    "$RUNNER" \
    "$MANIFEST" \
    "$OUTPUT_ABS" \
    "$ENVIRONMENT_SCRIPT" \
    "$PARALLEL" \
    "$COMPARE_SCRIPT" \
    "$RESULTS_DIR" \
    "$FIGURES_DIR"
tmux new-session -d -s "$TMUX_SESSION" -n "FOM_tests"
tmux send-keys -t "$TMUX_SESSION:FOM_tests" "$tmux_command" C-m
if (( PARALLEL )); then run_mode=parallel; else run_mode=sequential; fi
echo "Started ${#NODE_COUNTS[@]} $run_mode FOM tests in tmux session: $TMUX_SESSION"
echo "Attach with: tmux attach -t $TMUX_SESSION"
echo "Logs are stored inside each test directory under: $OUTPUT_ROOT"
echo "Comparison results: $RESULTS_DIR"
echo "Figures: $FIGURES_DIR"
