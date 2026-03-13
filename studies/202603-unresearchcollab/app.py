import streamlit as st
import pandas as pd
import plotly.express as px
import pycountry
import os

st.set_page_config(page_title="Dashboard Coopération Nantes Université", layout="wide")

# Dictionnaire des unités de recherche nantaises (ID OpenAlex -> libellé)
NANTES_MAP = {
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
# Mapping inverse : libellé -> ID
NANTES_LABEL_TO_ID = {v: k for k, v in NANTES_MAP.items()}

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
year_range = st.sidebar.slider(
    "Sélectionner la plage d'années :",
    min_value=2020,
    max_value=2025,
    value=(2020, 2025) # Valeur par défaut
)

# On filtre par année immédiatement pour alléger la suite
working_df = df[(df['year'] >= year_range[0]) & (df['year'] <= year_range[1])]

# On initialise working_df avec les données de base (ou filtrées par auteur si déjà sélectionné)
if 'selected_author' not in st.session_state:
    st.session_state.selected_author = "Tous les auteurs"

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

selected_country = st.sidebar.selectbox(
    "Choisir un pays partenaire :", 
    ["Tous les pays"] + available_countries,
    format_func=lambda x: f"{get_country_name(x)} ({country_counts[x]})" if x != "Tous les pays" else x
)

# Sous-filtre établissement (uniquement si pays choisi)
selected_inst = "Tous les établissements"
if selected_country != "Tous les pays":
    # On n'affiche que les institutions du pays sélectionné
    temp_inst_df = explode_parallel_cols(
        working_df[working_df['country'].str.contains(selected_country, na=False)][['doi', 'institution', 'country']],
        ['institution', 'country']
    )
    available_insts = sorted(temp_inst_df[temp_inst_df['country'] == selected_country]['institution'].unique())
    selected_inst = st.sidebar.selectbox("Choisir un établissement :", ["Tous les établissements"] + available_insts)

# --- FILTRES THÉMATIQUES HIÉRARCHIQUES ---
st.sidebar.header("🎯 Filtres Thématiques")

# 1. Domaines
all_domains = sorted(working_df['domains'].str.split('|').explode().str.strip().dropna().unique())
if 'nan' in all_domains: all_domains.remove('nan')
selected_domain = st.sidebar.selectbox("Filtre par domaine :", ["Tous les domaines"] + all_domains)

# 2. Disciplines (Fields) - Cascade
temp_df_fields = working_df
if selected_domain != "Tous les domaines":
    temp_df_fields = working_df[working_df['domains'].str.contains(selected_domain, na=False, regex=False)]
all_fields = sorted(temp_df_fields['fields'].str.split('|').explode().str.strip().dropna().unique())
if 'nan' in all_fields: all_fields.remove('nan')
selected_field = st.sidebar.selectbox("Filtre par discipline :", ["Toutes les disciplines"] + all_fields)

# 3. Sous-disciplines (Subfields) - Cascade
temp_df_subfields = temp_df_fields
if selected_field != "Toutes les disciplines":
    temp_df_subfields = temp_df_fields[temp_df_fields['fields'].str.contains(selected_field, na=False, regex=False)]
all_subfields = sorted(temp_df_subfields['subfields'].str.split('|').explode().str.strip().dropna().unique())
if 'nan' in all_subfields: all_subfields.remove('nan')
selected_subfield = st.sidebar.selectbox("Filtre par sous-discipline :", ["Toutes les sous-disciplines"] + all_subfields)

# 4. Sujets (Topics) - Cascade
temp_df_topics = temp_df_subfields
if selected_subfield != "Toutes les sous-disciplines":
    temp_df_topics = temp_df_subfields[temp_df_subfields['subfields'].str.contains(selected_subfield, na=False, regex=False)]
all_topics = sorted(temp_df_topics['topics'].str.split('|').explode().str.strip().dropna().unique())
if 'nan' in all_topics: all_topics.remove('nan')
selected_topic = st.sidebar.selectbox("Filtre par sujet :", ["Tous les sujets"] + all_topics)

# --- FILTRE UNITÉ DE RECHERCHE ---
st.sidebar.header("🏢 Unité de recherche")
units_sorted = ["Toutes les unités"] + sorted(NANTES_MAP.values())
selected_unit = st.sidebar.selectbox("Filtrer par unité nantaise :", units_sorted)

# --- RECHERCHE PAR CHERCHEUR ---
st.sidebar.header("👤 Chercheur Nantais")
# La liste des auteurs se restreint à l'unité choisie si applicable
if selected_unit != "Toutes les unités":
    unit_id = NANTES_LABEL_TO_ID[selected_unit]
    unit_authors_df = df[(df['is_nantes'] == True) & (df['inst_id'].str.contains(unit_id, na=False, regex=False))]
    nantes_authors_list = sorted(unit_authors_df['author'].unique())
else:
    nantes_authors_list = sorted(df[df['is_nantes'] == True]['author'].unique())

selected_author = st.sidebar.selectbox(
    "Filtrer par auteur nantais :",
    ["Tous les auteurs"] + nantes_authors_list,
    key="selected_author"
)

# --- FILTRE NOMBRE D'AUTEURS ---
st.sidebar.header("👥 Taille de l'équipe")
author_limit_options = {
    "Tous les effectifs": 1000000,
    "≤ 10 auteurs": 10,
    "≤ 50 auteurs": 50,
    "≤ 100 auteurs": 100,
    "≤ 1000 auteurs": 1000
}
selected_limit_label = st.sidebar.selectbox("Filtrer par nombre d'auteurs :", list(author_limit_options.keys()), index=0)
selected_limit_val = author_limit_options[selected_limit_label]

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

# Filtre unité de recherche : on garde les DOI où au moins un auteur nantais est de l'unité
if selected_unit != "Toutes les unités":
    unit_id = NANTES_LABEL_TO_ID[selected_unit]
    unit_dois = filtered_df[
        (filtered_df['is_nantes'] == True) &
        (filtered_df['inst_id'].str.contains(unit_id, na=False, regex=False, case=False))
    ]['doi'].unique()
    filtered_df = filtered_df[filtered_df['doi'].isin(unit_dois)]

display_df = filtered_df

# --- AFFICHAGE DES RÉSULTATS ---
st.title(f"Collaborations : "
         f"{selected_author if selected_author != 'Tous les auteurs' else selected_unit if selected_unit != 'Toutes les unités' else 'Nantes Université'}"
         f" ({year_range[0]}-{year_range[1]})")

st.markdown("""
Ce tableau de bord présente les publications scientifiques co-signées par des membres de **Nantes Université** avec des partenaires internationaux.   
💡 **Conseil :** Utilisez les filtres dans le menu à gauche pour explorer par chercheur ou par zone géographique.
""")

view_mode = st.radio(
    "Mode d'affichage :",
    options=["Institutions", "Carte", "Dataviz"],
    horizontal=True
)

st.write("---")

if view_mode == "Dataviz":
    st.write("### 🚩 Pays partenaires")
    # On s'assure de ne compter chaque pays qu'une seule fois par publication
    # 1. On récupère les couples (DOI, liste de pays) uniques
    paper_countries = display_df[['doi', 'country']].drop_duplicates()
    # 2. On éclate les pays et on dédoublonne pour avoir des couples (DOI, pays) uniques
    exploded_countries = paper_countries.assign(country=paper_countries['country'].str.split('|')).explode('country')
    exploded_countries['country'] = exploded_countries['country'].str.strip()
    unique_paper_country = exploded_countries.drop_duplicates()
    
    # 3. On compte et on exclut la France et les valeurs vides
    valid_countries = unique_paper_country[(unique_paper_country['country'] != 'FR') & (unique_paper_country['country'] != '') & (unique_paper_country['country'] != 'nan')]
    stats_countries = valid_countries['country'].value_counts().reset_index()
    stats_countries.columns = ['country_code', 'count']
    stats_countries['country_name'] = stats_countries['country_code'].apply(get_country_name)
    
    if not stats_countries.empty:
        fig_pie = px.pie(stats_countries, values='count', names='country_name', hole=0.4)
        st.plotly_chart(fig_pie, width="stretch")
    else:
        st.info("Aucune collaboration internationale sur ces critères.")

    st.write("---")
    st.write("### 👥 Auteurs Nantais")
    # Compter les publications uniques (par DOI) par auteurs nantais dans les données filtrées
    nantes_authors_stats = display_df[display_df['is_nantes'] == True].groupby('author')['doi'].nunique().reset_index()
    nantes_authors_stats.columns = ['Auteur', 'Publications']
    nantes_authors_stats = nantes_authors_stats.sort_values('Publications', ascending=False)
    
    if not nantes_authors_stats.empty:
        # On limite aux 15 premiers pour la lisibilité
        top_nantes_authors = nantes_authors_stats.head(15)
        fig_authors = px.bar(
            top_nantes_authors, 
            y='Auteur', 
            x='Publications', 
            orientation='h',
            color='Publications',
            color_continuous_scale='Viridis'
        )
        fig_authors.update_layout(yaxis={'categoryorder':'total ascending'}, showlegend=False)
        st.plotly_chart(fig_authors, width="stretch")
    else:
        st.info("Aucun auteur nantais trouvé.")

    st.write("---")
    st.write("### 🎓 Domaines (Subfields)")
    paper_subfields = display_df[['doi', 'subfields']].drop_duplicates()
    exploded_subfields = paper_subfields.assign(subfields=paper_subfields['subfields'].str.split('|')).explode('subfields')
    stats_subfields = exploded_subfields['subfields'].str.strip().value_counts().reset_index()
    stats_subfields.columns = ['Domaine', 'Publications']
    
    if not stats_subfields.empty:
        fig_sub = px.bar(stats_subfields.head(10), y='Domaine', x='Publications', orientation='h', color='Publications', color_continuous_scale='Blues')
        fig_sub.update_layout(yaxis={'categoryorder':'total ascending'}, showlegend=False)
        st.plotly_chart(fig_sub, width="stretch")

    st.write("---")
    st.write("### 🔬 Sujets (Topics)")
    paper_topics = display_df[['doi', 'topics']].drop_duplicates()
    exploded_topics = paper_topics.assign(topics=paper_topics['topics'].str.split('|')).explode('topics')
    stats_topics = exploded_topics['topics'].str.strip().value_counts().reset_index()
    stats_topics.columns = ['Sujet', 'Publications']
    
    if not stats_topics.empty:
        fig_top = px.bar(stats_topics.head(10), y='Sujet', x='Publications', orientation='h', color='Publications', color_continuous_scale='Reds')
        fig_top.update_layout(yaxis={'categoryorder':'total ascending'}, showlegend=False)
        st.plotly_chart(fig_top, width="stretch")
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
    
    inst_stats = partner_inst_df.groupby('institution')['doi'].nunique().reset_index()
    inst_stats.columns = ['Institution', 'Publications']
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
                nantes_researchers_stats = relevant_df[relevant_df['is_nantes'] == True].groupby('author')['doi'].nunique().sort_values(ascending=False).reset_index()
                nantes_researchers_stats.columns = ['author', 'count']
                
                display_list = []
                for _, res_row in nantes_researchers_stats.head(15).iterrows():
                    display_list.append(f"{res_row['author']} ({res_row['count']})")
                
                st.write(", ".join(display_list) + ("..." if len(nantes_researchers_stats) > 15 else ""))
                
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

        # Génération de la carte via Plotly Express Mapbox
        fig_map = px.scatter_mapbox(
            inst_stats,
            lat='lat',
            lon='lon',
            size='Publications',
            size_max=30,
            hover_name='Institution_Label',
            hover_data={
                'lat': False, 
                'lon': False, 
                'country_code': False, 
                'Pays': True, 
                'Publications': True,
                'All_Institutions': True
            },
            custom_data=['All_Institutions', 'Publications', 'Pays'],
            color='Publications',
            color_continuous_scale='Turbo',
            zoom=zoom_level,
            center=dict(lat=center_lat, lon=center_lon),
            mapbox_style="open-street-map"
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
            st.warning("La sélection sur carte n'est pas supportée par votre version de Streamlit.")
        
        st.write("---")
        
        # Logique d'affichage des détails après clic
        if event and hasattr(event, 'selection') and len(event.selection.points) > 0:
            selected_point = event.selection.points[0]
            # On récupère la liste des institutions packagées dans le point
            raw_insts = selected_point.get('customdata', [""])[0]
            selected_inst_names = raw_insts.split(' | ')
            
            pub_count = selected_point.get('customdata', [0, 0])[1]
            
            label_title = selected_inst_names[0] + (f" (+ {len(selected_inst_names)-1} autres)" if len(selected_inst_names) > 1 else "")
            st.write(f"### 📍 {label_title}")
            if len(selected_inst_names) > 1:
                st.info(f"Ce point regroupe : {', '.join(selected_inst_names)}")
            
            # Filtrer les DOIs pour TOUTES les institutions du cluster
            inst_dois = map_df[map_df['institution'].isin(selected_inst_names)]['doi'].unique()
            relevant_df = display_df[display_df['doi'].isin(inst_dois)]
            
            c1, c2 = st.columns(2)
            with c1:
                st.write("**👤 Chercheurs nantais impliqués :**")
                nantes_researchers_stats = relevant_df[relevant_df['is_nantes'] == True].groupby('author')['doi'].nunique().sort_values(ascending=False).reset_index()
                nantes_researchers_stats.columns = ['author', 'count']
                
                display_list = []
                for _, res_row in nantes_researchers_stats.head(15).iterrows():
                    display_list.append(f"{res_row['author']} ({res_row['count']})")
                
                st.write(", ".join(display_list) + ("..." if len(nantes_researchers_stats) > 15 else ""))
                
            with c2:
                render_domains_topics(relevant_df)
            
            st.write("**📄 Publications associées :**")
            sorted_dois = relevant_df[['doi', 'year']].drop_duplicates().sort_values('year', ascending=False)['doi'].values
            total_pubs = len(sorted_dois)
            PUB_PAGE_SIZE = 10
            total_pub_pages = max(1, (total_pubs - 1) // PUB_PAGE_SIZE + 1)
            if total_pub_pages > 1:
                pub_page = st.number_input(
                    f"Page publications (sur {total_pub_pages}, {total_pubs} total)",
                    min_value=1, max_value=total_pub_pages, step=1, value=1,
                    key="pub_page_carte"
                )
                dois_slice = sorted_dois[(pub_page-1)*PUB_PAGE_SIZE : pub_page*PUB_PAGE_SIZE]
            else:
                dois_slice = sorted_dois
            for pub_doi in dois_slice:
                pub_data = relevant_df[relevant_df['doi'] == pub_doi]
                if not pub_data.empty:
                    render_publication(pub_doi, pub_data, selected_author, selected_country)
            else:
                st.info("👆 Cliquez sur une bulle de la carte pour afficher les détails des partenariats avec cette université.")