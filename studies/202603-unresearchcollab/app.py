import streamlit as st
import pandas as pd
import plotly.express as px
import pycountry
import os

st.set_page_config(page_title="Dashboard Coopération Nantes Université", layout="wide")

# Dictionnaire des unités de recherche nantaises (ID OpenAlex -> libellé)
NANTES_MAP = {
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
# Établissements nantais
COMPONENTS_MAP = {
    "Centrale Nantes": "I100445878",
    "Nantes Université": "I97188460"
}

# Mapping inverse : libellé -> ID
NANTES_LABEL_TO_ID = {v: k for k, v in NANTES_MAP.items()}

# Mapping des Pôles Nantes Université
POLES_MAP = {
    "Pôle Humanités": ["CAPHI", "CFV", "CReAAH", "CREN", "CRHIA", "CRINI", "ESO", "LAMO", "LETG", "LLING", "LPPL"],
    "Pôle S&T": ["CEISAM", "GeM", "GEPEA", "IETR", "IMN", "IREENA", "LMJL", "LPG", "LS2N", "LTeN", "SUBATECH", "US2B"],
    "Pôle Santé": ["CR2TI", "CRCI2NA", "IICiMed", "INCIT", "ISOMER", "MIP", "PHAN", "RMeS", "SPHERE", "TaRGeT", "TENS", "ITX"],
    "Pôle Sociétés": ["CDMO", "CENS", "DCS", "IRDP", "LEMNA"]
}

def get_country_name(code):
    try:
        if code == 'UK':
            return 'United Kingdom'
        c = pycountry.countries.get(alpha_2=code)
        return c.name if c else code
    except:
        return code

def explode_parallel_cols(df, cols, id_col='doi'):
    """Explose des colonnes séparées par '|' en s'assurant qu'elles restent alignées."""
    if df.empty:
        return pd.DataFrame(columns=[id_col] + cols)
    split = {c: df[c].fillna('').astype(str).str.split('|') for c in cols}
    # Calculer le nombre d'éléments pour chaque ligne (doit être identique pour toutes les colonnes de la ligne)
    max_len = pd.concat([s.apply(len) for s in split.values()], axis=1).max(axis=1)
    
    rows = []
    for idx in df.index:
        n = max_len[idx]
        parts = {c: (split[c][idx] + [''] * n)[:n] for c in cols}
        for i in range(n):
            row_data = {id_col: df.at[idx, id_col]}
            for c in cols:
                row_data[c] = parts[c][i].strip()
            rows.append(row_data)
    return pd.DataFrame(rows)

def render_publication(doi, work_data, selected_author="", selected_country="Tous les pays"):
    """Affiche une publication sous forme d'expander avec équipe Nantes, partenaires et métadonnées."""
    title = work_data['title'].iloc[0] if not pd.isna(work_data['title'].iloc[0]) else "Sans titre"
    year = work_data['year'].iloc[0]

    with st.expander(f"({year}) {title}"):
        c1, c2 = st.columns(2)
        with c1:
            st.write("**Équipe Nantes :**")
            n_auths = work_data[work_data['is_nantes'] == True]
            for _, r in n_auths.iterrows():
                style = f"**{r['author']}**" if r['author'] == selected_author else r['author']
                inst_label = r['institution'].replace('|', ' / ')
                st.write(f"👤 {style}  \n*{inst_label}*")
        with c2:
            st.write("**Partenaires Internationaux :**")
            # On récupère tous les auteurs qui ne sont pas de Nantes
            f_auths = work_data[work_data['is_nantes'] == False]
            
            partners_to_show = []
            for _, r in f_auths.iterrows():
                insts = str(r['institution']).split('|')
                cntrs = str(r['country']).split('|')
                
                for i, c in zip(insts, cntrs):
                    c_clean = c.strip()
                    if c_clean == 'FR' or c_clean == '' or c_clean == 'nan':
                        continue
                    if selected_country != "Tous les pays" and c_clean != selected_country:
                        continue
                    partners_to_show.append({
                        'author': r['author'],
                        'institution': i.strip(),
                        'country': c_clean
                    })
            
            if not partners_to_show:
                st.write("_Aucun partenaire correspondant aux filtres_")
            else:
                for p in partners_to_show:
                    country_label = get_country_name(p['country'])
                    st.write(f"🌎 {p['author']}  \n*{p['institution']}* ({country_label})")

        levels = [
            ('domains', "🎓 Domaines"),
            ('fields', "📚 Disciplines"),
            ('subfields', "🧪 Sous-disciplines"),
            ('topics', "🔬 Sujets")
        ]
        
        has_any = any(col in work_data.columns and not pd.isna(work_data[col].iloc[0]) and work_data[col].iloc[0] != "" for col, _ in levels)
        if has_any:
            st.write("---")
            for col, label in levels:
                if col in work_data.columns and not pd.isna(work_data[col].iloc[0]) and work_data[col].iloc[0] != "":
                    vals = work_data[col].iloc[0].split('|')
                    st.write(f"**{label} :** {', '.join(vals)}")

        openalex_id = work_data['work_id'].iloc[0]
        authors_count = work_data['authors_count'].iloc[0] if 'authors_count' in work_data.columns else "N/A"
        doi_display = doi if doi else "N/A"
        doi_link = f"[{doi_display}]({doi_display})" if doi else "N/A"
        st.caption(f"**DOI:** {doi_link} | **OpenAlex:** [{openalex_id}](https://openalex.org/works/{openalex_id}) | **👥 Auteurs:** {authors_count}")

def render_domains_topics(relevant_df, max_items=10):
    """Affiche les 4 niveaux OpenAlex triés par fréquence."""
    levels = [
        ('domains', "🎓 Domaines"),
        ('fields', "📚 Disciplines"),
        ('subfields', "🧪 Sous-disciplines"),
        ('topics', "🔬 Sujets")
    ]
    
    for col, label in levels:
        paper_data = relevant_df[['doi', col]].drop_duplicates()
        exploded = paper_data.assign(
            val=paper_data[col].str.split('|')
        ).explode('val')
        exploded['val'] = exploded['val'].str.strip()
        counts = exploded[exploded['val'] != ""].groupby('val')['doi'].nunique().sort_values(ascending=False)
        
        st.write(f"**{label} :**")
        if counts.empty:
            st.write(f"_Aucune donnée_")
        else:
            items = [f"{name} ({count})" for name, count in counts.head(max_items).items()]
            more = f" _+ {len(counts) - max_items} autres_" if len(counts) > max_items else ""
            st.write(", ".join(items) + more)


@st.cache_data
def load_data():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, "cooperations_nantesu.parquet")
    df = pd.read_parquet(file_path)
    
    # Conversion forcée des colonnes catégorielles en chaînes pour éviter les 0 fantômes dans les filtres/groupbys
    for col in df.select_dtypes(include=['category']).columns:
        df[col] = df[col].astype(str)
        
    # On s'assure que les noms sont bien formatés pour la recherche
    df['author'] = df['author'].fillna("Inconnu")
    
    # Sécurité : si le cache Streamlit est ancien et n'a pas les nouvelles colonnes
    for col in ['topics', 'subfields', 'fields', 'domains', 'city', 'authors_count']:
        if col not in df.columns:
            df[col] = 0 if col == 'authors_count' else ""
        
    return df

