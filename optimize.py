import networkx as nx
import numpy as np
from tqdm import tqdm
import pickle, json, random, os
import ray
# see https://github.com/bayesian-optimization/BayesianOptimization
from bayes_opt import BayesianOptimization
from bayes_opt.logger import JSONLogger
from bayes_opt.event import Events
from bayes_opt import UtilityFunction

import utils, proto

native_alg = ['LND', 'CLN', 'ECL']
modified_alg = ['H(LND)', 'H(CLN)', 'H(ECL)']
metrics = ['dist', 'geodist', 'sum_ghg', 'delay', 'feeratio', 'feerate',
           'intercontinental_hops', 'intercountry_hops', 
           'avg_geodist', 'avg_ghg', 'avg_intercountry_hops', 'avg_intercontinental_hops']
train_limit = 1000

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
    T = f['transactions'][:train_limit] ####
    print(f'transactions: {len(T)}')
    
with open(os.path.join(snapshots_dir, 'global_energy_mix.json'), 'r') as f:
    global_energy_mix = json.load(f)
    
ray.init()

@ray.remote
def get_alg_results(G, T, alg, e, global_energy_mix):
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
        #with open(f, 'wb') as f:
        #    pickle.dump(_results, f)
    return _results[:train_limit]

def get_comparison(G, T, comparison, e, global_energy_mix):
        a_results, b_results = ray.get([get_alg_results.remote(G, T, comparison[0], e, global_energy_mix),
                                        get_alg_results.remote(G, T, comparison[1], e, global_energy_mix)])
    
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
            print(f"{m}, ε={'+' if d > 0 else ''}{d:.1f}%")
            d = np.abs(d) * 10 ** -len(optimize_metrics) if d < 0 else 1
            diff.append(d)
        
        return np.prod(diff)
        
optimization_budget = 30
bounds = {'e' : (-1.0, 1.0)} # Bounded region of parameter space
optimize_metrics = ['dist', 'avg_ghg', 'intercountry_hops', 'intercontinental_hops']
comparisons = [('LND', 'H(LND)'), # 0.042
               ('CLN', 'H(CLN)'), # 0.5748
               ('ECL', 'H(ECL)'), # 0.35622
               ]

random.seed(48)
np.random.seed(48)

# results = get_comparison(G, T, comparisons[0], 0.3, global_energy_mix)
# print(results)

optimal = []
if G and T:
    for c in comparisons:
        print(c)  
        acq_function = UtilityFunction(kind = "ei", # Expected Improvement method
                                       kappa = 2.5, # kappa - the balance between exploration and exploitation
        ) 
        optimizer = BayesianOptimization(f = None,
                                        pbounds = bounds,
                                        random_state = 48,
        )
        logger = JSONLogger(path=os.path.join(results_dir, f"{c[0]}_optlog.json"))
        optimizer.subscribe(Events.OPTIMIZATION_STEP, logger)
        
        for i in range(optimization_budget):
            next_point = optimizer.suggest(acq_function)
            target = get_comparison(G, T, c, next_point['e'], global_energy_mix)
            optimizer.register(params=next_point, target=target)
            print(f"Iteration {i+1}, next point to probe is: {next_point['e']}, corresponded score is: {target}\n")
            
        o = optimizer.space.min()
        optimal.append((c[1], o))
        print(f'Best point for {c[1]}:', o)
    print()
    for o in optimal:
        print(f"{o[0]}: {o[1]}")
    
ray.shutdown()  
