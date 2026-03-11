import pandas as pd
from pyalex import Institutions, config
import time
from tqdm import tqdm
import os

config.email = "guillaume.godet@univ-nantes.fr"

print("Loading dataset...")
df = pd.read_parquet("cooperations_ls2n.parquet")

# Extraire tous les IDs d'institutions uniques
all_inst_ids = set()
for inst_id_str in df['inst_id'].dropna():
    for inst_id in inst_id_str.split('|'):
        if inst_id:
            all_inst_ids.add(inst_id)

all_inst_ids = list(all_inst_ids)
print(f"Total unique institutions to fetch coordinates for: {len(all_inst_ids)}")

coord_map = {}

# On fait des requêtes par lots (max 50 par requête pour OpenAlex avec le filtre OR)
chunk_size = 50
chunks = [all_inst_ids[i:i + chunk_size] for i in range(0, len(all_inst_ids), chunk_size)]

print("Fetching coordinates from OpenAlex...")
for chunk in tqdm(chunks):
    try:
        query_val = "|".join([f"I{i}" for i in chunk])
        results = Institutions().filter(openalex=query_val).get()
        for res in results:
            id_val = res['id'].replace("https://openalex.org/I", "")
            geo = res.get('geo', {})
            if geo and geo.get('latitude') and geo.get('longitude'):
                coord_map[id_val] = {'lat': geo['latitude'], 'lon': geo['longitude']}
    except Exception as e:
        print(f"Error fetching chunk: {e}")
        time.sleep(2)

print(f"Fetched coordinates for {len(coord_map)} institutions.")

# Create the new columns
def get_lat_lon(ids, key):
    res = []
    for inst_id in str(ids).split('|'):
        if inst_id in coord_map:
            res.append(str(coord_map[inst_id][key]))
        else:
            res.append("")
    return "|".join(res)

print("Updating dataframe...")
df['lat'] = df['inst_id'].apply(lambda x: get_lat_lon(x, 'lat'))
df['lon'] = df['inst_id'].apply(lambda x: get_lat_lon(x, 'lon'))

df.to_parquet("cooperations_ls2n.parquet", index=False)
df.to_csv("cooperations_ls2n.csv", index=False)
print("Updated parquet and csv files with latitude and longitude.")
