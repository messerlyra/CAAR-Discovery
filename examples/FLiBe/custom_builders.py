# The builder code goes here
import glob
import random
import os
import numpy as np
from parsl import python_app, bash_app
import json

import ase
from ase import Atoms
from ase import neighborlist
from ase.geometry.cell import complete_cell
from ase.io import read, write

from alframework.tools.tools import random_rotation_matrix
from alframework.tools.tools import build_input_dict
from alframework.tools.molecules_class import MoleculesObject
import random
from copy import deepcopy

from alframework.builders.builders import create_atomic_system, construct_simulation_box, atomic_system_builder
from ase.data import atomic_masses, atomic_numbers

from collections import Counter
from ase.data import atomic_masses, atomic_numbers
from itertools import product

def create_atomic_system_FLiBe(target_num_atoms):
    """
    Create FLiBe with a 2:1 LiF:BeF2 ratio, i.e. Li2BeF4.

    One formula unit contains:
        2 Li
        1 Be
        4 F

    Total = 7 atoms per formula unit.
    """

    atoms_per_formula_unit = 7

    # Find closest integer number of Li2BeF4 formula units
    n_formula_units = round(target_num_atoms / atoms_per_formula_unit)

    atomic_system = {
        "Li": 2 * n_formula_units,
        "Be": 1 * n_formula_units,
        "F":  4 * n_formula_units,
    }

    return atomic_system

def atomic_system_builder_FLiBe(atom_charges, target_num_atoms, min_distance, density, max_tries=25, scale_coords=False):
    """Builds the atomic system

    Args:
        atom_charges (dict): A dictionary where the keys are the atom types in the system and the corresponding values
                             the charge of each atom type.
        target_num_atoms (int): Targeted total number of atoms in the system.
        min_distance (float): Minimum absolute distance between any two atoms [Angstroms].
        density (float): Density of the box [g/cm3]
        max_tries (int): Maximum number of cycles in the atom placing algorithm
        scale_coords (bool): Determines whether to scale the coordinates by the box length or not.

    Returns:
        (ase.Atoms): ASE atoms object representing a random configuration of the atomic system.

    """
    atomic_system = create_atomic_system_FLiBe(target_num_atoms)
    
    mass_system = sum([atomic_masses[atomic_numbers[atom_type]] * n_atoms / 6.022e23
                           for atom_type, n_atoms in atomic_system.items()]) # [g]
    box_volume = (mass_system / density * 1e24) # [Angstrom^3]
    box_length = box_volume ** (1/3) # [Angstrom]
 
#    coords = construct_simulation_box(atomic_system, min_distance, box_length, max_tries=max_tries, scale_coords=scale_coords)
    coords = construct_simulation_box(atomic_system, min_distance, density=density, max_tries=max_tries, scale_coords=scale_coords)

    atoms_type_list = []
    for k, v in atomic_system.items():
        atoms_type_list.extend([k] * v)

    return ase.Atoms(atoms_type_list, coords, pbc=True, cell=np.diag([box_length]*3))

@python_app(executors=['alf_sampler_executor'])
def atomic_system_task(moleculeid, atom_charges, target_num_atoms, min_distance, density_range):
    """Atomic system task that will be fed to the sampler.

    Args:
        moleculeid (str): Unique identifier of the atomic system in the database.
        atom_charges (dict): A dictionary where the keys are the atom types in the system and the corresponding
                             values are the charge of each atom type.
        target_num_atoms (int): Targeted total number of atoms in the system.
        min_distance (float): Minimum absolute distance between any two atoms [Angstroms].
        density_range (list): A list containing the minimum and maximum simulation box density [g/cm3].

    Returns:
        (MoleculesObject): A MoleculesObject representing the system.

    """
    rng = np.random.default_rng()
    density = rng.uniform(min(density_range), max(density_range))    

    ase_atoms = atomic_system_builder_FLiBe(atom_charges, target_num_atoms, min_distance, density)

    return MoleculesObject(ase_atoms, moleculeid)
