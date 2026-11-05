# Run this script as: python run_teacher.py
import os, sys; sys.path.append(os.path.dirname(os.path.abspath(__file__)))
#
# This script performs a simple labeling (teacher) task using ALF.
# It loads molecules from an HDF5 file, labels them, and saves the results.

import json
import os
import sys
from ase import Atoms
from alframework.tools.molecules_class import MoleculesObject
from custom_teacher import hippynn_calculator_task, Rootstock_calculator_task
from tools import run_parsl, load_molecules_from_h5, save_molecules_to_h5

def main():
    # Load config
    with open('master_config.json', 'r') as f:
        master_config = json.load(f)
    with open('teacher_config.json', 'r') as f:
        qm_config = json.load(f)

    # Load molecules from the demo HDF5 store
    h5_src = 'h5store/example.h5'
    h5_dst = 'labeled_molecules.h5'
    if os.path.exists(h5_dst):
        raise FileExistsError(f"refusing to overwrite existing {h5_dst}")

    print(f"Loading molecules from {h5_src}...")
    molecules = load_molecules_from_h5(h5_src)
    print(f"Loaded {len(molecules)} molecules.")

    # Parameters
    qm_scratch_dir = master_config.get("QM_scratch_dir", "qm_scratch")
    properties_list = master_config["properties_list"]

    # Ensure scratch dir is clean for the demo
    if os.path.exists(qm_scratch_dir):
        import shutil
        shutil.rmtree(qm_scratch_dir)
        os.makedirs(qm_scratch_dir, exist_ok=True)

    labeled_molecules = []

    # Run labeling on all molecules
    for i, mol in enumerate(molecules):
        print(f"Labeling molecule {i+1}/{len(molecules)}: {mol.get_moleculeid()}...")
        try:
            result = run_parsl(
                Rootstock_calculator_task,
                #hippynn_calculator_task,
                molecule_object=mol,
                QM_config=qm_config,
                QM_scratch_dir=qm_scratch_dir,
                properties_list=properties_list
            )
            labeled_molecules.append(result)
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"Failed to label {mol.get_moleculeid()}: {e}")
            sys.exit(1)

    # Save results back to HDF5
    print(f"Saving {len(labeled_molecules)} labeled molecules to {h5_dst}...")
    save_molecules_to_h5(h5_dst, labeled_molecules, properties_list)
    print("Done.")

if __name__ == "__main__":
    main()
