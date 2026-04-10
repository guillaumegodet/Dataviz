import streamlit as st
import pandas as pd
import requests
import datetime
import urllib.parse
from io import BytesIO

# --- CONFIGURATION ---
st.set_page_config(page_title="Publications Centrale Nantes - Com News", layout="wide", page_icon="📰")

# Centrale Nantes OpenAlex ID
CENTRALE_ID = "I100445878"

# Laboratoires mapping (from existing logic)
LAB_ID_MAP = {
    "I4210117005": "LS2N",
    "I4210137520": "GeM",
    "I4210153154": "LHEEA",
    "I4210162214": "AAU",
    "I4210153365": "LMJL",
}

@st.cache_data(ttl=3600)
def fetch_recent_publications(days=30):
    """Fetch OpenAlex works for Centrale Nantes sorted by date"""
    start_date = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime("%Y-%m-%d")
    url = f"https://api.openalex.org/works?filter=institutions.id:{CENTRALE_ID},from_publication_date:{start_date}&sort=publication_date:desc&per-page=100"
    
    response = requests.get(url)
    if response.status_code != 200:
        st.error(f"Erreur de connexion à l'API OpenAlex (Status: {response.status_code}).")
        return []
    
    data = response.json()
    return data.get("results", [])

def process_publications(raw_data):
    """Process OpenAlex JSON into a Flat DataFrame"""
    processed = []
    
    for work in raw_data:
        title = work.get("title", "")
        pub_date = work.get("publication_date", "")
        doi = work.get("doi", "") or work.get("id", "")
        is_oa = work.get("open_access", {}).get("is_oa", False)
        cited_by_count = work.get("cited_by_count", 0)
        
        # Authors and Labs identification
        centrale_authors = []
        author_labs = set()
        all_authors = []
        
        for auth in work.get("authorships", []):
            author_name = auth.get("author", {}).get("display_name", "Unknown")
            all_authors.append(author_name)
            
            is_centrale = False
            labs_for_this_author = []
            
            for inst in auth.get("institutions", []):
                inst_full_id = inst.get("id", "")
                inst_id = inst_full_id.split("/")[-1] if inst_full_id else ""
                
                if inst_id == CENTRALE_ID:
                    is_centrale = True
                    
                if inst_id in LAB_ID_MAP:
                    labs_for_this_author.append(LAB_ID_MAP[inst_id])
                    
                # Check lineage
                for lid_full in inst.get("lineage", []):
                    lid = lid_full.split("/")[-1] if lid_full else ""
                    if lid in LAB_ID_MAP:
                        labs_for_this_author.append(LAB_ID_MAP[lid])
                        
            if is_centrale or labs_for_this_author:
                centrale_authors.append(author_name)
                for lab in labs_for_this_author:
                    author_labs.add(lab)
        
        # Source (Journal/Conference)
        source_name = "Inconnu"
        primary_loc = work.get("primary_location")
        if primary_loc:
            source_data = primary_loc.get("source")
            if source_data:
                source_name = source_data.get("display_name", "Inconnu")
        
        # Topics
        topics = []
        for t in work.get("topics", []):
            display = t.get("display_name")
            if display:
                topics.append(display)
                
        # Main author formatting
        main_authors_str = ", ".join(centrale_authors) if centrale_authors else (", ".join(all_authors[:3]) + " et al.")
                
        processed.append({
            "Titre": title,
            "Auteurs": main_authors_str,
            "Laboratoires": ", ".join(sorted(author_labs)) if author_labs else "Non rattaché",
            "Journal/Conférence": source_name,
            "Thématiques": ", ".join(topics[:3]) if topics else "Non spécifié",
            "Date": pub_date,
            "Citations": cited_by_count,
            "Open Access": "Ouvert 🟢" if is_oa else "Fermé 🔴",
            "Lien": doi,
            "is_oa_bool": is_oa
        })
        
    return pd.DataFrame(processed)

def generate_linkedin_post(row):
    authors = row['Auteurs']
    lab = row['Laboratoires']
    journal = row['Journal/Conférence']
    theme = row['Thématiques'].split(",")[0] if row['Thématiques'] and row['Thématiques'] != 'Non spécifié' else "notre domaine"
    doi = row['Lien']
    title = row['Titre']
    
    post = f"🎉 Félicitations à nos chercheurs pour leur nouvelle publication !\n\n"
    post += f"Découvrez les travaux de {authors} "
    if lab and lab != "Non rattaché":
        post += f"du laboratoire {lab} "
    post += f"sur le thème : {theme}.\n\n"
    post += f"Leur article \"{title}\" vient d'être publié dans {journal}.\n\n"
    post += f"🔗 Pour le lire, c'est par ici : {doi}\n\n"
    
    tags = ["#CentraleNantes", "#Recherche", "#Innovation"]
    if lab and lab != "Non rattaché":
        for l in lab.split(", "):
            tags.append(f"#{l}")
            
    post += " ".join(tags)
    return post