df = load_data()

# --- SIDEBAR : FILTRES ---
st.sidebar.header("📅 Période")

# Récupération de la période depuis l'URL
url_years = st.query_params.get("years", "2020-2025")
try:
    y_min, y_max = map(int, url_years.split("-"))
    default_years = (max(2020, y_min), min(2025, y_max))
except:
    default_years = (2020, 2025)

year_range = st.sidebar.slider(
    "Sélectionner la plage d'années :",
    min_value=2020,
    max_value=2025,
    value=default_years
)
st.query_params["years"] = f"{year_range[0]}-{year_range[1]}"

# On filtre par année immédiatement pour alléger la suite
working_df = df[(df['year'] >= year_range[0]) & (df['year'] <= year_range[1])]

# On initialise working_df avec les données de base (ou filtrées par auteur si déjà sélectionné)
if 'selected_author' not in st.session_state:
    st.session_state.selected_author = st.query_params.get("author", "Tous les auteurs")

if st.session_state.selected_author != "Tous les auteurs":
    author_dois = working_df[working_df['author'] == st.session_state.selected_author]['doi'].unique()
    working_df = working_df[working_df['doi'].isin(author_dois)]

# --- FILTRE PAYS (Dynamique selon l'auteur choisi) ---
st.sidebar.header("🌍 Filtre Géographique")
# On "explose" les pays pour avoir une liste propre d'individus
all_countries_series = working_df['country'].str.split('|').explode().str.strip()
valid_countries = all_countries_series[(all_countries_series != 'FR') & (all_countries_series != 'nan') & (all_countries_series != '')].dropna()

# On trie les pays par nombre de publications décroissant
country_counts = valid_countries.value_counts()
available_countries = list(country_counts.index)

country_options = ["Tous les pays"] + available_countries
url_country = st.query_params.get("country", "Tous les pays")
country_idx = country_options.index(url_country) if url_country in country_options else 0

selected_country = st.sidebar.selectbox(
    "Choisir un pays partenaire :", 
    country_options,
    index=country_idx,
    format_func=lambda x: f"{get_country_name(x)} ({country_counts[x]})" if x != "Tous les pays" else x
)
st.query_params["country"] = selected_country

# Sous-filtre établissement (uniquement si pays choisi)
selected_inst = "Tous les établissements"
if selected_country != "Tous les pays":
    # On n'affiche que les institutions du pays sélectionné
    temp_inst_df = explode_parallel_cols(
        working_df[working_df['country'].str.contains(selected_country, na=False)][['doi', 'institution', 'country']],
        ['institution', 'country']
    )
    available_insts = sorted(temp_inst_df[temp_inst_df['country'] == selected_country]['institution'].unique())
    inst_options = ["Tous les établissements"] + available_insts
    url_inst = st.query_params.get("inst", "Tous les établissements")
    inst_idx = inst_options.index(url_inst) if url_inst in inst_options else 0
    selected_inst = st.sidebar.selectbox("Choisir un établissement :", inst_options, index=inst_idx)
    st.query_params["inst"] = selected_inst

# --- FILTRES THÉMATIQUES HIÉRARCHIQUES ---
st.sidebar.header("🎯 Filtres Thématiques")

# 1. Domaines
all_domains = sorted(working_df['domains'].str.split('|').explode().str.strip().dropna().unique())
if 'nan' in all_domains: all_domains.remove('nan')
domain_options = ["Tous les domaines"] + all_domains
url_domain = st.query_params.get("domain", "Tous les domaines")
domain_idx = domain_options.index(url_domain) if url_domain in domain_options else 0
selected_domain = st.sidebar.selectbox("Filtre par domaine :", domain_options, index=domain_idx)
st.query_params["domain"] = selected_domain

