import pandas as pd
from pyalex import Works, config
from tqdm import tqdm

# Configuration (Optionnel: ajoute ton mail pour le "polite pool" d'OpenAlex)
config.email = "guillaume.godet@univ-nantes.fr"
config.api_key = "XZ4HqnJboSxbP7oERU2PBm"

# Dictionnaire des IDs OpenAlex avec leurs libellés
NANTES_MAP = {
    "I97188460": "Nantes Université",
    "I100445878": "Centrale Nantes",
    "I4387152714": "CAPHI",
    "I4387153064": "CFV",
    "I4387153012": "CReAAH",
    "I4387152322": "CREN",
    "I4399598365": "CRHIA",
    "I4387153799": "CRINI",
    "I4387153532": "ESO",
    "I4387152722": "LAMO",
    "I4387153176": "LETG",
    "I4387152679": "LLING",
    "I4210089331": "LPPL",
    "I4210138474": "CEISAM",
    "I4210137520": "GeM",
    "I4210148006": "GEPEA",
    "I4210100151": "IETR",
    "I4210091049": "IMN",
    "I4392021119": "IREENA",
    "I4210153365": "LMJL",
    "I4210146808": "LPG",
    "I4210117005": "LS2N",
    "I4210109587": "LTeN",
    "I4210109007": "SUBATECH",
    "I4387154840": "US2B",
    "I4392021198": "CR2TI",
    "I4210092509": "CRCI2NA",
    "I4387930219": "IICiMed",
    "I4392021193": "INCIT",
    "I4392021232": "ISOMER",
    "I4392021216": "MIP",
    "I4210162532": "PHAN",
    "I4387152865": "RMeS",
    "I4392021239": "SPHERE",
    "I4392021141": "TaRGeT",
    "I4210108033": "TENS",
    "I4210144168": "ITX",
    "I4392021194": "CDMO",
    "I4210153136": "CENS",
    "I4210100746": "DCS",
    "I4392021099": "IRDP",
    "I4390039323": "LEMNA",
    "I4210153154": "LHEEA",
    "I4210162214": "AAU",
}

def get_cooperations():
    # 1. On cible les publications de Nantes Université entre 2020 et 2025
    query = (
        Works()
        .filter(institutions={"id": "I97188460"})
        .filter(from_publication_date="2020-01-01", to_publication_date="2025-12-31")
        .filter(countries_distinct_count=">1")
    )
    
    results = []
    cursor = "*"
    pbar = None
    
    while cursor:
        page = query.get(per_page=200, cursor=cursor)
        meta = page.meta
        
        if pbar is None:
            pbar = tqdm(total=meta['count'], desc="Récupération OpenAlex")
        
        for work in page:
            work_id = work['id']
            title = work['display_name']
            year = work['publication_year']
            # Extraire les thèmes (topics), sous-domaines (subfields), domaines (fields) et grands domaines (domains)
            topics = []
            subfields = []
            fields = []
            domains = []
            for t in work.get('topics', []):
                if t.get('display_name'):
                    topics.append(t.get('display_name'))
                if t.get('subfield', {}).get('display_name'):
                    subfields.append(t.get('subfield').get('display_name'))
                if t.get('field', {}).get('display_name'):
                    fields.append(t.get('field').get('display_name'))
                if t.get('domain', {}).get('display_name'):
                    domains.append(t.get('domain').get('display_name'))
            
            topics_str = "|".join(dict.fromkeys(filter(None, topics)))
            subfields_str = "|".join(dict.fromkeys(filter(None, subfields)))
            fields_str = "|".join(dict.fromkeys(filter(None, fields)))
            domains_str = "|".join(dict.fromkeys(filter(None, domains)))
            
            # Analyser les auteurs et affiliations
            for auth in work.get('authorships', []):
                author_name = auth['author']['display_name']
                
                institutions = []
                inst_ids = []
                rors = []
                countries = []
                any_is_nantes = False

                for inst in auth.get('institutions', []):
                    inst_id_full = inst.get('id')
                    if not inst_id_full:
                        continue
                    
                    inst_id = inst_id_full.replace("https://openalex.org/", "")
                    country = inst.get('country_code')
                    inst_name = inst.get('display_name')
                    
                    # On cherche si c'est une institution nantaise (insensible à la casse)
                    is_nantes = inst_id.upper() in [k.upper() for k in NANTES_MAP.keys()]
                    
                    # CRITÈRE DE CONSERVATION : Nantes OU Étranger
                    if is_nantes or (country and country != 'FR'):
                        if is_nantes:
                            # Récupérer la clé correcte (insensible à la casse)
                            real_key = next(k for k in NANTES_MAP.keys() if k.upper() == inst_id.upper())
                            inst_name = NANTES_MAP[real_key]
                            any_is_nantes = True
                        
                        institutions.append(inst_name if inst_name else "")
                        inst_ids.append(inst_id)
                        rors.append(inst.get('ror') if inst.get('ror') else "")
                        countries.append(country if country else "")

                # On n'ajoute l'auteur que s'il a au moins une institution
                if institutions:
                    results.append({
                        "doi": work.get('doi'),
                        "work_id": work_id.replace("https://openalex.org/", ""),
                        "title": title,
                        "year": year,
                        "author": author_name,
                        "institution": "|".join(dict.fromkeys(filter(None, institutions))),
                        "inst_id": "|".join(dict.fromkeys(filter(None, inst_ids))),
                        "ror": "|".join(dict.fromkeys(filter(None, rors))),
                        "country": "|".join(dict.fromkeys(filter(None, countries))),
                        "topics": topics_str,
                        "subfields": subfields_str,
                        "fields": fields_str,
                        "domains": domains_str,
                        "authors_count": work.get('authors_count', 0),
                        "is_nantes": any_is_nantes
                    })
            pbar.update(1)
        
        cursor = meta.get('next_cursor')

    if pbar:
        pbar.close()

    return pd.DataFrame(results)

# Lancer l'extraction
df = get_cooperations()

# Sauvegarder pour le dashboard (Parquet = + rapide et + léger)
df.to_parquet("cooperations_nantesu.parquet", index=False)
df.to_csv("cooperations_nantesu.csv", index=False)
print("Fichiers générés : cooperations_nantesu.parquet et cooperations_nantesu.csv")