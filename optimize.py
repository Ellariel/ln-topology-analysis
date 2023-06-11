import networkx as nx
import numpy as np
from tqdm import tqdm
import pickle, json, random, os
import ray

import utils, proto

ray.init()

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

def get_comparison(G, T, comparison, e, global_energy_mix):
        a_results = ray.get(get_alg_results.remote(G, T, comparison[0], e, global_energy_mix))
        b_results = ray.get(get_alg_results.remote(G, T, comparison[1], e, global_energy_mix))
                    
        complete = []
        for t in range(len(T)):
            complete.append(bool(a_results[t][1]) and bool(b_results[t][1]))         
        
        metric_results = {m : {} for m in metrics}
        for m in metrics:
            metric_results[m][comparison[0]] = [a_results[i][1][m] for i, t in enumerate(complete) if t and m in a_results[i][1]]
            metric_results[m][comparison[1]] = [b_results[i][1][m] for i, t in enumerate(complete) if t and m in b_results[i][1]]
            
        metric_results['avg_intercountry_hops'] = {}
        metric_results['avg_intercontinental_hops'] = {}
        metric_results['avg_geodist'] = {}
        metric_results['avg_ghg'] = {}
        for a in comparison:
            metric_results['avg_intercountry_hops'][a] = np.array(metric_results['intercountry_hops'][a]) / np.array(metric_results['dist'][a])
            metric_results['avg_intercontinental_hops'][a] = np.array(metric_results['intercontinental_hops'][a]) / np.array(metric_results['dist'][a])
            metric_results['avg_geodist'][a] = np.array(metric_results['geodist'][a]) / np.array(metric_results['dist'][a])
            metric_results['avg_ghg'][a] = np.array(metric_results['sum_ghg'][a]) / np.array(metric_results['dist'][a])
            
        diff = []
        for m in optimize_metrics:
            a = np.mean(metric_results[m][comparison[0]])
            b = np.mean(metric_results[m][comparison[1]])
            d = (b - a) * 100 / a
            print(f"{m} ε={'+' if d > 0 else ''}{d:.1f}%")
            diff.append(d)
        
        return np.mean(diff)
        
    
    
with open('ln-graph-prepared.pickle', 'rb') as f:
    f = pickle.load(f)
    G = f['directed_graph']
    print(f'nodes: {len(G.nodes)} edges: {len(G.edges)}')
    T = f['transactions'][:10] ####
    print(f'transactions: {len(T)}')
    
with open('global_energy_mix.json', 'r') as f:
    global_energy_mix = json.load(f)

native_alg = ['LND', 'CLN', 'ECL']
alg = native_alg + ['H(LND)', 'H(CLN)', 'H(ECL)']
metrics = ['dist', 'geodist', 'sum_ghg', 'delay', 'feeratio', 'feerate',
           'intercontinental_hops', 'intercountry_hops', 
           'avg_geodist', 'avg_ghg', 'avg_intercountry_hops', 'avg_intercontinental_hops']
optimize_metrics = ['dist', 'avg_ghg', 'avg_intercountry_hops', 'avg_intercontinental_hops']

comparisons = [('LND', 'H(LND)')]

random.seed(13)
np.random.seed(13)

e = 0.001
    
if G and T:
    for c in comparisons:
        results = get_comparison(G, T, c, e, global_energy_mix)

        print(results)
    