# 2. Disciplines (Fields) - Cascade
temp_df_fields = working_df
if selected_domain != "Tous les domaines":
    temp_df_fields = working_df[working_df['domains'].str.contains(selected_domain, na=False, regex=False)]
all_fields = sorted(temp_df_fields['fields'].str.split('|').explode().str.strip().dropna().unique())
if 'nan' in all_fields: all_fields.remove('nan')
field_options = ["Toutes les disciplines"] + all_fields
url_field = st.query_params.get("field", "Toutes les disciplines")
field_idx = field_options.index(url_field) if url_field in field_options else 0
selected_field = st.sidebar.selectbox("Filtre par discipline :", field_options, index=field_idx)
st.query_params["field"] = selected_field

# 3. Sous-disciplines (Subfields) - Cascade
temp_df_subfields = temp_df_fields
if selected_field != "Toutes les disciplines":
    temp_df_subfields = temp_df_fields[temp_df_fields['fields'].str.contains(selected_field, na=False, regex=False)]
all_subfields = sorted(temp_df_subfields['subfields'].str.split('|').explode().str.strip().dropna().unique())
if 'nan' in all_subfields: all_subfields.remove('nan')
subfield_options = ["Toutes les sous-disciplines"] + all_subfields
url_subfield = st.query_params.get("subfield", "Toutes les sous-disciplines")
subfield_idx = subfield_options.index(url_subfield) if url_subfield in subfield_options else 0
selected_subfield = st.sidebar.selectbox("Filtre par sous-discipline :", subfield_options, index=subfield_idx)
st.query_params["subfield"] = selected_subfield

# 4. Sujets (Topics) - Cascade
temp_df_topics = temp_df_subfields
if selected_subfield != "Toutes les sous-disciplines":
    temp_df_topics = temp_df_subfields[temp_df_subfields['subfields'].str.contains(selected_subfield, na=False, regex=False)]
all_topics = sorted(temp_df_topics['topics'].str.split('|').explode().str.strip().dropna().unique())
if 'nan' in all_topics: all_topics.remove('nan')
topic_options = ["Tous les sujets"] + all_topics
url_topic = st.query_params.get("topic", "Tous les sujets")
topic_idx = topic_options.index(url_topic) if url_topic in topic_options else 0
selected_topic = st.sidebar.selectbox("Filtre par sujet :", topic_options, index=topic_idx)
st.query_params["topic"] = selected_topic

# --- FILTRE ÉTABLISSEMENT ---
st.sidebar.header("🏫 Établissement Nantais")
comp_options = ["Tous les établissements"] + list(COMPONENTS_MAP.keys())
url_comp = st.query_params.get("comp", "Tous les établissements")
comp_idx = comp_options.index(url_comp) if url_comp in comp_options else 0
selected_comp = st.sidebar.selectbox("Choisir l'établissement :", comp_options, index=comp_idx)
st.query_params["comp"] = selected_comp

# --- FILTRE UNITÉ DE RECHERCHE ---
st.sidebar.header("🏢 Structure Nantaise")

# 1. Filtre par Pôle
poles_options = ["Tous les pôles"] + sorted(POLES_MAP.keys())
url_pole = st.query_params.get("pole", "Tous les pôles")
pole_idx = poles_options.index(url_pole) if url_pole in poles_options else 0
selected_pole = st.sidebar.selectbox("Filtrer par pôle :", poles_options, index=pole_idx)
st.query_params["pole"] = selected_pole

# 2. Filtre par Unité (dynamique selon le pôle)
if selected_pole != "Tous les pôles":
    allowed_units = POLES_MAP[selected_pole]
    units_sorted = ["Toutes les unités"] + sorted(allowed_units)
else:
    units_sorted = ["Toutes les unités"] + sorted(NANTES_MAP.values())

url_unit = st.query_params.get("unit", "Toutes les unités")
if url_unit not in units_sorted: url_unit = "Toutes les unités"
unit_idx = units_sorted.index(url_unit)
selected_unit = st.sidebar.selectbox("Filtrer par unité nantaise :", units_sorted, index=unit_idx)
st.query_params["unit"] = selected_unit

# --- RECHERCHE PAR CHERCHEUR ---
st.sidebar.header("👤 Chercheur Nantais")
# La liste des auteurs se restreint à l'unité choisie ou au pôle choisi
if selected_unit != "Toutes les unités":
    unit_id = NANTES_LABEL_TO_ID[selected_unit]
    unit_authors_df = df[(df['is_nantes'] == True) & (df['inst_id'].str.contains(unit_id, na=False, regex=False))]
    nantes_authors_list = sorted(unit_authors_df['author'].unique())
elif selected_pole != "Tous les pôles":
    pole_units = POLES_MAP[selected_pole]
    pole_ids = [NANTES_LABEL_TO_ID[u] for u in pole_units if u in NANTES_LABEL_TO_ID]
    regex_pattern = '|'.join(pole_ids)
    unit_authors_df = df[(df['is_nantes'] == True) & (df['inst_id'].str.contains(regex_pattern, na=False, regex=True))]
    nantes_authors_list = sorted(unit_authors_df['author'].unique())
