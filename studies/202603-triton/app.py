import streamlit as st
import pandas as pd
import plotly.express as px
import pycountry
import os

st.set_page_config(page_title="Dashboard Coopération LS2N", layout="wide")

def get_country_name(code):
    try:
        if code == 'UK':
            return 'United Kingdom'
        c = pycountry.countries.get(alpha_2=code)
        return c.name if c else code
    except:
        return code

@st.cache_data
def load_data():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, "cooperations_ls2n.parquet")
    df = pd.read_parquet(file_path)
    # On s'assure que les noms sont bien formatés pour la recherche
    df['author'] = df['author'].fillna("Inconnu")
    
    # Sécurité : si le cache Streamlit est ancien et n'a pas les colonnes topics ou subfields
    if 'topics' not in df.columns:
        df['topics'] = ""
    if 'subfields' not in df.columns:
        df['subfields'] = ""
        
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

# On initialise working_df avec les données de base (ou filtrées par auteur si déjà sélectionné)
if 'selected_author' not in st.session_state:
    st.session_state.selected_author = st.query_params.get("author", "Tous les auteurs")

if st.session_state.selected_author != "Tous les auteurs":
    author_dois = df[df['author'] == st.session_state.selected_author]['doi'].unique()
    working_df = df[df['doi'].isin(author_dois)]
else:
    working_df = df

# --- FILTRE PAYS (Dynamique selon l'auteur choisi) ---
st.sidebar.header("🌍 Filtre Géographique")
# On "explose" les pays pour avoir une liste propre d'individus
all_countries_series = working_df['country'].str.split('|').explode().str.strip()
available_countries = sorted(all_countries_series[all_countries_series != 'FR'].dropna().unique())

country_options = ["Tous les pays"] + available_countries
url_country = st.query_params.get("country", "Tous les pays")
country_idx = country_options.index(url_country) if url_country in country_options else 0

selected_country = st.sidebar.selectbox(
    "Choisir un pays partenaire :", 
    country_options,
    index=country_idx,
    format_func=lambda x: get_country_name(x) if x != "Tous les pays" else x
)
st.query_params["country"] = selected_country

# Sous-filtre établissement (uniquement si pays choisi)
selected_inst = "Tous les établissements"
if selected_country != "Tous les pays":
    country_mask = working_df['country'].str.contains(selected_country, na=False)
    all_insts = working_df[country_mask]['institution'].str.split('|').explode().str.strip()
    available_insts = sorted(all_insts.dropna().unique())
    inst_options = ["Tous les établissements"] + available_insts
url_inst = st.query_params.get("inst", "Tous les établissements")
inst_idx = inst_options.index(url_inst) if url_inst in inst_options else 0
selected_inst = st.sidebar.selectbox("Choisir un établissement :", inst_options, index=inst_idx)
st.query_params["inst"] = selected_inst

# --- FILTRE DOMAINE (Subfields) ---
st.sidebar.header("🎓 Domaine de recherche")
all_subfields_series = working_df['subfields'].str.split('|').explode().str.strip()
available_subfields = sorted(all_subfields_series.dropna().unique())
subfield_options = ["Tous les domaines"] + available_subfields
url_subfield = st.query_params.get("subfield", "Tous les domaines")
subfield_idx = subfield_options.index(url_subfield) if url_subfield in subfield_options else 0
selected_subfield = st.sidebar.selectbox("Choisir un domaine :", subfield_options, index=subfield_idx)
st.query_params["subfield"] = selected_subfield

# --- FILTRE SUJET (Topics) ---
st.sidebar.header("🔬 Sujet de recherche")
# Filtrer les thèmes disponibles selon le domaine choisi pour plus de pertinence
temp_df = working_df
if selected_subfield != "Tous les domaines":
    temp_df = working_df[working_df['subfields'].str.contains(selected_subfield, na=False, regex=False)]

all_topics_series = temp_df['topics'].str.split('|').explode().str.strip()
available_topics = sorted(all_topics_series.dropna().unique())
topic_options = ["Tous les sujets"] + available_topics
url_topic = st.query_params.get("topic", "Tous les sujets")
topic_idx = topic_options.index(url_topic) if url_topic in topic_options else 0
selected_topic = st.sidebar.selectbox("Choisir un sujet :", topic_options, index=topic_idx)
st.query_params["topic"] = selected_topic

# --- RECHERCHE PAR CHERCHEUR (Déplacé en bas) ---
st.sidebar.header("👤 Chercheur Nantais")
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

st.sidebar.markdown("---")
st.sidebar.info("🔗 L'URL de votre navigateur contient vos filtres actuels. Copiez-la pour partager cette vue.")

