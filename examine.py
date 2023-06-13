import numpy as np
from tqdm import tqdm
import pickle, json, random, os
import ray

import utils, proto

native_alg = ['LND', 'CLN', 'ECL']
modified_alg = ['H(LND)', 'H(CLN)', 'H(ECL)']
metrics = ['dist', 'geodist', 'sum_ghg', 'delay', 'feeratio',# 'feerate',
           'intercontinental_hops', 'intercountry_hops', 
           'continents', 'countries', 'avg_geodist', 'avg_ghg']

e = list(np.array(range(-10, 11, 1)) / 10) + [0.27876, 0.25556, 0.35784]

base_dir = './'
snapshots_dir = os.path.join(base_dir, 'snapshots')
results_dir = os.path.join(base_dir, 'results')
os.makedirs(results_dir, exist_ok=True)
os.makedirs(snapshots_dir, exist_ok=True)

for alg in native_alg:
    os.makedirs(os.path.join(results_dir, alg), exist_ok=True)
    
with open(os.path.join(snapshots_dir, 'ln-graph-prepared.pickle'), 'rb') as f:
    f = pickle.load(f)
    G = f['directed_graph']
    print(f'nodes: {len(G.nodes)} edges: {len(G.edges)}')
    T = f['transactions']
    print(f'transactions: {len(T)}')
    
with open(os.path.join(snapshots_dir, 'global_energy_mix.json'), 'r') as f:
    global_energy_mix = json.load(f)
    
ray.init()

random.seed(13)
np.random.seed(13)

@ray.remote
def get_alg_results(G, T, alg, e, global_energy_mix, save=True):
    _results = []
    if alg in native_alg:
        f = os.path.join(os.path.join(results_dir, alg), f'{alg}_results.pickle')
    else:
        f = os.path.join(os.path.join(results_dir, alg[2:-1]), f'{alg[2:-1]}_{e}_results.pickle')
    if os.path.exists(f):
        with open(f, 'rb') as f:
            _results = pickle.load(f) 
    else:
        for t in T:
            r = None
            path = proto.get_shortest_path(G, t[0], t[1], t[2], proto_type=alg, 
                                                global_energy_mix=global_energy_mix, _e=e)
            if path:
                r = utils.get_path_params(G, path, t[2], global_energy_mix=global_energy_mix)
            _results.append((t, r)) 
        if save:
            with open(f, 'wb') as f:
                pickle.dump(_results, f)
    return _results

if G and T and not os.path.exists(os.path.join(results_dir, f'metric_results.pickle')):
    results = {0.0 : {}}
    metric_results = {}
    
    _reduced = ray.get([get_alg_results.remote(G, T, a, 0.0, global_energy_mix) for a in native_alg])
    for i, a in enumerate(native_alg):
            results[0.0][a] = _reduced[i]   
    
    for _e in tqdm(e):
        if _e not in results:
            results[_e] = {}     
        _reduced = ray.get([get_alg_results.remote(G, T, a, _e, global_energy_mix) for a in modified_alg])
        for i, a in enumerate(modified_alg):
            results[_e][a] = _reduced[i]
                    
        complete = []
        for t in range(len(T)):
            ok = True
            for a in native_alg:
                ok = ok and bool(results[0.0][a][t][1])
            for a in modified_alg:
                ok = ok and bool(results[_e][a][t][1])
            complete.append(ok)           
        
        metric_results[_e] = {m : {} for m in metrics}
        for m in metrics:
            for a in native_alg:
                metric_results[_e][m][a] = [results[0.0][a][i][1][m] for i, t in enumerate(complete) if t and m in results[0.0][a][i][1]]
            for a in modified_alg:
                metric_results[_e][m][a] = [results[_e][a][i][1][m] for i, t in enumerate(complete) if t and m in results[_e][a][i][1]]
            
        metric_results[_e]['avg_geodist'] = {}
        metric_results[_e]['avg_ghg'] = {}
        for a in native_alg + modified_alg:
            metric_results[_e]['avg_geodist'][a] = np.array(metric_results[_e]['geodist'][a]) / np.array(metric_results[_e]['dist'][a])
            metric_results[_e]['avg_ghg'][a] = np.array(metric_results[_e]['sum_ghg'][a]) / np.array(metric_results[_e]['dist'][a])
            
    with open(os.path.join(results_dir, f'metric_results.pickle'), 'wb') as f:
            pickle.dump(metric_results, f)
else:
    print('There is an issue with data or metric_results.pickle is already exists.')
            
ray.shutdown()