else:
    nantes_authors_list = sorted(df[df['is_nantes'] == True]['author'].unique())

author_options = ["Tous les auteurs"] + nantes_authors_list
if st.session_state.selected_author not in author_options:
    st.session_state.selected_author = "Tous les auteurs"

selected_author = st.sidebar.selectbox(
    "Filtrer par auteur nantais :",
    author_options,
    key="selected_author"
)
st.query_params["author"] = selected_author



# --- FILTRE NOMBRE D'AUTEURS ---
st.sidebar.header("👥 Taille de l'équipe")
author_limit_options = {
    "Tous les effectifs": 1000000,
    "≤ 10 auteurs": 10,
    "≤ 50 auteurs": 50,
    "≤ 100 auteurs": 100,
    "≤ 1000 auteurs": 1000
}
limit_options = list(author_limit_options.keys())
url_limit = st.query_params.get("limit", "Tous les effectifs")
limit_idx = limit_options.index(url_limit) if url_limit in limit_options else 0

selected_limit_label = st.sidebar.selectbox(
    "Filtrer par nombre d'auteurs :", 
    limit_options, 
    index=limit_idx
)
selected_limit_val = author_limit_options[selected_limit_label]
st.query_params["limit"] = selected_limit_label

st.sidebar.markdown("---")
st.sidebar.info("🔗 L'URL de votre navigateur contient vos filtres actuels. Copiez-la pour partager cette vue.")

# --- LOGIQUE DE FILTRAGE FINAL ---
filtered_df = working_df.copy()

# Filtre par année
filtered_df = filtered_df[(filtered_df['year'] >= year_range[0]) & (filtered_df['year'] <= year_range[1])]

# Filtre par nombre d'auteurs
if selected_limit_val < 1000000:
    filtered_df = filtered_df[filtered_df['authors_count'] <= selected_limit_val]

# Filtre par pays
if selected_country != "Tous les pays":
    c_dois = filtered_df[filtered_df['country'].str.contains(selected_country, na=False)]['doi'].unique()
    filtered_df = filtered_df[filtered_df['doi'].isin(c_dois)]
    
if selected_inst != "Tous les établissements":
    i_dois = filtered_df[filtered_df['institution'].str.contains(selected_inst, na=False, regex=False)]['doi'].unique()
    filtered_df = filtered_df[filtered_df['doi'].isin(i_dois)]

# Filtres thématiques
if selected_domain != "Tous les domaines":
    d_dois = filtered_df[filtered_df['domains'].str.contains(selected_domain, na=False, regex=False)]['doi'].unique()
    filtered_df = filtered_df[filtered_df['doi'].isin(d_dois)]

if selected_field != "Toutes les disciplines":
    f_dois = filtered_df[filtered_df['fields'].str.contains(selected_field, na=False, regex=False)]['doi'].unique()
    filtered_df = filtered_df[filtered_df['doi'].isin(f_dois)]

if selected_subfield != "Toutes les sous-disciplines":
    s_dois = filtered_df[filtered_df['subfields'].str.contains(selected_subfield, na=False, regex=False)]['doi'].unique()
    filtered_df = filtered_df[filtered_df['doi'].isin(s_dois)]

if selected_topic != "Tous les sujets":
    t_dois = filtered_df[filtered_df['topics'].str.contains(selected_topic, na=False, regex=False)]['doi'].unique()
    filtered_df = filtered_df[filtered_df['doi'].isin(t_dois)]

# Filtre par établissement
if selected_comp != "Tous les établissements":
    comp_id = COMPONENTS_MAP[selected_comp]
    comp_dois = filtered_df[
        (filtered_df['is_nantes'] == True) &
        (filtered_df['inst_id'].str.contains(comp_id, na=False, regex=False))
    ]['doi'].unique()
    filtered_df = filtered_df[filtered_df['doi'].isin(comp_dois)]

# Filtre structure nantaise (Pôle / Unité)
if selected_unit != "Toutes les unités":
    unit_id = NANTES_LABEL_TO_ID[selected_unit]
    unit_dois = filtered_df[
        (filtered_df['is_nantes'] == True) &
        (filtered_df['inst_id'].str.contains(unit_id, na=False, regex=False, case=False))
    ]['doi'].unique()
    filtered_df = filtered_df[filtered_df['doi'].isin(unit_dois)]
elif selected_pole != "Tous les pôles":
    pole_units = POLES_MAP[selected_pole]
    pole_ids = [NANTES_LABEL_TO_ID[u] for u in pole_units if u in NANTES_LABEL_TO_ID]
    regex_pattern = '|'.join(pole_ids)
    unit_dois = filtered_df[
        (filtered_df['is_nantes'] == True) &
        (filtered_df['inst_id'].str.contains(regex_pattern, na=False, regex=True))
    ]['doi'].unique()
    filtered_df = filtered_df[filtered_df['doi'].isin(unit_dois)]

display_df = filtered_df

# --- AFFICHAGE DES RÉSULTATS ---
# Construction dynamique du titre en fonction des filtres
structure_label = selected_author if selected_author != 'Tous les auteurs' else \
                 selected_unit if selected_unit != 'Toutes les unités' else \
                 selected_pole if selected_pole != 'Tous les pôles' else \
                 selected_comp if selected_comp != 'Tous les établissements' else \
                 "Nantes Université"