# --- LOGIQUE DE FILTRAGE FINAL ---
filtered_df = working_df.copy()

# Filtre par année
filtered_df = filtered_df[(filtered_df['year'] >= year_range[0]) & (filtered_df['year'] <= year_range[1])]

if selected_country != "Tous les pays":
    c_dois = filtered_df[filtered_df['country'].str.contains(selected_country, na=False)]['doi'].unique()
    filtered_df = filtered_df[filtered_df['doi'].isin(c_dois)]
    
if selected_inst != "Tous les établissements":
    i_dois = filtered_df[filtered_df['institution'].str.contains(selected_inst, na=False, regex=False)]['doi'].unique()
    filtered_df = filtered_df[filtered_df['doi'].isin(i_dois)]

if selected_subfield != "Tous les domaines":
    s_dois = filtered_df[filtered_df['subfields'].str.contains(selected_subfield, na=False, regex=False)]['doi'].unique()
    filtered_df = filtered_df[filtered_df['doi'].isin(s_dois)]

if selected_topic != "Tous les sujets":
    t_dois = filtered_df[filtered_df['topics'].str.contains(selected_topic, na=False, regex=False)]['doi'].unique()
    filtered_df = filtered_df[filtered_df['doi'].isin(t_dois)]

display_df = filtered_df

# --- AFFICHAGE DES RÉSULTATS ---
st.title(f"Collaborations : {selected_author if selected_author != 'Tous les auteurs' else 'LS2N'} ({year_range[0]}-{year_range[1]})")

st.markdown("""
Ce tableau de bord présente les publications scientifiques co-signées par des membres du **LS2N** avec des partenaires internationaux. 
💡 **Conseil :** Utilisez les filtres dans le menu à gauche pour explorer par chercheur ou par zone géographique.
""")

col1, col2 = st.columns([1, 2])

with col1:
    st.write("### 🚩 Pays partenaires")
    # On s'assure de ne compter chaque pays qu'une seule fois par publication
    # 1. On récupère les couples (DOI, liste de pays) uniques
    paper_countries = display_df[['doi', 'country']].drop_duplicates()
    # 2. On éclate les pays et on dédoublonne pour avoir des couples (DOI, pays) uniques
    exploded_countries = paper_countries.assign(country=paper_countries['country'].str.split('|')).explode('country')
    exploded_countries['country'] = exploded_countries['country'].str.strip()
    unique_paper_country = exploded_countries.drop_duplicates()
    
    # 3. On compte et on exclut la France
    stats_countries = unique_paper_country[unique_paper_country['country'] != 'FR']['country'].value_counts().reset_index()
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

