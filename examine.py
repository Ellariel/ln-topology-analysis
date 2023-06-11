import networkx as nx
import numpy as np
from tqdm import tqdm
import pickle, json, random, os
import ray

import utils, proto

ray.init()

with open('ln-graph-prepared.pickle', 'rb') as f:
    f = pickle.load(f)
    G = f['directed_graph']
    print(f'nodes: {len(G.nodes)} edges: {len(G.edges)}')
    T = f['transactions'][:1000] ####
    print(f'transactions: {len(T)}')
    
with open('global_energy_mix.json', 'r') as f:
    global_energy_mix = json.load(f)

native_alg = ['LND', 'CLN', 'ECL']
alg = native_alg + ['H(LND)', 'H(CLN)', 'H(ECL)']
metrics = ['dist', 'geodist', 'sum_ghg', 'delay', 'feeratio', 'feerate',
           'intercontinental_hops', 'intercountry_hops', 
           'avg_geodist', 'avg_ghg', 'avg_intercountry_hops', 'avg_intercontinental_hops']

e = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]

random.seed(13)
np.random.seed(13)

def _load(f):
    with open(f, 'rb') as f:
        return pickle.load(f)    

@ray.remote
def get_alg_results(G, T, alg, e, global_energy_mix):
    _results = []
    f = f'{alg}-results.pickle'
    if alg in native_alg and os.path.exists(f):
        _results = _load(f)
    else:
        for t in T:
            r = None
            path = proto.get_shortest_path(G, t[0], t[1], t[2], proto_type=alg, 
                                                global_energy_mix=global_energy_mix, _e=e)
            if path:
                r = utils.get_path_params(G, path, t[2], global_energy_mix=global_energy_mix)
            _results.append((t, r)) 
    return _results

if G and T:
    results = {}
    metric_results = {}
    for _e in tqdm(e):
        results[_e] = {}
        for a in tqdm(alg, desc=f'e={_e}', leave=False):
            _results = ray.get(get_alg_results.remote(G, T, a, _e, global_energy_mix))
            results[_e][a] = _results
            
            f = f'{a}-results.pickle'
            if a in native_alg and not os.path.exists(f):
                with open(f, 'wb') as f:
                    pickle.dump(_results, f)
                    
        complete = []
        for t in range(len(T)):
            ok = True
            for a in alg:
                ok = ok and bool(results[_e][a][t][1])
            complete.append(ok)           
        
        metric_results[_e] = {m : {} for m in metrics}
        for m in metrics:
            for a in alg:
                metric_results[_e][m][a] = [results[_e][a][i][1][m] for i, t in enumerate(complete) if t and m in results[_e][a][i][1]]
            
        metric_results[_e]['avg_intercountry_hops'] = {}
        metric_results[_e]['avg_intercontinental_hops'] = {}
        metric_results[_e]['avg_geodist'] = {}
        metric_results[_e]['avg_ghg'] = {}
        for a in alg:
            metric_results[_e]['avg_intercountry_hops'][a] = np.array(metric_results[_e]['intercountry_hops'][a]) / np.array(metric_results[_e]['dist'][a])
            metric_results[_e]['avg_intercontinental_hops'][a] = np.array(metric_results[_e]['intercontinental_hops'][a]) / np.array(metric_results[_e]['dist'][a])
            metric_results[_e]['avg_geodist'][a] = np.array(metric_results[_e]['geodist'][a]) / np.array(metric_results[_e]['dist'][a])
            metric_results[_e]['avg_ghg'][a] = np.array(metric_results[_e]['sum_ghg'][a]) / np.array(metric_results[_e]['dist'][a])
            
    with open(f'metric_results.pickle', 'wb') as f:
            pickle.dump(metric_results, f)