geo_label = ""
if selected_country != "Tous les pays":
    country_name = get_country_name(selected_country)
    geo_label += f" — {country_name}"
    if selected_inst != "Tous les établissements":
        geo_label += f" ({selected_inst})"

th_label = ""
if selected_domain != "Tous les domaines":
    th_label += f" — {selected_domain}"
    if selected_field != "Toutes les disciplines":
        th_label += f" > {selected_field}"
        if selected_subfield != "Toutes les sous-disciplines":
            th_label += f" > {selected_subfield}"
            if selected_topic != "Tous les sujets":
                th_label += f" > {selected_topic}"

st.title(f"Collaborations : {structure_label} ({year_range[0]}-{year_range[1]}){geo_label}{th_label}")

st.markdown("""
Ce tableau de bord présente les publications scientifiques co-signées par des membres de **Nantes Université** avec des partenaires internationaux.   
💡 **Conseil :** Utilisez les filtres dans le menu à gauche pour explorer par chercheur ou par zone géographique.
""")

view_options = ["Institutions", "Carte", "Dataviz"]
url_mode = st.query_params.get("mode", "Institutions")
mode_idx = view_options.index(url_mode) if url_mode in view_options else 0

view_mode = st.radio(
    "Mode d'affichage :",
    options=view_options,
    index=mode_idx,
    horizontal=True
)
st.query_params["mode"] = view_mode

st.write("---")

if view_mode == "Dataviz":
    # 1. PAYS PARTENAIRES
    st.write("### 🚩 Pays partenaires")
    paper_countries = display_df[['doi', 'country']].drop_duplicates()
    exploded_countries = paper_countries.assign(country=paper_countries['country'].str.split('|')).explode('country')
    exploded_countries['country'] = exploded_countries['country'].str.strip()
    unique_paper_country = exploded_countries.drop_duplicates()
    valid_countries = unique_paper_country[(unique_paper_country['country'] != 'FR') & (unique_paper_country['country'] != '') & (unique_paper_country['country'] != 'nan')]
    stats_countries = valid_countries['country'].value_counts().reset_index()
    stats_countries.columns = ['country_code', 'count']
    stats_countries = stats_countries[stats_countries['count'] > 0]
    stats_countries['country_name'] = stats_countries['country_code'].apply(get_country_name)
    
    if not stats_countries.empty:
        fig_pie = px.pie(stats_countries, values='count', names='country_name', hole=0.4)
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("Aucune collaboration internationale sur ces critères.")

    st.write("---")
    
    # 2. ÉVOLUTION TEMPORELLE
    st.write("### 📈 Évolution temporelle")
    evo_df = display_df[['doi', 'year']].drop_duplicates()
    evo_stats = evo_df.groupby('year').size().reset_index(name='count')
    if not evo_stats.empty:
        full_years = pd.DataFrame({'year': range(year_range[0], year_range[1] + 1)})
        evo_stats = pd.merge(full_years, evo_stats, on='year', how='left').fillna(0)
        fig_evo = px.line(evo_stats, x='year', y='count', markers=True)
        fig_evo.update_traces(line_color='#2E86C1', line_width=3, marker=dict(size=8))
        fig_evo.update_layout(xaxis_type='category', yaxis_title="Co-publications")
        st.plotly_chart(fig_evo, use_container_width=True)

    st.write("---")

    # 3. ÉTABLISSEMENTS NANTAIS
    st.write("### 🏫 Établissements nantais")
    comp_stats = []
    for name, cid in COMPONENTS_MAP.items():
        count = display_df[(display_df['is_nantes'] == True) & (display_df['inst_id'].str.contains(cid, na=False))]['doi'].nunique()
        if count > 0:
            comp_stats.append({'Établissement': name, 'Publications': count})
    df_comp = pd.DataFrame(comp_stats)
    if not df_comp.empty:
        fig_comp = px.bar(df_comp.sort_values('Publications', ascending=False), x='Publications', y='Établissement', orientation='h', color='Publications', color_continuous_scale='Greens')
        fig_comp.update_layout(yaxis={'categoryorder':'total ascending'}, showlegend=False)
        st.plotly_chart(fig_comp, use_container_width=True)

    st.write("---")

    # 4. PÔLES
    st.write("### 🧬 Pôles")
    pole_stats = []
    for p_name, p_units in POLES_MAP.items():
        p_ids = [NANTES_LABEL_TO_ID[u] for u in p_units if u in NANTES_LABEL_TO_ID]
        regex = '|'.join(p_ids)
        count = display_df[(display_df['is_nantes'] == True) & (display_df['inst_id'].str.contains(regex, na=False))]['doi'].nunique()
        if count > 0:
            pole_stats.append({'Pôle': p_name, 'Publications': count})
    df_pole = pd.DataFrame(pole_stats)
    if not df_pole.empty:
        fig_p = px.bar(df_pole.sort_values('Publications', ascending=False), x='Publications', y='Pôle', orientation='h', color='Publications', color_continuous_scale='Purples')
        fig_p.update_layout(yaxis={'categoryorder':'total ascending'}, showlegend=False)
        st.plotly_chart(fig_p, use_container_width=True)

    st.write("---")

    # 5. UNITÉS DE RECHERCHE
    st.write("### 🏢 Unités de recherche (Labos)")
    nantes_labs_df = display_df[display_df['is_nantes'] == True].copy()
    nantes_labs_df = nantes_labs_df.assign(lab=nantes_labs_df['institution'].str.split('|')).explode('lab')
    nantes_labs_df['lab'] = nantes_labs_df['lab'].str.strip()
    official_labs = set(NANTES_MAP.values())
    lab_stats = nantes_labs_df[nantes_labs_df['lab'].isin(official_labs)].groupby('lab', observed=True)['doi'].nunique().reset_index()
    lab_stats.columns = ['Laboratoire', 'Publications']
    lab_stats = lab_stats[lab_stats['Publications'] > 0].sort_values('Publications', ascending=False)
    if not lab_stats.empty:
        fig_labs = px.bar(lab_stats.head(20), y='Laboratoire', x='Publications', orientation='h', color='Publications', color_continuous_scale='Magma')
        fig_labs.update_layout(yaxis={'categoryorder':'total ascending'}, showlegend=False)
        st.plotly_chart(fig_labs, use_container_width=True)

    st.write("---")

    # 6. AUTEURS NANTAIS
    st.write("### 👥 Auteurs nantais")
    nantes_authors_stats = display_df[display_df['is_nantes'] == True].groupby('author', observed=True)['doi'].nunique().reset_index()
    nantes_authors_stats.columns = ['Auteur', 'Publications']
    nantes_authors_stats = nantes_authors_stats[nantes_authors_stats['Publications'] > 0].sort_values('Publications', ascending=False)
    if not nantes_authors_stats.empty:
        fig_authors = px.bar(nantes_authors_stats.head(15), y='Auteur', x='Publications', orientation='h', color='Publications', color_continuous_scale='Viridis')
        fig_authors.update_layout(yaxis={'categoryorder':'total ascending'}, showlegend=False)
        st.plotly_chart(fig_authors, use_container_width=True)

    st.write("---")

    # FONCTION HELPER POUR LES GRAPHES THÉMATIQUES
    def plot_thematic(df, col, title, color_scale, head=10):
        st.write(f"### {title}")
        paper_data = df[['doi', col]].drop_duplicates()
        exploded = paper_data.assign(val=paper_data[col].str.split('|')).explode('val')
        exploded['val'] = exploded['val'].str.strip()
        stats = exploded[exploded['val'] != ""].groupby('val')['doi'].nunique().reset_index()
        stats.columns = ['Label', 'Publications']
        stats = stats.sort_values('Publications', ascending=False)
        if not stats.empty:
            fig = px.bar(stats.head(head), y='Label', x='Publications', orientation='h', color='Publications', color_continuous_scale=color_scale)
            fig.update_layout(yaxis={'categoryorder':'total ascending'}, showlegend=False, yaxis_title=None)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.write("_Aucune donnée disponible_")

    # 7. DOMAINES
    plot_thematic(display_df, 'domains', "🎓 Domaines", 'Blues')
    st.write("---")
    # 8. DISCIPLINES
    plot_thematic(display_df, 'fields', "📚 Disciplines", 'Teal')
    st.write("---")
    # 9. SOUS-DISCIPLINES
    plot_thematic(display_df, 'subfields', "🧪 Sous-disciplines", 'GnBu')
    st.write("---")
    # 10. SUJETS
    plot_thematic(display_df, 'topics', "🔬 Sujets", 'Reds', head=15)

