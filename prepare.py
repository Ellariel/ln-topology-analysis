import networkx as nx
import pandas as pd
import numpy as np
from tqdm import tqdm
import pickle, os, random
import utils

random.seed(13)
np.random.seed(13)

with open('ln-graph-snapshot.gpickle', 'rb') as f:
    G = pickle.load(f)
    print(f'nodes: {len(G.nodes)} edges: {len(G.edges)}')
    
if os.path.exists('iso_codes.csv'):
  iso = pd.read_csv('iso_codes.csv', sep=';')
  iso = iso[['Continent', 'ISO3']].set_index('ISO3').to_dict()['Continent']
  
short_dict = {'Europe' : 'EU',
              'Americas' : 'AM',
              'Asia' : 'AS',
              'Oceania' : 'OC',
              'Africa' : 'AF'}

for i in G.nodes:
  if 'locations' in G.nodes[i] and 'country_code_iso3' in G.nodes[i]['locations']:
    c = G.nodes[i]['locations']['country_code_iso3']
    if c in iso and iso[c] in short_dict:
      G.nodes[i]['locations']['continent_code'] = short_dict[iso[c]]
  
T = utils.generate_tx(G, 10000)
for i in T:
    if nx.shortest_path_length(G, i[0], i[1]) <= 1:
        print('path error!')

with open('ln-graph-prepared.pickle', 'wb') as f:
        pickle.dump({'directed_graph' : G,
                     'transactions' : T}, f)
        print('ln-graph-prepared.pickle saved.')