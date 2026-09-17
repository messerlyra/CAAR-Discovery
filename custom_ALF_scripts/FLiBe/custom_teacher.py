import os
import json
import pickle
import re
import parsl
from parsl import python_app, bash_app

import os
import ase
from ase import Atoms
from ase import units

from alframework.tools.tools import load_module_from_config
from alframework.tools.molecules_class import MoleculesObject

from hippynn.experiment.serialization import load_checkpoint_from_cwd
from hippynn.tools import active_directory
from hippynn.interfaces.ase_interface import HippynnCalculator

from hippynn.graphs.ensemble import make_ensemble
import torch

import time

@python_app(executors=['alf_QM_executor'])
def hippynn_calculator_task(molecule_object,QM_config,QM_scratch_dir,properties_list):

    assert isinstance(molecule_object, MoleculesObject), 'molecule_object must be an instance of MoleculesObject'

    directory = QM_scratch_dir + '/' + molecule_object.get_moleculeid()
    properties = list(properties_list.keys())
    atoms = molecule_object.get_atoms()
    
    if os.path.isdir(directory):
        raise RuntimeError('Scratch directory exists: ' + directory)
    else:
       os.makedirs(directory)
     
    use_ensemble = QM_config["use_ensemble"]
    energy_name = QM_config["energy_name"]
    force_name = QM_config["force_name"]
    
    calc_start_time = time.time()

    if use_ensemble:

        ensemble_path = QM_config["ensemble_path"]
        energy_name = "ensemble_"+energy_name
        force_name = "ensemble_"+force_name

        model_form = ensemble_path+'*'
        ensemble_graph, ensemble_info = make_ensemble(model_form)

        # Retrieve the ensemble node which has just been created.
        # The name will be the prefix 'ensemble' followed by the db_name from the ensemble members.
        ensemble_energy = ensemble_graph.node_from_name(energy_name)
        ensemble_force = ensemble_graph.node_from_name(force_name)

        # The ensemble node has `mean`, `std`, and `all` outputs.
        energy_node = ensemble_energy.mean
        calc = HippynnCalculator(energy=energy_node, en_unit=units.eV)

        #extra_properties = {"ens_predictions": ensemble_energy.all, "ens_std": ensemble_energy.std, "force_std":ensemble_force.std}
        #calc = HippynnCalculator(energy=energy_node, extra_properties=extra_properties)
    
    else:
    
        model_path = QM_config["model_path"] 

        with active_directory(model_path, create=False):
            bundle = load_checkpoint_from_cwd(map_location='cpu')
        model = bundle["training_modules"].model
    
        energy_node = model.node_from_name(energy_name)
        calc = HippynnCalculator(energy_node, en_unit=units.eV)
    
    #calc.to(torch.float64)
    #if torch.cuda.is_available():
    #    calc.to(torch.device("cuda"))
        
    calc.to(torch.device("cuda"))

    mol = atoms.copy() ###RAM: It appears that without .copy() this has pickling problems
    mol.calc = calc
    energy = mol.get_potential_energy()
    forces = mol.get_forces()

    calc_end_time = time.time()
    calc_time = calc_end_time - calc_start_time 
    
    free_energy = energy
    return_results = {}
    return_results['energy'] = energy
    return_results['free_energy'] = free_energy
    return_results['forces'] = forces

    file = open(directory+'/output.txt','w')
    file.write("Cell (A)"+'\n')
    file.write(str(atoms.get_cell())+'\n')
    file.write("Elements: "+'\n')
    file.write(str(atoms.get_chemical_formula())+'\n')
    file.write("Coordinates (A)"+'\n')
    file.write(str(atoms.get_positions())+'\n')
    file.write('Energy (eV): '+str(energy)+'\n')
    file.write("Forces (eV/A): "+"\n")
    file.write(str(forces)+'\n')
    file.write('Converged'+'\n')
    file.write("Run time (s): "+str(calc_time))
    file.close()
    
    molecule_object.store_results(return_results)
    molecule_object.set_converged_flag(True)

    return molecule_object
    

