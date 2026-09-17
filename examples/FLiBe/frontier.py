import parsl
from parsl.config import Config
from parsl.executors import HighThroughputExecutor
from parsl.addresses import address_by_interface

# For IC/NERSC:
from parsl.providers import SlurmProvider
from parsl.launchers import SrunLauncher
from parsl.launchers import SingleNodeLauncher
from parsl.launchers import SimpleLauncher

config_standard = Config(
    executors=[
        HighThroughputExecutor(
            label='alf_QM_executor',
            #This executor is kinda strange. We manually increase the node count so that 
            #our parallel qm job gets multiple nodes, but leave nodes_per_block=1 so 
            #that parsl  doesn't assign multiple tasks

            # Optional: the network interface on the login node to
            # which compute nodes can communicate
            #address=address_by_interface('bond0.144'),
            #max_workers=8,
            #cpu_affinity='alternating',
            max_workers_per_node=1, ###RAM: I don't understand why this is needed

            provider=SlurmProvider(
                # Partition / QOS
                #'regular',
                #'ml4chem',
                #'standard',
                init_blocks = 0,
                min_blocks = 0,
                max_blocks = 1,

                #nodes_per_block=6,
                #workers_per_node=8, ###Commented out previously, didn't work when uncommented

                # string to prepend to #SBATCH blocks in the submit
                scheduler_options='#SBATCH --nodes=6 --ntasks-per-node=8 -p batch -J QM -A  csc728 --qos=debug',

                # Command to be run before starting a worker
                #worker_init=

                # We request all hyperthreads on a node.
                #launcher=SrunLauncher(overrides='-c 64'),
                #launcher=SimpleLauncher(),
                launcher=SrunLauncher(overrides='--ntasks 48 -c 7 --gpus-per-task=1 --gpu-bind=closest'),
                walltime='0:05:00',

                # Slurm scheduler on Cori can be slow at times,
                # increase the command timeouts
                cmd_timeout=30,
            ),
        ),
        HighThroughputExecutor(
            label='alf_ML_executor',

            # Optional: the network interface on the login node to
            # which compute nodes can communicate
            #address=address_by_interface('bond0.144'),
            #max_workers=1,
            #cpu_affinity='alternating',


            provider=SlurmProvider(
                # Partition / QOS
                #'regular',
                #'ml4chem',
                #'gpu',
                init_blocks = 0,
                min_blocks = 0,
                max_blocks = 1,

                nodes_per_block=1,
                #workers_per_node=1,

                # string to prepend to #SBATCH blocks in the submit
                #scheduler_options='#SBATCH --qos=debug',
                scheduler_options='#SBATCH --nodes=1 -p batch -J ML -A csc728',

                # Command to be run before starting a worker
                #worker_init='export HIPPYNN_USE_CUSTOM_KERNELS=triton',

                # We request all hyperthreads on a node.
                #launcher=SrunLauncher(overrides='-c 64'),
                launcher=SingleNodeLauncher(),
                walltime='0:03:00',

                # Slurm scheduler on Cori can be slow at times,
                # increase the command timeouts
                cmd_timeout=30,
            ),
        ),
        HighThroughputExecutor(
            label='alf_sampler_executor',

            # Optional: the network interface on the login node to
            # which compute nodes can communicate
            #address=address_by_interface('bond0.144'),
            max_workers_per_node=1, ###RAM: I don't understand why this is needed

            provider=SlurmProvider(
                # Partition / QOS
                #'regular',
                #'ml4chem',
                #'gpu',
                init_blocks = 0,
                min_blocks = 0,
                max_blocks = 1,

                #nodes_per_block=6,

                # string to prepend to #SBATCH blocks in the submit
                #scheduler_options='#SBATCH --qos=debug',
                scheduler_options='#SBATCH --nodes 6 --ntasks-per-node=8 -p batch -J MD -A csc728',

                # Command to be run before starting a worker
                #worker_init=

                # We request all hyperthreads on a node.
                #launcher=SrunLauncher(overrides='-c 64'),
                launcher=SrunLauncher(overrides='--ntasks 48 -c 7 --gpus-per-task=1 --gpu-bind=closest'),
                #launcher=SingleNodeLauncher(),
                walltime='0:02:00',

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

            # Optional: the network interface on the login node to
            # which compute nodes can communicate
            #address=address_by_interface('bond0.144'),
            #max_workers=1,
            #cpu_affinity='alternating',


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
                #launcher=SrunLauncher(overrides='-c 64'),
                launcher=SimpleLauncher(),
                walltime='0:10:00',

                # Slurm scheduler on Cori can be slow at times,
                # increase the command timeouts
                cmd_timeout=5,
            ),
        ),
        HighThroughputExecutor(
            label='alf_ML_executor',

            # Optional: the network interface on the login node to
            # which compute nodes can communicate
            #address=address_by_interface('bond0.144'),
            #max_workers=1,
            #cpu_affinity='alternating',


            provider=SlurmProvider(
                # Partition / QOS
                #'regular',
                #'ml4chem',
                #'gpu_debug',
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

            # Optional: the network interface on the login node to
            # which compute nodes can communicate
            #address=address_by_interface('bond0.144'),
            #max_workers=4,
            #cpu_affinity='alternating',

            provider=SlurmProvider(
                # Partition / QOS
                #'regular',
                #'ml4chem',
                #'gpu_debug',
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
                walltime='0:30:00',

                # Slurm scheduler on Cori can be slow at times,
                # increase the command timeouts
                cmd_timeout=5,
            ),
        )
    ]
)
