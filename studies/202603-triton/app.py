import streamlit as st
import pandas as pd
import plotly.express as px
import pycountry

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
    df = pd.read_csv("cooperations_ls2n.csv")
    # On s'assure que les noms sont bien formatés pour la recherche
    df['author'] = df['author'].fillna("Inconnu")
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

# Filtrage final pour l'affichage
if selected_country != "Tous les pays":
    # On cherche le pays sélectionné dans la chaîne (ex: "FR|US")
    final_dois = working_df[working_df['country'].str.contains(selected_country, na=False)]['doi'].unique()
    display_df = working_df[working_df['doi'].isin(final_dois)]
else:
    display_df = working_df

# --- AFFICHAGE DES RÉSULTATS ---
st.title(f"Collaborations : {selected_author if selected_author != 'Tous les auteurs' else 'LS2N'} (2020-2025)")

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

with col2:
    dois = display_df['doi'].dropna().unique()
    st.write(f"### 📄 Publications ({len(dois)})")
    
    for doi in dois:
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
            
            openalex_id = work_data['work_id'].iloc[0]
            st.caption(f"**DOI:** [{doi}]({doi}) | **OpenAlex:** [{openalex_id}](https://openalex.org/works/{openalex_id})")