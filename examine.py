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
    T = f['transactions']
    print(f'transactions: {len(T)}')
    
with open('global_energy_mix.json', 'r') as f:
    global_energy_mix = json.load(f)

alg = ['LND', 'CLN', 'ECL', 'H(LND)', 'H(CLN)', 'H(ECL)']

if G and T:
    for a in tqdm(alg):
        f = f'{a}-results.pickle'
        if not os.path.exists(f):
            results = []
            for t in tqdm(T, desc=a, leave=False):
                path = proto.get_shortest_path(G, t[0], t[1], t[2], proto_type=a, 
                                            global_energy_mix=global_energy_mix)
                if path:
                    r = utils.get_path_params(G, path, t[2], global_energy_mix=global_energy_mix)
                    results.append((t, r))
                else:
                    results.append((t, None))
            with open(f, 'wb') as f:
                pickle.dump(results, f)
    