with col2:
    view_options = ["Par Publications", "Par Universités partenaires", "Par Carte"]
    url_mode = st.query_params.get("mode", "Par Publications")
    mode_idx = view_options.index(url_mode) if url_mode in view_options else 0

    view_mode = st.radio(
        "Mode d'affichage :",
        options=view_options,
        index=mode_idx,
        horizontal=True
    )
    st.query_params["mode"] = view_mode
    
    st.write("---")

    if view_mode == "Par Publications":
        dois = display_df['doi'].dropna().unique()
        total_items = len(dois)
        ITEMS_PER_PAGE = 20
        total_pages = (total_items - 1) // ITEMS_PER_PAGE + 1 if total_items > 0 else 0
    
        st.write(f"### 📄 Publications ({total_items})")
        
        if total_pages > 1:
            # On utilise une colonne pour centrer le sélecteur de page ou le mettre discrètement
            page_col1, page_col2 = st.columns([1, 1])
            with page_col1:
                current_page = st.number_input(f"Page (sur {total_pages})", min_value=1, max_value=total_pages, step=1, value=1)
            
            start_idx = (current_page - 1) * ITEMS_PER_PAGE
            end_idx = start_idx + ITEMS_PER_PAGE
            dois_to_show = dois[start_idx:end_idx]
        else:
            dois_to_show = dois
    
        for doi in dois_to_show:
            work_data = display_df[display_df['doi'] == doi]
            if work_data.empty:
                continue
                
            title = work_data['title'].iloc[0] if not pd.isna(work_data['title'].iloc[0]) else "Sans titre"
            year = work_data['year'].iloc[0]
            
            with st.expander(f"({year}) {title}"):
                c1, c2 = st.columns(2)
                with c1:
                    st.write("**Équipe Nantes :**")
                    n_auths = work_data[work_data['is_nantes'] == True]
                    for _, r in n_auths.iterrows():
                        style = f"**{r['author']}**" if r['author'] == selected_author else r['author']
                        # On affiche les institutions proprement même si plusieurs
                        inst_label = r['institution'].replace('|', ' / ')
                        st.write(f"👤 {style}  \n*{inst_label}*")
                with c2:
                    st.write("**Partenaires Internationaux :**")
                    # Un auteur est étranger s'il a au moins un pays qui n'est pas FR
                    f_auths = work_data[work_data['country'].str.contains(r'^(?!FR$)', regex=True, na=False)]
                    for _, r in f_auths.iterrows():
                        # Filtrer pour ne montrer que les pays non-FR de cet auteur
                        other_countries = [get_country_name(c) for c in str(r['country']).split('|') if c != 'FR']
                        countries_label = ", ".join(other_countries)
                        inst_label = r['institution'].replace('|', ' / ')
                        st.write(f"🌎 {r['author']}  \n*{inst_label}* ({countries_label})")
                
                # Affichage des Domaines et Thèmes (Subfields & Topics)
                if ('subfields' in work_data.columns and not pd.isna(work_data['subfields'].iloc[0])) or \
                   ('topics' in work_data.columns and not pd.isna(work_data['topics'].iloc[0])):
                    st.write("---")
                    
                    if 'subfields' in work_data.columns and not pd.isna(work_data['subfields'].iloc[0]):
                        subfields_list = work_data['subfields'].iloc[0].split('|')
                        st.write("🎓 **Domaines de recherche :**")
                        st.write(", ".join(subfields_list))
                    
                    if 'topics' in work_data.columns and not pd.isna(work_data['topics'].iloc[0]):
                        topics_list = work_data['topics'].iloc[0].split('|')
                        st.write("🔬 **Sujets de recherche :**")
                        st.write(", ".join(topics_list))
                
                openalex_id = work_data['work_id'].iloc[0]
                st.caption(f"**DOI:** [{doi}]({doi}) | **OpenAlex:** [{openalex_id}](https://openalex.org/works/{openalex_id})")

    elif view_mode == "Par Universités partenaires":
        # Mode : Universités partenaires
        partner_inst_df = display_df[display_df['is_nantes'] == False][['doi', 'institution']].copy()
        partner_inst_df['institution'] = partner_inst_df['institution'].fillna("")
        partner_inst_df = partner_inst_df.assign(institution=partner_inst_df['institution'].str.split('|')).explode('institution')
        partner_inst_df['institution'] = partner_inst_df['institution'].str.strip()
        partner_inst_df = partner_inst_df[partner_inst_df['institution'] != ""]
        
        inst_stats = partner_inst_df.groupby('institution')['doi'].nunique().reset_index()
        inst_stats.columns = ['Institution', 'Publications']
        inst_stats = inst_stats.sort_values('Publications', ascending=False)
        
        total_insts = len(inst_stats)
        st.write(f"### 🏫 Universités partenaires ({total_insts})")
        
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

        for _, row in insts_to_show.iterrows():
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
                    st.write("**🎓 Domaines de recherche :**")
                    domains = relevant_df['subfields'].str.split('|').explode().str.strip()
                    domains = sorted(domains[domains != ""].dropna().unique())
                    st.write(", ".join(domains[:5]) + ("..." if len(domains) > 5 else ""))
                    
                    st.write("**🔬 Sujets de recherche :**")
                    topics = relevant_df['topics'].str.split('|').explode().str.strip()
                    topics = sorted(topics[topics != ""].dropna().unique())
                    st.write(", ".join(topics[:5]) + ("..." if len(topics) > 5 else ""))
                
                st.write("---")
                st.write("**📄 Publications associées :**")
                unique_pubs = relevant_df[['doi', 'year', 'title']].drop_duplicates().sort_values('year', ascending=False)
                for _, pub_row in unique_pubs.iterrows():
                    pub_title = pub_row['title'] if not pd.isna(pub_row['title']) else "Sans titre"
                    st.markdown(f"- ({pub_row['year']}) [{pub_title}]({pub_row['doi']})")

    elif view_mode == "Par Carte":
        st.write("### 🗺️ Carte des Universités")
        st.markdown("Cliquez sur une université sur la carte ci-dessous pour filtrer et afficher les détails en-dessous.")
        
        # 1. Extraction et formatage des données géographiques
        df_copy = display_df[display_df['is_nantes'] == False].copy()
        
        # Eclater les colonnes parallèles
        records = []
        for _, row in df_copy.iterrows():
            insts = str(row['institution']).split('|')
            lats = str(row.get('lat', '')).split('|')
            lons = str(row.get('lon', '')).split('|')
            countries = str(row['country']).split('|')
            
            # Alignement en cas d'erreur de dimension
            max_len = max(len(insts), len(lats), len(lons), len(countries))
            insts += [''] * (max_len - len(insts))
            lats += [''] * (max_len - len(lats))
            lons += [''] * (max_len - len(lons))
            countries += [''] * (max_len - len(countries))
            
            for i, inst in enumerate(insts):
                inst = inst.strip()
                if inst and lats[i].strip() and lons[i].strip():
                    records.append({
                        'doi': row['doi'],
                        'institution': inst,
                        'lat': lats[i].strip(),
                        'lon': lons[i].strip(),
                        'country_code': countries[i].strip()
                    })
                    
        map_df = pd.DataFrame(records)
        
        if map_df.empty:
            st.info("Aucune donnée géographique disponible pour cette sélection.")
        else:
            # Agréger par institution
            inst_stats = map_df.groupby(['institution', 'lat', 'lon', 'country_code'])['doi'].nunique().reset_index()
            inst_stats.columns = ['Institution', 'lat', 'lon', 'country_code', 'Publications']
            
            inst_stats['lat'] = pd.to_numeric(inst_stats['lat'], errors='coerce')
            inst_stats['lon'] = pd.to_numeric(inst_stats['lon'], errors='coerce')
            inst_stats = inst_stats.dropna(subset=['lat', 'lon'])
            inst_stats['Pays'] = inst_stats['country_code'].apply(get_country_name)
            
            # Génération de la carte via Plotly Express
            fig_map = px.scatter_geo(
                inst_stats,
                lat='lat',
                lon='lon',
                size='Publications',
                size_max=30,
                hover_name='Institution',
                custom_data=['Institution', 'Publications', 'Pays'],
                color='Publications',
                color_continuous_scale='Turbo',
                projection="natural earth"
            )
            # Améliorer le tooltip
            fig_map.update_traces(
                hovertemplate="<b>%{customdata[0]}</b><br>Pays: %{customdata[2]}<br>Publications: %{customdata[1]}<extra></extra>"
            )
            fig_map.update_layout(
                margin={"r":0,"t":0,"l":0,"b":0},
                geo=dict(showcoastlines=True, coastlinecolor="LightBlue", showland=True, landcolor="WhiteSmoke", showocean=True, oceancolor="AliceBlue")
            )
            
            # Utilisation de on_select pour rendre la carte cliquable (disponible depuis Streamlit 1.35)
            try:
                event = st.plotly_chart(fig_map, width="stretch", on_select="rerun", selection_mode=("points"))
            except Exception:
                # Fallback pour les anciennes versions de Streamlit
                st.plotly_chart(fig_map, width="stretch")
                event = None
                st.warning("La sélection sur carte n'est pas supportée par votre version de Streamlit.")
            
            st.write("---")
            
            # Logique d'affichage des détails après clic
            if event and len(event.selection.points) > 0:
                # Les points sont retournés sous forme de dictionnaires dans les versions récentes
                selected_point = event.selection.points[0]
                selected_inst_name = selected_point['customdata'][0]
                pub_count = selected_point['customdata'][1]
                
                st.write(f"### 🏫 {selected_inst_name} ({pub_count} publications)")
                
                inst_dois = map_df[map_df['institution'] == selected_inst_name]['doi'].unique()
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
                    st.write("**🎓 Domaines de recherche :**")
                    domains = relevant_df['subfields'].str.split('|').explode().str.strip()
                    domains = sorted(domains[domains != ""].dropna().unique())
                    st.write(", ".join(domains[:5]) + ("..." if len(domains) > 5 else ""))
                    
                    st.write("**🔬 Sujets de recherche :**")
                    topics = relevant_df['topics'].str.split('|').explode().str.strip()
                    topics = sorted(topics[topics != ""].dropna().unique())
                    st.write(", ".join(topics[:5]) + ("..." if len(topics) > 5 else ""))
                
                st.write("**📄 Publications associées :**")
                unique_pubs = relevant_df[['doi', 'year', 'title']].drop_duplicates().sort_values('year', ascending=False)
                for _, pub_row in unique_pubs.iterrows():
                    pub_title = pub_row['title'] if not pd.isna(pub_row['title']) else "Sans titre"
                    st.markdown(f"- ({pub_row['year']}) [{pub_title}]({pub_row['doi']})")
                    
            else:
                st.info("👆 Cliquez sur une bulle de la carte pour afficher les détails des partenariats avec cette université.")