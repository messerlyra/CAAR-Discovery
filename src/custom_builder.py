# The builder code goes here
import glob
import random
import os
import numpy as np
from parsl import python_app, bash_app
from timing.timing_client import time_task
import json

import ase
from ase import Atoms
from ase import neighborlist
from ase.geometry.cell import complete_cell
from ase.io import cfg
from ase.io import read, write

from alframework.tools.tools import random_rotation_matrix
from alframework.tools.tools import build_input_dict
from alframework.tools.molecules_class import MoleculesObject
from copy import deepcopy

from alframework.builders.builders import create_atomic_system, construct_simulation_box, atomic_system_builder
from ase.data import atomic_masses, atomic_numbers
from itertools import combinations

def atom_charges_selector(atom_charges, max_elements=None, rng=None):
    """Select one valid element combination uniformly at random.

    Every subset containing at least one cation and one anion has the same
    probability. If ``max_elements`` is provided, only subsets with at most
    that many elements are considered.
    """
    if rng is None:
        rng = np.random.default_rng()

    cations = [element for element, charge in atom_charges.items() if charge > 0]
    anions = [element for element, charge in atom_charges.items() if charge < 0]

    if not cations:
        raise ValueError("atom_charges must contain at least one cation (positive charge).")
    if not anions:
        raise ValueError("atom_charges must contain at least one anion (negative charge).")
    if max_elements is not None:
        if not isinstance(max_elements, (int, np.integer)):
            raise TypeError("max_elements must be an integer or None.")
        if max_elements < 2:
            raise ValueError("max_elements must be at least 2.")
        if max_elements > len(atom_charges):
            raise ValueError(
                "max_elements cannot exceed the number of available elements."
            )

    elements = list(atom_charges)
    largest_allowed = len(elements) if max_elements is None else max_elements
    valid_combinations = [
        combination
        for size in range(2, largest_allowed + 1)
        for combination in combinations(elements, size)
        if any(element in cations for element in combination)
        and any(element in anions for element in combination)
    ]
    selected_elements = valid_combinations[
        int(rng.integers(0, len(valid_combinations)))
    ]
    return {
        element: atom_charges[element]
        for element in selected_elements
    }


def atomic_system_builder_alt(atom_charges, target_num_atoms, min_distance, density, max_tries=25, scale_coords=False):
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
    atomic_system = create_atomic_system(atom_charges, target_num_atoms)
    
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
@time_task("builder")
def atomic_system_task(moleculeid, atom_charges, target_num_atoms, min_distance, density_range, max_elements=None):
    """Atomic system task that will be fed to the sampler.

    Args:
        moleculeid (str): Unique identifier of the atomic system in the database.
        atom_charges (dict): A dictionary where the keys are the atom types in the system and the corresponding
                             values are the charge of each atom type.
        target_num_atoms (int): Targeted total number of atoms in the system.
        min_distance (float): Minimum absolute distance between any two atoms [Angstroms].
        density_range (list): A list containing the minimum and maximum simulation box density [g/cm3].
        max_elements (int, optional): Maximum number of elements to select for the system.

    Returns:
        (MoleculesObject): A MoleculesObject representing the system.

    """
    rng = np.random.default_rng()
    density = rng.uniform(min(density_range), max(density_range))    

    atoms_selected = atom_charges_selector(atom_charges, max_elements, rng)

    ase_atoms = atomic_system_builder_alt(atoms_selected, target_num_atoms, min_distance, density)

    return MoleculesObject(ase_atoms, moleculeid)
