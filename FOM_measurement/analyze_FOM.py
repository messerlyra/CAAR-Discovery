#!/usr/bin/env python3
"""Analyze and extrapolate ALF MD/QM/ML workflow timings."""

import argparse
from datetime import datetime
import math
from pathlib import Path
import pickle
import re


def get_timestamp(directory, pattern):
    """Return the latest modification time matching a glob pattern."""
    files = list(directory.glob(pattern))
    if not files:
        raise FileNotFoundError(f"No files found matching: {directory / pattern}")
    if len(files) > 1:
        print(f"Warning: Multiple files match {pattern}. Using the most recently modified file.")
    return max(files, key=lambda f: f.stat().st_mtime).stat().st_mtime


def format_duration(seconds):
    """Format seconds as HH:MM:SS.ss."""
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{int(hours):02d}:{int(minutes):02d}:{seconds:05.2f}"


def analyze_md_steps(sampling_dir):
    """Return average MD step wall time, maximum recorded step, and trajectory count.

    Each delta_realtime_step_* measurement represents 100 steps. Ignore
    measurements at steps 0 and 100 to exclude initial equilibration.
    """
    pickle_files = sorted(sampling_dir.glob('*.p'))
    if not pickle_files:
        raise FileNotFoundError(f"No pickle files found in: {sampling_dir}")
    total_step_time = 0.0
    timing_count = 0
    steps_per_trajectory = []
    for file in pickle_files:
        with file.open('rb') as handle:
            data = pickle.load(handle)  # Only use trusted ALF-generated pickle files.
        if not isinstance(data, dict):
            continue
        step_indices = []
        for key, value in data.items():
            match = re.search(r'delta_realtime_step_(\d+)$', str(key))
            if not match:
                continue
            step_index = int(match.group(1))
            step_indices.append(step_index)
            if step_index <= 100:
                continue
            total_step_time += float(value)
            timing_count += 1
        if step_indices:
            steps_per_trajectory.append(max(step_indices))
    if not timing_count:
        raise ValueError('No MD timing data found after equilibration.')
    if not steps_per_trajectory:
        raise ValueError('No MD step indices found.')
    return total_step_time / timing_count / 100.0, max(steps_per_trajectory), len(steps_per_trajectory)


def get_num_atoms(sampling_dir):
    """Read the atom count from the positions array in a sampling pickle."""
    for file in sorted(sampling_dir.glob('*.p')):
        with file.open('rb') as handle:
            data = pickle.load(handle)  # Only load trusted ALF-generated files.
        if isinstance(data, dict) and 'positions' in data:
            num_atoms = len(data['positions'])
            if num_atoms <= 0:
                raise ValueError(f'Empty positions array in: {file}')
            return num_atoms
    raise ValueError(f'No sampling pickle contains positions in: {sampling_dir}')


def analyze_qm_calculations(qm_dir, num_trajectories):
    """Count QM output files and extrapolate batches to MD trajectory count."""
    mol_dirs = sorted(d for d in qm_dir.glob('mol-*') if d.is_dir())
    total_qm = len(mol_dirs)
    completed_qm = sum((d / 'output.txt').is_file() for d in mol_dirs)
    if not completed_qm:
        raise ValueError('No completed QM calculations found.')
    qm_batches = math.ceil(num_trajectories / completed_qm)
    return completed_qm, total_qm, qm_batches



