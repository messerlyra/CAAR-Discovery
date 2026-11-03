import pickle
import os
import sys

avg_time_step = 0
count = 0

sampling_dir = 'sampling'

for file_name in os.listdir(sampling_dir):
    if '.p' not in file_name: continue
    with open(sampling_dir+'/'+file_name,"rb") as f:
        p = pickle.load(f)

    print(file_name)
    Natoms = len(p['positions'])
    print(f"{Natoms=}")
    print(f"{p['realtime_simulation']=}")
    print(f"{p['simulationtime']=}")
    print(f"{p['distmin']=}")
    print(f"{p['distcrit']=}")
    print(f"{p['Es']=}")
    print(f"{p['Fs']=}")
    print(f"{p['Fsmax']=}")
    print(f"{p['Ecrit']=}")
    print(f"{p['Fcrit']=}")
    print(f"{p['Fmcrit']=}")
    for key, val in p.items():
        if "delta_realtime_step" in key: print(key,val)
    for key, val in p.items():
        if "realtime_step" in key and "delta" not in key: print(key,val) 

    for key, val in p.items():
        if "delta_realtime_step" in key and "delta_realtime_step_0" not in key:
            avg_time_step += float(val) 
            count += 1

if count > 0:
    avg_time_step /= count
    print(f"{avg_time_step=}")

