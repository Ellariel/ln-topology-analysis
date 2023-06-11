import networkx as nx
import numpy as np
from tqdm import tqdm
import pickle, json, random, os

import utils, proto

random.seed(13)
np.random.seed(13)

with open('ln-graph-prepared.pickle', 'rb') as f:
    f = pickle.load(f)
    G = f['directed_graph']
    print(f'nodes: {len(G.nodes)} edges: {len(G.edges)}')
    T = f['transactions'][:1000] ####
    print(f'transactions: {len(T)}')
    
with open('global_energy_mix.json', 'r') as f:
    global_energy_mix = json.load(f)

alg = ['LND', 'CLN', 'ECL', 'H(LND)', 'H(CLN)', 'H(ECL)']
metrics = ['dist', 'geodist', 'sum_ghg', 'delay', 'feeratio', 'feerate',
           'intercontinental_hops', 'intercountry_hops', 
           'avg_geodist', 'avg_ghg', 'avg_intercountry_hops', 'avg_intercontinental_hops']

e = 0.5

if G and T:
    for a in tqdm(alg):
        f = f'{a}-results.pickle'
        if not os.path.exists(f):
            results = []
            for t in tqdm(T, desc=a, leave=False):
                path = proto.get_shortest_path(G, t[0], t[1], t[2], proto_type=a, 
                                            global_energy_mix=global_energy_mix, _e=e)
                if path:
                    r = utils.get_path_params(G, path, t[2], global_energy_mix=global_energy_mix)
                    results.append((t, r))
                else:
                    results.append((t, None))
            with open(f, 'wb') as f:
                pickle.dump(results, f)
    
    results = {}
    for a in alg:
        f = f'{a}-results.pickle'
        if os.path.exists(f):
            with open(f, 'rb') as f:
                results[a] = pickle.load(f)
                #print(f'{a} - loaded')
                
    if len(results):
        complete = []
        for t in range(len(T)):
            ok = True
            for a in alg:
                ok = ok and bool(results[a][t][1])
            complete.append(ok)

        metric_results = {m : {} for m in metrics}
        for m in metrics:
            for a in alg:
                metric_results[m][a] = [results[a][i][1][m] for i, t in enumerate(complete) if t and m in results[a][i][1]]
            
        metric_results['avg_intercountry_hops'] = {}
        metric_results['avg_intercontinental_hops'] = {}
        metric_results['avg_geodist'] = {}
        metric_results['avg_ghg'] = {}
        for a in alg:
            metric_results['avg_intercountry_hops'][a] = np.array(metric_results['intercountry_hops'][a]) / np.array(metric_results['dist'][a])
            metric_results['avg_intercontinental_hops'][a] = np.array(metric_results['intercontinental_hops'][a]) / np.array(metric_results['dist'][a])
            metric_results['avg_geodist'][a] = np.array(metric_results['geodist'][a]) / np.array(metric_results['dist'][a])
            metric_results['avg_ghg'][a] = np.array(metric_results['sum_ghg'][a]) / np.array(metric_results['dist'][a])
            
        with open(f'metric_results.pickle', 'wb') as f:
            pickle.dump(metric_results, f)