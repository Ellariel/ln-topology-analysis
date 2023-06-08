
import networkx as nx
import pandas as pd
import numpy as np
from tqdm import tqdm
import random
from geopy.distance import geodesic

import proto

def not_na(x):
    return pd.notna(x)

def drop_none(x):
    return [i for i in x if not_na(i)]

def get_node_location(G, id):
    if 'locations' in G.nodes[id]:
      return G.nodes[id]['locations']

def get_coords(G, id):
     c = get_node_location(G, id)
     if c and 'latitude' in c:
        return (c['latitude'], c['longitude']) 

def get_continent(G, id):
     c = get_node_location(G, id)
     if c and 'continent_code' in c:
        return c['continent_code'] 

def get_country(G, id):
     c = get_node_location(G, id)
     if c and 'country_code_iso3' in c:
        return c['country_code_iso3'] 

def get_geodist(G, path):
        for p in range(len(path)-1):
            e = G.get_edge_data(path[p], path[p+1])
            loc = [get_coords(G, p) for p in path]
            #loc = drop_none(loc)
            dist = []
            for c in range(len(loc)-1):
                dist.append(geodesic(loc[c], loc[c+1]).km)
            return np.sum(dist)

def get_continent_hops(G, path):
        for p in range(len(path)-1):
            e = G.get_edge_data(path[p], path[p+1])
            loc = [get_continent(G, p) for p in path]
            loc = drop_none(loc)
            hops = 0
            for c in range(len(loc)-1):
                if loc[c] != loc[c+1]:
                  hops += 1
            return hops

def get_country_hops(G, path):
        for p in range(len(path)-1):
            e = G.get_edge_data(path[p], path[p+1])
            loc = [get_country(G, p) for p in path]
            loc = drop_none(loc)
            hops = 0
            for c in range(len(loc)-1):
                if loc[c] != loc[c+1]:
                  hops += 1
            return hops

def get_ghg(G, id, global_energy_mix):
    country, continent = get_country(G, id), get_continent(G, id)
    ghg = global_energy_mix[country]['carbon_intensity'] if country in global_energy_mix and 'carbon_intensity' in global_energy_mix[country] else False
    ghg = global_energy_mix['continent_average'][continent] if not ghg and continent and 'continent_average' in global_energy_mix and continent in global_energy_mix['continent_average'] else ghg
    ghg = global_energy_mix['world_average'] if not ghg and 'world_average' in global_energy_mix else ghg
    ghg = 726 if not ghg else ghg
    return ghg

def get_total_ghg(G, path, global_energy_mix):
        ghg = 0
        for p in path:
            ghg += get_ghg(G, p, global_energy_mix)
        return ghg

# Carbon intensity of electricity (gCO2/kWh)
# https://github.com/mlco2/codecarbon/blob/master/codecarbon/data/private_infra/global_energy_mix.json
def get_ghg_costs(G, u, v, global_energy_mix):
    return get_ghg(G, v, global_energy_mix) - get_ghg(G, u, global_energy_mix)

def get_shortest_path(G, u, v, amount, proto_type='LND', global_energy_mix=None):
    def weight_function(u, v, e):
      return proto.cost_function(G, u, v, amount, proto_type=proto_type, global_energy_mix=global_energy_mix)
    try:
      return nx.shortest_path(G, u, v, weight=weight_function)
    except:
      pass

def get_path_params(G, path, amount, global_energy_mix=None):
    a = amount
    p = path
    delay = 0     
    for i in range(len(p) - 1):
        if G.has_edge(p[i], p[i + 1]):
            e = G.edges[p[i], p[i + 1]]
            a += a * e['fee_rate_sat'] + e['fee_base_sat']
            delay += e['delay']
    return {'path' : p,
            'dist' : len(p),
            'geodist' : get_geodist(G, p),
            'ghg' : get_total_ghg(G, p, global_energy_mix),
            'delay' : delay,
            'feeratio' : a / amount,
            'feerate' : a / amount - 1,
            'amount' : a,
            'intercontinental_hops' : get_continent_hops(G, p),
            'intercountry_hops' : get_country_hops(G, p)}

def generate_tx(G, transacitons_count=1000, seed=2, centralized=False):
    log_space = np.logspace(0, 7, 10**6)
    ##
    def random_amount(): # SAT
        # Возвращает массив значений от 10^0 = 1 до 10^7, равномерно распределенных на логарифмической шкале
        # https://coingate.com/blog/post/lightning-network-bitcoin-stats-progress
        # The highest transaction processed is 0.03967739 BTC, while the lowest is 0.000001 BTC. The average payment size is 0.00508484 BTC;
        # highest: 3967739.0 SAT
        # average: 508484.0 SAT
        # lowest: 100.0 SAT
        return log_space[random.randrange(0, 10**6)] + 100
    ##
    def shortest_path_len(u, v):
        path_len = 0
        try:
              path_len = nx.shortest_path_length(G, u, v)
        except:
              pass
        return path_len
    ##
    random.seed(seed)
    tx_set = []
    nodes = list(G.nodes)
    max_path_length = 0
    if not centralized:
      for _ in tqdm(range(1, transacitons_count + 1)):
            while True:
              u = nodes[random.randrange(0, len(nodes))]
              v = nodes[random.randrange(0, len(nodes))]
              p = shortest_path_len(u, v)
              max_path_length = max(max_path_length, p)
              if v != u and p >= 2 and (u, v) not in tx_set:
                break
            tx_set.append((u, v))
    else:
      u = nodes[random.randrange(0, len(nodes))]
      for v in tqdm(nodes):
          p = shortest_path_len(u, v)
          max_path_length = max(max_path_length, p)
          if v != u and p >= 2 and (u, v) not in tx_set:
            tx_set.append((u, v))
    tx_set = [(tx[0], tx[1], random_amount()) for tx in tx_set]
    print(f'max_path_length: {max_path_length}')
    return tx_set