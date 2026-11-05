#!/usr/bin/env bash
set -euo pipefail

NODE_MAX_MD=-1
NODE_MAX_QM=64
NODE_MAX_ML=1
readonly GPUS_PER_NODE=8

# Resolve paths before entering any ALF test directory.
readonly BASE_DIR=$(dirname $(realpath "${BASH_SOURCE[0]}"))
readonly OUTPUT_ABS="$BASE_DIR/FOM_runs"
readonly TEMPLATE_DIR="$BASE_DIR/FOM_template"
readonly MASTER_TEMPLATE="master_template.json"
readonly H5_PRECOMPUTED_DIR="h5store_precomputed"

for path in "$TEMPLATE_DIR/$MASTER_TEMPLATE"; do
    if [[ ! -f "$path" ]]; then
        echo "Error: required file not found: $path" >&2
        exit 1
    fi
done

if [ $# -ne 1 ]; then
    echo "Usage: $0 <node_count>" >&2
    exit 1
fi
nodes="$1"

for limit in "$NODE_MAX_MD" "$NODE_MAX_QM" "$NODE_MAX_ML"; do
    if [[ ! "$limit" =~ ^-?[0-9]+$ ]] || (( limit == 0 || limit < -1 )); then
        echo "Error: node limits must be positive integers or -1." >&2
        exit 1
    fi
done

# Prepare configurations and precomputed HDF5 copies for this test.
if true; then
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

    sed -e "s/NNODES_QM/${nnodes_qm}/g" \
        -e "s/NNODES_MD/${nnodes_md}/g" \
        -e "s/NNODES_ML/${nnodes_ml}/g" \
        -e "s/NNODES/${nnodes_md}/g" \
        -e "s/NCONFIGS_QM_MINUS_ONE/$((nconfigs_qm - 1))/g" \
        -e "s/NCONFIGS_QM_PLUS_ONE/$((nconfigs_qm + 1))/g" \
        -e "s/NCONFIGS_QM/${nconfigs_qm}/g" \
        -e "s/NCONFIGS_MD_MINUS_ONE/$((nconfigs_md - 1))/g" \
        -e "s/NCONFIGS_MD_PLUS_ONE/$((nconfigs_md + 1))/g" \
        -e "s/NCONFIGS_MD/${nconfigs_md}/g" \
        "$test_dir/$MASTER_TEMPLATE" >"$test_dir/master_config.json"

    mkdir -p "$test_dir/h5store"
    for ((h5_index = 0; h5_index < h5_copies; h5_index++)); do
        printf -v h5_name 'data-%sconfigs-copy-%04d.h5' "$nconfigs_qm" "$h5_index"
        cp "$H5_PRECOMPUTED_DIR/$h5_precomputed_file" "$test_dir/h5store/$h5_name"
    done

    echo "Prepared $test_name: MD=$nconfigs_md, QM/batch=$nconfigs_qm, QM batches=$qm_batches, HDF5 copies=$h5_copies"
fi
