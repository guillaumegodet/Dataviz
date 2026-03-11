import streamlit as st
import pandas as pd
import plotly.express as px
import pycountry
import os

st.set_page_config(page_title="Dashboard Coopération Nantes", layout="wide")

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

# --- SIDEBAR : RECHERCHE PAR AUTEUR NANTAIS ---
st.sidebar.header("🔍 Recherche par Chercheur")

nantes_authors_list = sorted(df[df['is_nantes'] == True]['author'].unique())
selected_author = st.sidebar.selectbox(
    "Choisir un auteur nantais :",
    ["Tous les auteurs"] + nantes_authors_list
)

# --- LOGIQUE DE FILTRAGE PAR AUTEUR ---
if selected_author != "Tous les auteurs":
    author_dois = df[df['author'] == selected_author]['doi'].unique()
    working_df = df[df['doi'].isin(author_dois)]
    st.sidebar.success(f"Affichage des coopérations pour : {selected_author}")
else:
    working_df = df

# --- FILTRE PAYS (Dynamique selon l'auteur choisi) ---
st.sidebar.header("🌍 Filtre Géographique")
# On "explose" les pays pour avoir une liste propre d'individus
all_countries_series = working_df['country'].str.split('|').explode().str.strip()
available_countries = sorted(all_countries_series[all_countries_series != 'FR'].dropna().unique())

selected_country = st.sidebar.selectbox(
    "Choisir un pays partenaire :", 
    ["Tous les pays"] + available_countries,
    format_func=lambda x: get_country_name(x) if x != "Tous les pays" else x
)

# Sous-filtre établissement (uniquement si pays choisi)
selected_inst = "Tous les établissements"
if selected_country != "Tous les pays":
    country_mask = working_df['country'].str.contains(selected_country, na=False)
    all_insts = working_df[country_mask]['institution'].str.split('|').explode().str.strip()
    available_insts = sorted(all_insts.dropna().unique())
    selected_inst = st.sidebar.selectbox("Choisir un établissement :", ["Tous les établissements"] + available_insts)

# --- FILTRE DOMAINE (Subfields) ---
st.sidebar.header("🎓 Domaine de recherche")
all_subfields_series = working_df['subfields'].str.split('|').explode().str.strip()
available_subfields = sorted(all_subfields_series.dropna().unique())
selected_subfield = st.sidebar.selectbox("Choisir un domaine :", ["Tous les domaines"] + available_subfields)

# --- FILTRE THÈME (Topics) ---
st.sidebar.header("🔬 Thème de recherche")
# Filtrer les thèmes disponibles selon le domaine choisi pour plus de pertinence
temp_df = working_df
if selected_subfield != "Tous les domaines":
    temp_df = working_df[working_df['subfields'].str.contains(selected_subfield, na=False, regex=False)]

all_topics_series = temp_df['topics'].str.split('|').explode().str.strip()
available_topics = sorted(all_topics_series.dropna().unique())
selected_topic = st.sidebar.selectbox("Choisir un thème :", ["Tous les thèmes"] + available_topics)

# --- LOGIQUE DE FILTRAGE FINAL ---
filtered_df = working_df.copy()

if selected_country != "Tous les pays":
    c_dois = filtered_df[filtered_df['country'].str.contains(selected_country, na=False)]['doi'].unique()
    filtered_df = filtered_df[filtered_df['doi'].isin(c_dois)]
    
if selected_inst != "Tous les établissements":
    i_dois = filtered_df[filtered_df['institution'].str.contains(selected_inst, na=False, regex=False)]['doi'].unique()
    filtered_df = filtered_df[filtered_df['doi'].isin(i_dois)]

if selected_subfield != "Tous les domaines":
    s_dois = filtered_df[filtered_df['subfields'].str.contains(selected_subfield, na=False, regex=False)]['doi'].unique()
    filtered_df = filtered_df[filtered_df['doi'].isin(s_dois)]

if selected_topic != "Tous les thèmes":
    t_dois = filtered_df[filtered_df['topics'].str.contains(selected_topic, na=False, regex=False)]['doi'].unique()
    filtered_df = filtered_df[filtered_df['doi'].isin(t_dois)]

display_df = filtered_df

# --- AFFICHAGE DES RÉSULTATS ---
st.title(f"Collaborations : {selected_author if selected_author != 'Tous les auteurs' else 'LS2N'} (2020-2025)")

st.markdown("""
Cet observatoire présente les publications scientifiques co-signées par des membres du **LS2N** avec des partenaires internationaux. 
💡 **Conseil :** Utilisez les filtres dans le menu à gauche pour explorer par chercheur ou par zone géographique.
""")

col1, col2 = st.columns([1, 2])

with col1:
    st.write("### 🚩 Pays partenaires")
    # On explose pour compter chaque pays individuellement
    exploded_countries = display_df['country'].str.split('|').explode().str.strip()
    stats_countries = exploded_countries[exploded_countries != 'FR'].value_counts().reset_index()
    stats_countries.columns = ['country_code', 'count']
    stats_countries['country_name'] = stats_countries['country_code'].apply(get_country_name)
    
    if not stats_countries.empty:
        fig_pie = px.pie(stats_countries, values='count', names='country_name', hole=0.4)
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("Aucune collaboration internationale sur ces critères.")

    st.write("---")
    st.write("### 👥 Auteurs Nantais")
    # Compter les publications par auteurs nantais dans les données filtrées
    nantes_authors_stats = display_df[display_df['is_nantes'] == True]['author'].value_counts().reset_index()
    nantes_authors_stats.columns = ['Auteur', 'Publications']
    
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
        st.plotly_chart(fig_authors, use_container_width=True)
    else:
        st.info("Aucun auteur nantais trouvé.")

with col2:
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
                    st.write("🔬 **Thèmes de recherche :**")
                    st.write(", ".join(topics_list))
            
            openalex_id = work_data['work_id'].iloc[0]
            st.caption(f"**DOI:** [{doi}]({doi}) | **OpenAlex:** [{openalex_id}](https://openalex.org/works/{openalex_id})")