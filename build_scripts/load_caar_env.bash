module load PrgEnv-gnu/8.6.0
module load miniforge3/23.11.0-0
module load rocm/6.2.4
module load craype-accel-amd-gfx90a

module load PrgEnv-cray
module load cray-mpich

conda config --set solver classic
packname=caar_env
packpath=/lustre/orion/csc728/world-shared/messerlyra/envs/${packname}

source activate ${packpath}

export PYTHONPATH="$packpath-packages/ALF-CAAR/:$PYTHONPATH"
