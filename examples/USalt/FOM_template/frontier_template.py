import parsl
from parsl.config import Config
from parsl.executors import HighThroughputExecutor
from parsl.addresses import address_by_interface

# For IC/NERSC:
from parsl.providers import SlurmProvider
from parsl.launchers import SrunLauncher
from parsl.launchers import SingleNodeLauncher
from parsl.launchers import SimpleLauncher

import task_counts  # keep finished tasks in ALF status output

config_FOM = Config(
    executors=[
        HighThroughputExecutor(
            label='alf_QM_executor',
            #This executor is kinda strange. We manually increase the node count so that 
            #our parallel qm job gets multiple nodes, but leave nodes_per_block=1 so 
            #that parsl  doesn't assign multiple tasks

            max_workers_per_node=1, ###RAM: I don't understand why this is needed

            provider=SlurmProvider(
                init_blocks = 0,
                min_blocks = 0,
                max_blocks = 1,


                # string to prepend to #SBATCH blocks in the submit
                scheduler_options='#SBATCH --nodes=NNODES --ntasks-per-node=8 -p batch -J QM_NNODESnodes -A  csc728',

                # Command to be run before starting a worker
                #worker_init=

                # We request all hyperthreads on a node.
                launcher=SrunLauncher(overrides='--ntasks NCONFIGS -c 7 --gpus-per-task=1 --gpu-bind=closest'),

                walltime='0:20:00',

                # Slurm scheduler on Cori can be slow at times,
                # increase the command timeouts
                cmd_timeout=30,
            ),
        ),
        HighThroughputExecutor(
            label='alf_ML_executor',

            max_workers_per_node=1,

            provider=SlurmProvider(
                init_blocks = 0,
                min_blocks = 0,
                max_blocks = 1,

                nodes_per_block=1,

                # string to prepend to #SBATCH blocks in the submit
                scheduler_options='#SBATCH --nodes=1 --ntasks-per-node=1 -p batch -J ML_NNODESnodes -A csc728',

                # Command to be run before starting a worker
                #worker_init='export HIPPYNN_USE_CUSTOM_KERNELS=triton',

                # We request all hyperthreads on a node.
                #launcher=SrunLauncher(),
                launcher=SrunLauncher(overrides='--ntasks 1 -c 56 --gpus-per-task=8 --gpu-bind=closest'),
                walltime='0:05:00',

                # Slurm scheduler on Cori can be slow at times,
                # increase the command timeouts
                cmd_timeout=30,
            ),
        ),
        HighThroughputExecutor(
            label='alf_sampler_executor',

            max_workers_per_node=1, ###RAM: I don't understand why this is needed

            provider=SlurmProvider(
                init_blocks = 0,
                min_blocks = 0,
                max_blocks = 1,

                # string to prepend to #SBATCH blocks in the submit
                scheduler_options='#SBATCH --nodes NNODES --ntasks-per-node=8 -p batch -J MD_NNODESnodes -A csc728',

                # Command to be run before starting a worker
                #worker_init=

                # We request all hyperthreads on a node.
                launcher=SrunLauncher(overrides='--ntasks NCONFIGS -c 7 --gpus-per-task=1 --gpu-bind=closest'),
                walltime='0:20:00',

                # Slurm scheduler on Cori can be slow at times,
                # increase the command timeouts
                cmd_timeout=30,
            ),
        )
    ]
)

