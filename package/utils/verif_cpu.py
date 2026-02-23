import multiprocessing
from tqdm import tqdm

def verif_cpu(cpu, length_ensemble):
    cpu_max = cpu
    if cpu > multiprocessing.cpu_count():
        cpu_max = min(multiprocessing.cpu_count(), length_ensemble)
        tqdm.write(f"[INFO] You've selected a higher number of cpu than your current available cpu : {multiprocessing.cpu_count()}")
    if cpu > length_ensemble:
        cpu_max = min(cpu, length_ensemble)
        tqdm.write(f"[INFO] You've selected a higher number of cpu than the number needed : {multiprocessing.cpu_count()}")
    tqdm.write(f"[INFO] you are currently using {cpu_max} cpu")
    return cpu_max