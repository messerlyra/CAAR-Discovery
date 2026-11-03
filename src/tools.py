from parsl.app.errors import RemoteExceptionWrapper
from custom_builders import atomic_system_task
from alframework.tools.tools import store_current_data
import h5py
from ase import Atoms
from alframework.tools.molecules_class import MoleculesObject

def run_parsl(parsl_func, *args, **kwargs):
    """
    Runs the inner function of a Parsl python_app and handles the result.
    
    Args:
        parsl_func: The Parsl decorated function (PythonApp).
        *args: Positional arguments for the inner function.
        **kwargs: Keyword arguments for the inner function.
        
    Returns:
        The return value of the inner function.
        
    Raises:
        The exception raised by the inner function if it fails.
    """
    # Access the original function via .func
    inner_func = parsl_func.func
    
    try:
        result = inner_func(*args, **kwargs)
        
        # Parsl's .func might still return a RemoteExceptionWrapper 
        # if the execution was wrapped in a way that captures exceptions.
        if isinstance(result, RemoteExceptionWrapper):
            raise result.get_exception()
            
        return result
    except Exception as e:
        # If the result was already a RemoteExceptionWrapper, it's handled above.
        # If the inner_func raised an exception directly, we raise it here.
        if isinstance(e, RemoteExceptionWrapper):
            raise e.get_exception()
        raise e

def build_molecule(moleculeid, builder_config):
    """
    Builds a molecule using the atomic_system_task.
    """
    return run_parsl(
        atomic_system_task,
        moleculeid=moleculeid,
        atom_charges=builder_config['atom_charges'],
        target_num_atoms=builder_config['target_num_atoms'],
        min_distance=builder_config['min_distance'],
        density_range=builder_config['density_range']
    )

def load_molecules_from_h5(h5_path):
    """
    Loads molecules from an HDF5 file.
    """
    molecules = []
    def extract_mols(data):
        # ['_id', 'cell', 'coordinates', 'energy', 'forces', 'species']
        cell = data['cell'][:]
        positions = data['coordinates'][:]
        species = data['species'][:]
        symbols = [x.decode('utf-8') for x in species]
        for i in range(len(cell)):
            atoms = Atoms(symbols=symbols, positions=positions[i], cell=cell[i], pbc=True)
            mol_id = f"{len(molecules)}"
            molecules.append( MoleculesObject(atoms, mol_id) )

    with h5py.File(h5_path, 'r') as f:
        for group_name in f.keys():
            group = f[group_name]
            if 'cell' in group.keys():
                extract_mols(group)
            else:
                for mol_id in group.keys():
                    extract_mols(group[mol_id])
                    
    return molecules

def save_molecules_to_h5(h5_path, molecules, properties_list):
    """
    Saves a list of MoleculesObject to an HDF5 file using alframework's store_current_data.
    """
    # store_current_data expects a list of results (usually from a queue)
    # and a properties list.
    store_current_data(h5_path, molecules, properties_list)
