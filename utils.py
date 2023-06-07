
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
            loc = [get_coords(p) for p in path]
            #loc = drop_none(loc)
            dist = []
            for c in range(len(loc)-1):
                dist.append(geodesic(loc[c], loc[c+1]).km)
            return np.sum(dist)

def get_continent_hops(G, path):
        for p in range(len(path)-1):
            e = G.get_edge_data(path[p], path[p+1])
            loc = [get_continent(p) for p in path]
            loc = drop_none(loc)
            hops = 0
            for c in range(len(loc)-1):
                if loc[c] != loc[c+1]:
                  hops += 1
            return hops

def get_country_hops(G, path):
        for p in range(len(path)-1):
            e = G.get_edge_data(path[p], path[p+1])
            loc = [get_country(p) for p in path]
            loc = drop_none(loc)
            hops = 0
            for c in range(len(loc)-1):
                if loc[c] != loc[c+1]:
                  hops += 1
            return hops