elif view_mode == "Institutions":
    # Mode : Universités partenaires
    # On utilise explode_parallel_cols pour avoir une liste propre d'institutions et leurs pays
    partner_inst_df = explode_parallel_cols(
        display_df[display_df['is_nantes'] == False][['doi', 'institution', 'country']],
        ['institution', 'country']
    )
    # On nettoie et on filtre (on ne garde que l'étranger, Nantes est la référence)
    partner_inst_df = partner_inst_df[partner_inst_df['institution'] != ""]
    partner_inst_df = partner_inst_df[(partner_inst_df['country'] != "FR") & (partner_inst_df['country'] != "nan") & (partner_inst_df['country'] != "")]
    
    if selected_country != "Tous les pays":
        partner_inst_df = partner_inst_df[partner_inst_df['country'] == selected_country]
    
    inst_stats = partner_inst_df.groupby('institution', observed=True)['doi'].nunique().reset_index()
    inst_stats.columns = ['Institution', 'Publications']
    # Sécurité supplémentaire : on retire les lignes à 0 publications (problème de catégories sparse)
    inst_stats = inst_stats[inst_stats['Publications'] > 0]
    inst_stats = inst_stats.sort_values('Publications', ascending=False)
    
    total_insts = len(inst_stats)
    st.write(f"### 🏫 Institutions ({total_insts})")
    
    ITEMS_PER_PAGE = 20
    total_pages = (total_insts - 1) // ITEMS_PER_PAGE + 1 if total_insts > 0 else 0
    
    if total_pages > 1:
        page_col1, page_col2 = st.columns([1, 1])
        with page_col1:
            current_page = st.number_input(f"Page (sur {total_pages})", min_value=1, max_value=total_pages, step=1, value=1, key='inst_page')
        
        start_idx = (current_page - 1) * ITEMS_PER_PAGE
        end_idx = start_idx + ITEMS_PER_PAGE
        insts_to_show = inst_stats.iloc[start_idx:end_idx]
    else:
        insts_to_show = inst_stats

    for inst_idx, (_, row) in enumerate(insts_to_show.iterrows()):
        inst_name = row['Institution']
        pub_count = row['Publications']
        
        with st.expander(f"🏫 {inst_name} ({pub_count} publications)"):
            inst_dois = partner_inst_df[partner_inst_df['institution'] == inst_name]['doi'].unique()
            relevant_df = display_df[display_df['doi'].isin(inst_dois)]
            
            c1, c2 = st.columns(2)
            with c1:
                st.write("**👤 Chercheurs nantais impliqués :**")
                nantes_res_stats = relevant_df[relevant_df['is_nantes'] == True].groupby('author', observed=True)['doi'].nunique().sort_values(ascending=False).reset_index()
                nantes_res_stats.columns = ['author', 'count']
                nantes_res_stats = nantes_res_stats[nantes_res_stats['count'] > 0]
                res_list = [f"{r['author']} ({r['count']})" for _, r in nantes_res_stats.head(15).iterrows()]
                st.write(", ".join(res_list) + ("..." if len(nantes_res_stats) > 15 else ""))
                
                st.write("**🏢 Labos nantais impliqués :**")
                nantes_labs_df = relevant_df[relevant_df['is_nantes'] == True].copy()
                nantes_labs_df = nantes_labs_df.assign(lab=nantes_labs_df['institution'].str.split('|')).explode('lab')
                nantes_labs_df['lab'] = nantes_labs_df['lab'].str.strip()
                
                # Filtrer pour ne garder QUE les labos officiels de la liste NANTES_MAP
                official_labs = set(NANTES_MAP.values())
                lab_stats = nantes_labs_df[nantes_labs_df['lab'].isin(official_labs)].groupby('lab', observed=True)['doi'].nunique().sort_values(ascending=False).reset_index()
                lab_stats.columns = ['lab', 'count']
                lab_list = [f"{r['lab']} ({r['count']})" for _, r in lab_stats[lab_stats['count'] > 0].iterrows()]
                st.write(", ".join(lab_list) if lab_list else "_Aucun labo officiel identifié_")
                
            with c2:
                render_domains_topics(relevant_df)
            
            st.write("---")
            st.write("**📄 Publications associées :**")
            sorted_dois = relevant_df[['doi', 'year']].drop_duplicates().sort_values('year', ascending=False)['doi'].values
            total_pubs = len(sorted_dois)
            PUB_PAGE_SIZE = 10
            total_pub_pages = max(1, (total_pubs - 1) // PUB_PAGE_SIZE + 1)
            if total_pub_pages > 1:
                pub_page = st.number_input(
                    f"Page publications (sur {total_pub_pages}, {total_pubs} total)",
                    min_value=1, max_value=total_pub_pages, step=1, value=1,
                    key=f"pub_page_inst_{inst_idx}"
                )
                dois_slice = sorted_dois[(pub_page-1)*PUB_PAGE_SIZE : pub_page*PUB_PAGE_SIZE]
            else:
                dois_slice = sorted_dois
            for pub_doi in dois_slice:
                pub_data = relevant_df[relevant_df['doi'] == pub_doi]
                if not pub_data.empty:
                    render_publication(pub_doi, pub_data, selected_author, selected_country)

elif view_mode == "Carte":
    st.write("### 🗺️ Carte des collaborations")
    st.markdown("Cliquez sur une université sur la carte ci-dessous pour filtrer et afficher les détails en-dessous.")
    
    # 1. Extraction et formatage des données géographiques
    df_copy = display_df[display_df['is_nantes'] == False].copy()
    
    map_df = explode_parallel_cols(
        df_copy[['doi', 'institution', 'lat', 'lon', 'country']].rename(columns={'country': 'country_code'}),
        ['institution', 'lat', 'lon', 'country_code']
    )
    # On ne garde que les partenaires étrangers sur la carte
    map_df = map_df[(map_df['institution'] != '') & (map_df['lat'] != '') & (map_df['lon'] != '') & (map_df['country_code'] != 'FR')]
    
    # Filtrer par pays si sélectionné
    if selected_country != "Tous les pays":
        map_df = map_df[map_df['country_code'] == selected_country]

    if map_df.empty:
        st.info("Aucune donnée géographique disponible pour cette sélection.")
    else:
        # Agréger par POSITION (Clustering par coordonnées)
        inst_stats = map_df.groupby(['lat', 'lon', 'country_code']).agg({
            'doi': 'nunique',
            'institution': lambda x: " | ".join(sorted(x.unique()))
        }).reset_index()
        
        inst_stats.columns = ['lat', 'lon', 'country_code', 'Publications', 'All_Institutions']
        
        inst_stats['lat'] = pd.to_numeric(inst_stats['lat'], errors='coerce')
        inst_stats['lon'] = pd.to_numeric(inst_stats['lon'], errors='coerce')
        inst_stats = inst_stats.dropna(subset=['lat', 'lon'])
        inst_stats['Pays'] = inst_stats['country_code'].apply(get_country_name)

        # Créer un libellé lisible pour la carte
        def make_label(row):
            insts = row['All_Institutions'].split(' | ')
            if len(insts) > 1:
                return f"{insts[0]} (+ {len(insts)-1} autres)"
            return insts[0]
        
        inst_stats['Institution_Label'] = inst_stats.apply(make_label, axis=1)
        
        # Calcul du centre et du zoom
        if selected_country != "Tous les pays" and not inst_stats.empty:
            center_lat = inst_stats['lat'].mean()
            center_lon = inst_stats['lon'].mean()
            
            lat_range = inst_stats['lat'].max() - inst_stats['lat'].min()
            lon_range = inst_stats['lon'].max() - inst_stats['lon'].min()
            max_range = max(lat_range, lon_range)
            
            if max_range < 0.1: zoom_level = 9
            elif max_range < 1: zoom_level = 7
            elif max_range < 5: zoom_level = 5
            elif max_range < 15: zoom_level = 3.5
            else: zoom_level = 2.5
        else:
            center_lat, center_lon, zoom_level = 20, 0, 0.5

        # Préparation des données pour le survol (tooltip)
        # On renomme temporairement les colonnes pour que l'affichage soit propre
        inst_stats = inst_stats.rename(columns={
            'Pays': ' ', 
            'Publications': 'publications en commun avec Nantes U'
        })
        
        # Génération de la carte via Plotly Express Mapbox
        fig_map = px.scatter_mapbox(
            inst_stats,
            lat='lat',
            lon='lon',
            size='publications en commun avec Nantes U',
            size_max=30,
            hover_name='Institution_Label',
            custom_data=[' ', 'publications en commun avec Nantes U'],
            color='publications en commun avec Nantes U',
            color_continuous_scale='Turbo',
            zoom=zoom_level,
            center=dict(lat=center_lat, lon=center_lon),
            mapbox_style="open-street-map"
        )
        
        # Définition d'un template de survol propre (hover_template)
        fig_map.update_traces(
            hovertemplate="<b>%{hovertext}</b><br>" +
                          "%{customdata[0]}<br>" +
                          "%{customdata[1]} publications en commun avec Nantes Université<extra></extra>"
        )
        
        fig_map.update_layout(
            margin={"r":0,"t":0,"l":0,"b":0},
            height=600,
            showlegend=False
        )
        
        # Utilisation de on_select pour rendre la carte cliquable
        try:
            event = st.plotly_chart(fig_map, width="stretch", on_select="rerun", selection_mode=("points"), config={'scrollZoom': True})
        except Exception:
            st.plotly_chart(fig_map, width="stretch", config={'scrollZoom': True})
            event = None
        
        st.write("---")
        
        # Logique d'affichage des détails après clic
        if event and hasattr(event, 'selection') and len(event.selection.points) > 0:
            selected_point = event.selection.points[0]
            # On récupère la liste des institutions packagées dans le point
            raw_insts = selected_point.get('customdata', [""])[0]
            selected_inst_names = raw_insts.split(' | ')
            
            st.write(f"### 📍 Détail des institutions à cet emplacement")
            
            # On affiche un bloc distinct (expander) pour chaque institution du groupe
            for idx, inst_name in enumerate(selected_inst_names):
                inst_dois = map_df[map_df['institution'] == inst_name]['doi'].unique()
                relevant_df = display_df[display_df['doi'].isin(inst_dois)]
                pub_count = len(inst_dois)
                
                with st.expander(f"🏫 {inst_name} ({pub_count} publications)", expanded=True):
                    c1, c2 = st.columns(2)
                    with c1:
                        st.write("**👤 Chercheurs nantais impliqués :**")
                        nantes_res_stats = relevant_df[relevant_df['is_nantes'] == True].groupby('author', observed=True)['doi'].nunique().sort_values(ascending=False).reset_index()
                        nantes_res_stats.columns = ['author', 'count']
                        nantes_res_stats = nantes_res_stats[nantes_res_stats['count'] > 0]
                        res_list = [f"{r['author']} ({r['count']})" for _, r in nantes_res_stats.head(15).iterrows()]
                        st.write(", ".join(res_list) + ("..." if len(nantes_res_stats) > 15 else ""))
                        
                        st.write("**🏢 Labos nantais impliqués :**")
                        nantes_labs_df = relevant_df[relevant_df['is_nantes'] == True].copy()
                        nantes_labs_df = nantes_labs_df.assign(lab=nantes_labs_df['institution'].str.split('|')).explode('lab')
                        nantes_labs_df['lab'] = nantes_labs_df['lab'].str.strip()
                        
                        # Filtrer pour ne garder QUE les labos officiels de la liste NANTES_MAP
                        official_labs = set(NANTES_MAP.values())
                        lab_stats = nantes_labs_df[nantes_labs_df['lab'].isin(official_labs)].groupby('lab', observed=True)['doi'].nunique().sort_values(ascending=False).reset_index()
                        lab_stats.columns = ['lab', 'count']
                        lab_list = [f"{r['lab']} ({r['count']})" for _, r in lab_stats[lab_stats['count'] > 0].iterrows()]
                        st.write(", ".join(lab_list) if lab_list else "_Aucun labo officiel identifié_")
                        
                    with c2:
                        render_domains_topics(relevant_df)
                    
                    st.write("---")
                    st.write("**📄 Publications associées :**")
                    sorted_dois = relevant_df[['doi', 'year']].drop_duplicates().sort_values('year', ascending=False)['doi'].values
                    
                    # On affiche les publications sans pagination complexe ici pour plus de clarté
                    for pub_doi in sorted_dois[:10]: # On montre les 10 dernières
                        pub_data = relevant_df[relevant_df['doi'] == pub_doi]
                        if not pub_data.empty:
                            render_publication(pub_doi, pub_data, selected_author, selected_country)
                    
                    if len(sorted_dois) > 10:
                        st.info(f"Et {len(sorted_dois)-10} autres publications...")
        else:
            st.info("👆 Cliquez sur une bulle de la carte pour afficher les détails individuels des universités à cet emplacement.")