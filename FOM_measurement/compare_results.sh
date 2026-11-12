# Compare results only after every ALF run has finished successfully.
#
set -euo pipefail

readonly BASE_DIR=$(dirname $(realpath "$0"))
readonly OUTPUT_ROOT="$BASE_DIR/FOM_runs"
readonly RESULTS_DIR="$OUTPUT_ROOT/results"
readonly FIGURES_DIR="$OUTPUT_ROOT/figures"

readonly ENVIRONMENT_SCRIPT="${ENVIRONMENT_SCRIPT:-/lustre/orion/world-shared/csc728/messerlyra/scripts/load_caar_env.bash}"

source "$ENVIRONMENT_SCRIPT" || exit 1
export PYTHONPATH="$BASE_DIR/../src:$PYTHONPATH"

mkdir -p "$RESULTS_DIR" "$FIGURES_DIR"

comparison_log="$RESULTS_DIR/FOM_comparison.log"
echo "Starting FOM comparison..." | tee "$comparison_log"
for test_dir in $OUTPUT_ROOT/nodes_*; do
	test_name=$(basename "$test_dir")
	echo "# Analyzing $test_name" | tee -a "$comparison_log"

	[ -s "$RESULTS_DIR/$test_name.txt" ] \
	  || ( python3 "$BASE_DIR/analyze_FOM.py" --alf_path "$test_dir" | tee "$RESULTS_DIR/$test_name.txt" ) \
	  || (echo "Error analyzing $test_dir" | tee -a "$comparison_log")
	[ -s "$RESULTS_DIR/$test_name.txt" ] || rm "$RESULTS_DIR/$test_name.txt"
	echo | tee -a "$comparison_log"
done

python3 calculate_results.py
python3 plot_results.py

#node_counts=($test_name $nnodes_md $nnodes_qm $nnodes_ml)
#python -u "$BASE_DIR/compare_FOM.py" --alf_path "$OUTPUT_ROOT" --nodes "${node_counts[@]}" \
#	--results-dir "$RESULTS_DIR" --figures-dir "$FIGURES_DIR" | tee -a $comparison_log
