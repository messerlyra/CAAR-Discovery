
show() {
  echo "nnodes_md=$1"
  echo "nnodes_qm=$2"
  echo "nnodes_ml=$3"
}

test_name="a/b/c/nodes_4MD_5QM_6ML"
read -a nodes < <(python3 -c "import re, sys; m = re.search(r'nodes_(\d+)MD_(\d+)QM_(\d+)ML', sys.argv[1]); print(*(m.groups())) if m else sys.exit(1)" "$test_name")

echo "nodes=${nodes[*]}"
echo "nnodes_md=${nodes[0]}"
show ${nodes[*]}