def analyze_ml_epochs(ensembles_dir):
    """Read the last epoch duration and index from each model in the latest ensemble."""
    candidates = []
    for directory in ensembles_dir.glob('ensemble-*'):
        if directory.is_dir():
            match = re.fullmatch(r'ensemble-(\d+)', directory.name)
            if match:
                candidates.append((int(match.group(1)), directory))
    if not candidates:
        raise FileNotFoundError(f'No ensemble-NNNN directories found in: {ensembles_dir}')
    ensemble_dir = max(candidates, key=lambda item: item[0])[1]
    models = []
    for directory in ensemble_dir.iterdir():
        if directory.is_dir() and re.fullmatch(r'model[-_](\d+)', directory.name):
            log = directory / 'training_log.txt'
            if not log.is_file():
                raise FileNotFoundError(f'Missing training log: {log}')
            content = log.read_text(encoding='utf-8', errors='replace')
            durations = re.findall(r'Total epoch time:\s*([0-9]+(?:\.[0-9]+)?)\s*s\b', content)
            epochs = re.findall(r'\bEpoch\s+(\d+)\s*:', content)
            if not durations or not epochs:
                models.append((directory.name, 0, 0))
                continue
                #raise ValueError(f'Missing epoch timing or index in: {log}')
            duration = float(durations[-1])
            if not math.isfinite(duration) or duration <= 0:
                raise ValueError(f'Invalid last epoch duration in: {log}')
            models.append((directory.name, int(epochs[-1]) + 1, duration))
    #if not models:
    #    raise ValueError(f'No model training directories found in: {ensemble_dir}')
    models.sort(key=lambda item: int(re.search(r'(\d+)$', item[0]).group(1)))
    if len(models) != 8:
        print(f'Warning: Expected 8 ML models, found {len(models)} in {ensemble_dir}.')
    epoch_counts = {item[1] for item in models}
    if len(epoch_counts) != 1:
        raise ValueError(f'Models have different completed epoch counts: {sorted(epoch_counts)}')
    return ensemble_dir, models[0][1], sum(item[2] for item in models) / len(models), models

