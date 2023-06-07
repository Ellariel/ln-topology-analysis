
import networkx as nx
import pandas as pd
import numpy as np
from geopy.distance import geodesic

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
    ghg = global_energy_mix[country]['carbon_intensity'] if country in global_energy_mix and 'carbon_intensity' in global_energy_mix[country] else None
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