# --- MAIN UI ---
st.title("📰 Centrale Nantes - Radar des Publications")
st.markdown("Un outil automatisé pour la Direction de la Communication. Identifiez facilement les récentes publications de nos chercheurs et valorisez-les sur les réseaux sociaux.")

# Sidebar Controls
st.sidebar.header("🔍 Critères de recherche")
days_lookback = st.sidebar.slider("Période d'analyse (jours) :", 7, 90, 30, step=1)

with st.spinner("Récupération des données depuis OpenAlex..."):
    raw_data = fetch_recent_publications(days_lookback)
    
if raw_data:
    df = process_publications(raw_data)
    
    # ── Filtres Dynamiques ──
    st.sidebar.divider()
    st.sidebar.subheader("🎯 Filtrer les résultats")
    
    # Lab filter
    all_labs = set()
    for lab_str in df["Laboratoires"]:
        if lab_str != "Non rattaché":
            for lab in lab_str.split(", "):
                all_labs.add(lab)
    selected_lab = st.sidebar.selectbox("Par laboratoire :", ["Tous les labos"] + sorted(list(all_labs)))
    
    # Theme search text input
    theme_search = st.sidebar.text_input("Par mot-clé thématique :", placeholder="ex: robot, matériaux, énergie...")
    
    # Options
    oa_only = st.sidebar.checkbox("🟢 Seulement les articles Open Access")
    sort_by = st.sidebar.radio("Trier par :", ["Plus récent", "Impact (Citations)"])
    
    # ── Applying Filters ──
    filtered_df = df.copy()
    if selected_lab != "Tous les labos":
        filtered_df = filtered_df[filtered_df["Laboratoires"].str.contains(selected_lab, regex=False)]
        
    if theme_search:
        # Case insensitive thematic filter
        filtered_df = filtered_df[filtered_df["Thématiques"].str.contains(theme_search, case=False, na=False) | 
                                  filtered_df["Titre"].str.contains(theme_search, case=False, na=False)]
    
    if oa_only:
        filtered_df = filtered_df[filtered_df["is_oa_bool"] == True]
        
    if sort_by == "Plus récent":
        filtered_df = filtered_df.sort_values(by="Date", ascending=False)
    else:
        filtered_df = filtered_df.sort_values(by="Citations", ascending=False)
        
    # ── KPIs ──
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Publications", len(filtered_df))
    
    oa_percent = int((filtered_df["is_oa_bool"].sum() / len(filtered_df)) * 100) if len(filtered_df) > 0 else 0
    c2.metric("Publications Open Access", f"{filtered_df['is_oa_bool'].sum()} ({oa_percent}%)")
    
    c3.metric("Citations totales (sur la période)", filtered_df["Citations"].sum())
    
    st.divider()
    
    # ── Table Affichage ──
    st.subheader("📚 Liste des publications")
    display_cols = ["Titre", "Auteurs", "Laboratoires", "Journal/Conférence", "Thématiques", "Date", "Citations", "Open Access", "Lien"]
    st.dataframe(
        filtered_df[display_cols],
        use_container_width=True,
        column_config={
            "Lien": st.column_config.LinkColumn("Lien DOI"),
            "Citations": st.column_config.NumberColumn(format="%d")
        },
        hide_index=True
    )
    
    st.divider()
    
    # ── Export & Cards ──
    c_left, c_right = st.columns(2)
    
    with c_left:
        st.subheader("📥 Export des données")
        st.markdown("Idéal pour consolider vos bilans de communication ou intégrer dans vos outils internes.")
        
        csv_data = filtered_df[display_cols].to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📄 Télécharger en CSV",
            data=csv_data,
            file_name=f'publications_centrale_nantes_{datetime.date.today()}.csv',
            mime='text/csv',
        )
        
        try:
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                filtered_df[display_cols].to_excel(writer, index=False, sheet_name='Publications')
            st.download_button(
                label="📊 Télécharger en Excel",
                data=buffer.getvalue(),
                file_name=f'publications_centrale_nantes_{datetime.date.today()}.xlsx',
                mime='application/vnd.ms-excel',
            )
        except ModuleNotFoundError:
            st.info("💡 L'export Excel natif nécessite le module `xlsxwriter`. Usez de l'export CSV en attendant.")
            
    with c_right:
        st.subheader("📱 Assistant Réseaux Sociaux")
        st.markdown("Générez un template de post pré-rempli pour LinkedIn / X.")
        
        if not filtered_df.empty:
            titles = filtered_df["Titre"].tolist()
            selected_title = st.selectbox("Sélectionnez la publication à mettre en avant :", titles)
            selected_row = filtered_df[filtered_df["Titre"] == selected_title].iloc[0]
            
            post_content = generate_linkedin_post(selected_row)
            
            # Affichage dans un textArea pour modification possible
            st.text_area("Brouillon pour LinkedIn :", value=post_content, height=250)
            
            # Trick for copy
            st.markdown("*(Pour copier, cliquez dans la zone ci-dessus et faites `Ctrl+A` puis `Ctrl+C`)*")
            
else:
    st.warning("Aucune donnée disponible pour cette période, ou erreur de connexion API.")