def main():
    parser = argparse.ArgumentParser(description='Analyze ALF workflow execution times.')
    parser.add_argument('--alf_path', type=Path, default=Path.cwd(), help='ALF root directory (default: current working directory / PWD)')
    parser.add_argument('--timestep', type=float, default=0.25, help='MD timestep in fs (default: 0.25)')
    parser.add_argument('--md-duration', type=float, default=100.0, help='Target MD duration in ps (default: 100.0)')
    parser.add_argument('--epochs', type=int, default=500, help='Target ML epochs (default: 500)')
    args = parser.parse_args()
    if args.epochs <= 0:
        parser.error('--epochs must be a positive integer.')
    if not math.isfinite(args.timestep) or not math.isfinite(args.md_duration) or args.timestep <= 0 or args.md_duration <= 0:
        parser.error('--timestep and --md-duration must be finite positive numbers.')

    scripts_dir = args.alf_path / 'runinfo' / '000' / 'submit_scripts'
    sampling_dir = args.alf_path / 'sampling'
    qm_dir = args.alf_path / 'QM'
    ensembles_dir = args.alf_path / 'ensembles'
    for directory in (scripts_dir, sampling_dir, qm_dir, ensembles_dir):
        if not directory.is_dir():
            parser.error(f'Directory not found: {directory}')

    t_md_start = get_timestamp(scripts_dir, 'cmd_MD*.sh')
    t_md_end = get_timestamp(scripts_dir, 'parsl.alf_sampler_executor.block-0.*.stderr')
    t_qm_start = get_timestamp(scripts_dir, 'cmd_QM*.sh')
    t_qm_end = get_timestamp(scripts_dir, 'parsl.alf_QM_executor.block-0.*.stderr')
    t_ml_start = get_timestamp(scripts_dir, 'cmd_ML*.sh')
    t_ml_end = get_timestamp(scripts_dir, 'parsl.alf_ML_executor.block-0.*.stderr')
    md_time_original = t_md_end - t_md_start
    qm_time_original = t_qm_end - t_qm_start
    ml_time_original = t_ml_end - t_ml_start
    if min(md_time_original, qm_time_original, ml_time_original) < 0:
        raise ValueError('Invalid timestamp order. Check the selected files.')

    avg_time_step, original_steps, num_trajectories = analyze_md_steps(sampling_dir)
    target_steps = round(args.md_duration * 1000 / args.timestep)
    additional_steps = max(0, target_steps - original_steps)
    md_time_additional = additional_steps * avg_time_step
    md_time = md_time_original + md_time_additional

    completed_qm, total_qm, qm_batches = analyze_qm_calculations(qm_dir, num_trajectories)
    qm_time = qm_time_original * qm_batches
    ensemble_dir, original_epochs, avg_epoch_time, model_timings = analyze_ml_epochs(ensembles_dir)
    additional_epochs = max(0, args.epochs - original_epochs)
    ml_time_additional = additional_epochs * avg_epoch_time
    ml_time = ml_time_original + ml_time_additional
    total_time = md_time + qm_time + ml_time
    if total_time <= 0:
        raise ValueError('Total extrapolated workflow time must be positive.')

    num_atoms = get_num_atoms(sampling_dir)
    qm_calcs = completed_qm * qm_batches
    if qm_calcs > num_trajectories:
        print(
        f"WARNING: Extrapolated QM calculations ({qm_calcs}) "
        f"exceed MD trajectories ({num_trajectories}). "
        f"Limiting QM calculations to {num_trajectories}."
        )
        qm_calcs = num_trajectories
    force_components = qm_calcs * num_atoms * 3
    total_hours = total_time / 3600.0
    fom = force_components / total_hours

    print('\nALF Workflow Timing Analysis')
    print('=' * 50)
    print(f'\nALF directory: {args.alf_path.resolve()}')
    print('\nTimestamps:')
    for label, timestamp in [('MD start', t_md_start), ('MD end', t_md_end), ('QM start', t_qm_start), ('QM end', t_qm_end), ('ML start', t_ml_start), ('ML end', t_ml_end)]:
        date = datetime.fromtimestamp(timestamp)
        print(f'  {label:<12}: {date:%Y-%m-%d %H:%M:%S}')

    print('\nMD Step Analysis:')
    print(f'  Trajectories analyzed : {num_trajectories}')
    print(f'  MD timestep           : {args.timestep:.4f} fs')
    print(f'  Target MD duration    : {args.md_duration:.4f} ps')
    print(f'  Original MD steps     : {original_steps:,}')
    print(f'  Target MD steps       : {target_steps:,}')
    print(f'  Additional MD steps   : {additional_steps:,}')
    print(f'  Average time per step : {avg_time_step:.6f} s')

    print('\nMD Timing Extrapolation:')
    print(f'  Original MD time      : {format_duration(md_time_original)}')
    print(f'  Additional MD time    : {format_duration(md_time_additional)}')
    print(f'  Extrapolated MD time  : {format_duration(md_time)}')

    print('\nQM Labeling Analysis:')
    print(f'  MD trajectories       : {num_trajectories}')
    print(f'  QM calculations       : {total_qm}')
    print(f'  Completed QM          : {completed_qm}')
    print(f'  Required QM batches   : {qm_batches}')
    print(f'  Original QM time      : {format_duration(qm_time_original)}')
    print(f'  Extrapolated QM calcs : {qm_calcs:,}')
    print(f'  Extrapolated QM time  : {format_duration(qm_time)}')

    print('\nML Training Analysis:')
    print(f'  Ensemble              : {ensemble_dir.name}')
    for model_name, epochs_done, last_time in model_timings:
        print(f'  {model_name:<21} : {epochs_done} epochs, last epoch {last_time:.4f} s')
    print(f'  Original ML epochs    : {original_epochs:,}')
    print(f'  Target ML epochs      : {args.epochs:,}')
    print(f'  Additional ML epochs  : {additional_epochs:,}')
    print(f'  Average epoch time    : {avg_epoch_time:.6f} s')
    print(f'  Original ML time      : {format_duration(ml_time_original)}')
    print(f'  Additional ML time    : {format_duration(ml_time_additional)}')
    print(f'  Extrapolated ML time  : {format_duration(ml_time)}')

    print('\nStage Durations:')
    print(f'  MD Sampling : {format_duration(md_time)}')
    print(f'  QM Labeling : {format_duration(qm_time)}')
    print(f'  ML Training : {format_duration(ml_time)}')
    print('  ' + '-' * 35)
    print(f'  Total       : {format_duration(total_time)}')

    print('\nFigure of Merit (FOM):')
    print(f'  Total QM calculations : {qm_calcs:,}')
    print(f'  Atoms per structure   : {num_atoms:,}')
    print(f'  Force components/atom : 3')
    print(f'  Total force components: {force_components:,}')
    print(f'  Total time (hours)    : {total_hours:.6f}')
    print(f'  FOM (components/hour) : {fom:,.2f}')

    print('\nTime Distribution:')
    for label, duration in [('MD', md_time), ('QM', qm_time), ('ML', ml_time)]:
        percentage = 100 * duration / total_time if total_time else 0
        print(f'  {label:<3}: {percentage:6.2f}%')
    print()


if __name__ == '__main__':
    main()

