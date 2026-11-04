# Compare results only after every ALF run has finished successfully.
#
# FIXME: use directories inside OUTPUT_ROOT instead of MANIFEST.
#
# Concentions:
#   MANIFEST         = $OUTPUT_ROOT/FOM_manifest.tsv
#   COMPARE_SCRIPT   = $BASE_DIR/compare_FOM.py
#   RESULTS_DIR      = $OUTPUT_ROOT/results
#   FIGURES_DIR      = $OUTPUT_ROOT/figures

echo 'FIXME: This script needs work before running.'
exit 1

readonly BASE_DIR=$(dirname $(realpath "$0"))
readonly OUTPUT_ROOT="$BASE_DIR/FOM_runs"
readonly MANIFEST="$OUTPUT_ROOT/FOM_manifest.tsv"
readonly COMPARE_SCRIPT="$BASE_DIR/compare_FOM.py"
readonly RESULTS_DIR="$OUTPUT_ROOT/results"
readonly FIGURES_DIR="$OUTPUT_ROOT/figures"
readonly ENVIRONMENT_SCRIPT="${ENVIRONMENT_SCRIPT:-/lustre/orion/world-shared/csc728/messerlyra/scripts/load_caar_env.bash}"

mkdir -p "$RESULTS_DIR" "$FIGURES_DIR"

echo "Starting FOM comparison..."
comparison_log="$RESULTS_DIR/FOM_comparison.log"
for test_dir in $OUTPUT_ROOT/nodes_*; do
	test_name=$(basename $test_dir)
	parse
    node_counts=()
    while IFS=$'\t' read -r test_name nnodes_md nnodes_qm nnodes_ml; do
        node_counts+=("$nnodes_md")
    done < "$MANIFEST"

    (
        # shellcheck disable=SC1090
        source "$ENVIRONMENT_SCRIPT" || exit 1
        export PYTHONPATH="$BASE_DIR/../src:$PYTHONPATH"
        python -u "$COMPARE_SCRIPT" --alf_path "$OUTPUT_ROOT" --nodes "${node_counts[@]}" \
            --results-dir "$RESULTS_DIR" --figures-dir "$FIGURES_DIR"
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