config_standard = Config(
    executors=[
        HighThroughputExecutor(
            label='alf_QM_executor',
            #This executor is kinda strange. We manually increase the node count so that 
            #our parallel qm job gets multiple nodes, but leave nodes_per_block=1 so 
            #that parsl  doesn't assign multiple tasks

            max_workers_per_node=1, ###RAM: I don't understand why this is needed

            provider=SlurmProvider(
                init_blocks = 0,
                min_blocks = 0,
                max_blocks = 1,


                # string to prepend to #SBATCH blocks in the submit
                scheduler_options='#SBATCH --nodes=2 --ntasks-per-node=8 -p batch -J QM -A  csc728',

                # Command to be run before starting a worker
                #worker_init=

                # We request all hyperthreads on a node.
                launcher=SrunLauncher(overrides='--ntasks 16 -c 7 --gpus-per-task=1 --gpu-bind=closest'),

                walltime='0:10:00',

                # Slurm scheduler on Cori can be slow at times,
                # increase the command timeouts
                cmd_timeout=30,
            ),
        ),
        HighThroughputExecutor(
            label='alf_ML_executor',

            max_workers_per_node=1,

            provider=SlurmProvider(
                init_blocks = 0,
                min_blocks = 0,
                max_blocks = 1,
                
                nodes_per_block=2,

                # string to prepend to #SBATCH blocks in the submit
                scheduler_options='#SBATCH --nodes=2 --ntasks-per-node=1 -p batch -J ML -A csc728 --qos=debug',

                # Command to be run before starting a worker
                #worker_init='export HIPPYNN_USE_CUSTOM_KERNELS=triton',

                # We request all hyperthreads on a node.
                #launcher=SrunLauncher(),
                launcher=SrunLauncher(overrides='--ntasks 2 -c 56 --gpus-per-task=8 --gpu-bind=closest'),
                walltime='0:05:00',

                # Slurm scheduler on Cori can be slow at times,
                # increase the command timeouts
                cmd_timeout=30,
            ),
        ),
        HighThroughputExecutor(
            label='alf_sampler_executor',

            max_workers_per_node=1, ###RAM: I don't understand why this is needed

            provider=SlurmProvider(
                init_blocks = 0,
                min_blocks = 0,
                max_blocks = 1,

                # string to prepend to #SBATCH blocks in the submit
                scheduler_options='#SBATCH --nodes 2 --ntasks-per-node=8 -p batch -J MD -A csc728',

                # Command to be run before starting a worker
                #worker_init=

                # We request all hyperthreads on a node.
                launcher=SrunLauncher(overrides='--ntasks 16 -c 7 --gpus-per-task=1 --gpu-bind=closest'),
                walltime='0:10:00',

                # Slurm scheduler on Cori can be slow at times,
                # increase the command timeouts
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
                # Partition / QOS
                #'regular',
                #'ml4chem',
                #'debug',
                init_blocks = 0,
                min_blocks = 0,
                max_blocks = 1,

                nodes_per_block=1,
                #workers_per_node=1,

                # string to prepend to #SBATCH blocks in the submit
                scheduler_options='#SBATCH --nodes=1 --ntasks-per-node=1 -p batch -J QM_debug -A  csc728',

                # Command to be run before starting a worker
                #worker_init=

                # We request all hyperthreads on a node.
                launcher=SimpleLauncher(),
                walltime='0:10:00',

                # Slurm scheduler on Cori can be slow at times,
                # increase the command timeouts
                cmd_timeout=5,
            ),
        ),
        HighThroughputExecutor(
            label='alf_ML_executor',

            provider=SlurmProvider(
                init_blocks = 0,
                min_blocks = 0,
                max_blocks = 1,

                nodes_per_block=1,
                #workers_per_node=1,

                # string to prepend to #SBATCH blocks in the submit
                scheduler_options='#SBATCH --nodes=1 -p batch -J ML_debug -A  csc728 --qos=debug',

                # Command to be run before starting a worker
                #worker_init=

                # We request all hyperthreads on a node.
                #launcher=SrunLauncher(overrides='-c 64'),
                launcher=SingleNodeLauncher(),
                walltime='0:05:00',

                # Slurm scheduler on Cori can be slow at times,
                # increase the command timeouts
                cmd_timeout=5,
            ),
        ),
        HighThroughputExecutor(
            label='alf_sampler_executor',

            provider=SlurmProvider(
                init_blocks = 0,
                min_blocks = 0,
                max_blocks = 1,

                nodes_per_block=1,
                #workers_per_node=1,

                # string to prepend to #SBATCH blocks in the submit
                scheduler_options='#SBATCH --nodes=1 -p batch -J md_debug -A  csc728 --qos=debug',

                # Command to be run before starting a worker
                #worker_init=

                # We request all hyperthreads on a node.
                #launcher=SrunLauncher(overrides='-c 64'),
                launcher=SingleNodeLauncher(),
                walltime='0:01:00',

                # Slurm scheduler on Cori can be slow at times,
                # increase the command timeouts
                cmd_timeout=5,
            ),
        )
    ]
)
