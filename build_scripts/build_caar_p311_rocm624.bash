###Updated, 09/05/25
module load PrgEnv-gnu/8.6.0
module load miniforge3/23.11.0-0
module load rocm/6.2.4
module load craype-accel-amd-gfx90a

module load PrgEnv-cray
module load cray-mpich

###Can be a good idea
#conda clean -a -y

conda config --set solver classic
packname=caar_env
packpath=/lustre/orion/csc728/world-shared/messerlyra/envs/${packname}
conda create -y --prefix=${packpath} python=3.11 -c conda-forge

source activate ${packpath}
conda config --set solver classic

###RAM: I moved this above the installation of torch
conda install -y numpy pandas matplotlib scipy jupyter h5py tqdm
conda install -y numba python-graphviz cython scikit-learn spglib seekpath PyYAML wheel setuptools maggma pydantic -c conda-forge

###Updated, 09/05/25
pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/rocm6.2

pip install pyscf
pip install rdkit
pip install parsl

mkdir ${packpath}-packages
pushd ${packpath}-packages
mkdir ${packpath}/PythonPath
git clone https://github.com/bnebgen-LANL/ase.git
pip install -e ./ase
git clone https://github.com/messerlyra/hippynn-CAAR.git
pip install -e ./hippynn-CAAR

git clone https://github.com/messerlyra/ALF-CAAR.git
ln -s ${packpath}-packages/ALF-CAAR/alframework ${packpath}/PythonPath/alframework

pip install rootstock

