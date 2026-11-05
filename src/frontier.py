import os
import parsl
from parsl.config import Config
from parsl.executors import HighThroughputExecutor
from parsl.addresses import address_by_interface

# For IC/NERSC:
from parsl.providers import SlurmProvider
from parsl.launchers import SrunLauncher
from parsl.launchers import SingleNodeLauncher
from parsl.launchers import SimpleLauncher

def get_env_int(key, default):
    return int(os.getenv(key, default))

def get_env_str(key, default):
    return os.getenv(key, default)

# Dynamic values from environment variables
NNODES_MD = get_env_int('NNODES_MD', 1)
NNODES_QM = get_env_int('NNODES_QM', 1)
NNODES_ML = get_env_int('NNODES_ML', 1)
NCONFIGS_MD = NNODES_MD * 8
NCONFIGS_QM = NNODES_QM * 8

WALLTIME_MD = get_env_str('WALLTIME_MD', '0:15:00')
WALLTIME_QM = get_env_str('WALLTIME_QM', '0:30:00')
WALLTIME_ML = get_env_str('WALLTIME_ML', '0:15:00')

print(f"NNODES_MD = {NNODES_MD}")
print(f"NNODES_QM = {NNODES_QM}")
print(f"NNODES_ML = {NNODES_ML}")
print(f"WALLTIME_MD = {WALLTIME_MD}")
print(f"WALLTIME_QM = {WALLTIME_QM}")
print(f"WALLTIME_ML = {WALLTIME_ML}")

shared_opts = "-p batch -A csc728"
debug_opts  = "-q debug -p batch -A csc728"

config_standard = Config(
    executors=[
        HighThroughputExecutor(
            label='alf_QM_executor',
            max_workers_per_node=1,
            provider=SlurmProvider(
                init_blocks=0,
                min_blocks=0,
                max_blocks=1,
                scheduler_options=f'#SBATCH --nodes={NNODES_QM} --ntasks-per-node=8 -J QM_{NNODES_QM}nodes {shared_opts}',
                launcher=SrunLauncher(overrides=f'--ntasks {NCONFIGS_QM} -c 7 --gpus-per-task=1 --gpu-bind=closest'),
                walltime=WALLTIME_QM,
                cmd_timeout=30,
            ),
        ),
        HighThroughputExecutor(
            label='alf_ML_executor',
            provider=SlurmProvider(
                init_blocks=0,
                min_blocks=0,
                max_blocks=1,
                nodes_per_block=1,
                scheduler_options=f'#SBATCH --nodes={NNODES_ML} --ntasks-per-node=1 -J ML_{NNODES_ML}nodes {shared_opts}',
                launcher=SrunLauncher(overrides=f'--ntasks 1 -c 56 --gpus-per-task=8 --gpu-bind=closest'),
                walltime=WALLTIME_ML,
                cmd_timeout=30,
            ),
        ),
        HighThroughputExecutor(
            label='alf_sampler_executor',
            max_workers_per_node=1,
            provider=SlurmProvider(
                init_blocks=0,
                min_blocks=0,
                max_blocks=1,
                scheduler_options=f'#SBATCH --nodes={NNODES_MD} --ntasks-per-node=8 -J MD_{NNODES_MD}nodes {shared_opts}',
                launcher=SrunLauncher(overrides=f'--ntasks {NCONFIGS_MD} -c 7 --gpus-per-task=1 --gpu-bind=closest'),
                walltime=WALLTIME_MD,
                cmd_timeout=30,
            ),
        )
    ]
)

config_debug = Config(
    executors=[
        HighThroughputExecutor(
            label='alf_QM_executor',
            provider=SlurmProvider(
                init_blocks=0,
                min_blocks=0,
                max_blocks=1,
                nodes_per_block=1,
                scheduler_options=f'#SBATCH --nodes=1 --ntasks-per-node=1 -J QM_debug {debug_opts}',
                launcher=SimpleLauncher(),
                walltime='0:10:00',
                cmd_timeout=5,
            ),
        ),
        HighThroughputExecutor(
            label='alf_ML_executor',
            provider=SlurmProvider(
                init_blocks=0,
                min_blocks=0,
                max_blocks=1,
                nodes_per_block=1,
                scheduler_options=f'#SBATCH --nodes=1 -J ML_debug {debug_opts}',
                launcher=SingleNodeLauncher(),
                walltime='0:05:00',
                cmd_timeout=5,
            ),
        ),
        HighThroughputExecutor(
            label='alf_sampler_executor',
            provider=SlurmProvider(
                init_blocks=0,
                min_blocks=0,
                max_blocks=1,
                nodes_per_block=1,
                scheduler_options=f'#SBATCH --nodes=1 -J MD_debug {debug_opts}',
                launcher=SingleNodeLauncher(),
                walltime='0:01:00',
                cmd_timeout=5,
            ),
        )
    ]
)
