# SCRIPT COMPLET — Sunburst OpenAlex avec couleurs Domain → Field → Subfield

import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from concurrent.futures import ThreadPoolExecutor
from matplotlib.colors import to_rgb, to_hex
import numpy as np

# --------------------------------------------------------
# CONFIGURATION
# --------------------------------------------------------
BASE_WORKS_API = "https://api.openalex.org/works"
BASE_SUBFIELD_API = "https://api.openalex.org/subfields"

# Couleurs élégantes des 4 Domaines
DOMAIN_COLORS = {
    "Physical Sciences": "#1E88E5", 
    "Life Sciences": "#43A047",      
    "Social Sciences": "#D32F2F",  
    "Health Sciences": "#FB8C00",    
}

DEFAULT_COLOR = "#6A5ACD"

# --------------------------------------------------------
# UTILITAIRES COULEURS
# --------------------------------------------------------
def lighten(hex_color, factor):
    r, g, b = to_rgb(hex_color)
    r, g, b = [min(1, c + (1 - c) * factor) for c in (r, g, b)]
    return to_hex((r, g, b))


def color_scale(domain):
    base = DOMAIN_COLORS.get(domain, DEFAULT_COLOR)
    return base, lighten(base, 0.4), lighten(base, 0.7)

# --------------------------------------------------------
# APPELS API
# --------------------------------------------------------
@st.cache_data(show_spinner=False)
def fetch_subfield_counts(inst, period):
    url = (
        f"{BASE_WORKS_API}?group_by=primary_topic.subfield.id&per_page=200"
        f"&filter=authorships.institutions.lineage:{inst},publication_year:{period}"
    )
    r = requests.get(url, timeout=30).json()
    if "group_by" not in r:
        return None
    return pd.DataFrame([
        {"subfield_id": x["key"], "count": x["count"]} for x in r["group_by"]
    ])


@st.cache_data(show_spinner=False)
def fetch_subfield_details(subfield_id):
    sid = subfield_id.split("/")[-1]
    try:
        r = requests.get(f"{BASE_SUBFIELD_API}/{sid}", timeout=10).json()
        return {
            "subfield_id": subfield_id,
            "Subfield_Name": r.get("display_name", "N/A"),
            "Field_Name": r.get("field", {}).get("display_name", "N/A"),
            "Domain_Name": r.get("domain", {}).get("display_name", "N/A"),
        }
    except:
        return None

# --------------------------------------------------------
# CONSTRUCTION DU SUNBURST (VERSION FIABLE)
# --------------------------------------------------------
def build_chart(institution, period, max_subfields):

    # ---- 1) RÉCUPÉRATION SUBFIELDS ----
    df = fetch_subfield_counts(institution, period)
    if df is None or df.empty:
        st.error("Aucun résultat trouvé pour cette requête.")
        return

    # ---- 2) RÉCUPÉRATION HIÉRARCHIE (PARALLÈLE) ----
    subfields = df.subfield_id.unique()
    with ThreadPoolExecutor(max_workers=12) as ex:
        details = list(filter(None, ex.map(fetch_subfield_details, subfields)))

    dfh = pd.DataFrame(details)
    df_final = df.merge(dfh, on="subfield_id")
    df_final = df_final[df_final.Domain_Name != "N/A"].sort_values("count", ascending=False)

    df_chart = df_final.head(max_subfields).copy()

    # ---- 3) CRÉATION DES COULEURS ----
    cmap = {}
    for domain in df_chart.Domain_Name.unique():
        c_dom, c_field, c_sub = color_scale(domain)

        cmap[domain] = c_dom
        for fld in df_chart[df_chart.Domain_Name == domain].Field_Name.unique():
            cmap[fld] = c_field
        for sub in df_chart[df_chart.Domain_Name == domain].Subfield_Name.unique():
            cmap[sub] = c_sub

    # ---- 4) RECONSTRUCTION MANUELLE DU SUNBURST ----
    from collections import defaultdict

    node_count = defaultdict(int)
    parent_of = {}
    domains = []

    # Feuilles
    for _, row in df_chart.iterrows():
        dom = row['Domain_Name']
        fld = row['Field_Name']
        sub = row['Subfield_Name']
        cnt = int(row['count'])

        node_count[sub] += cnt
        parent_of[sub] = fld
        parent_of[fld] = dom
        if dom not in domains:
            domains.append(dom)

    # Sommes Fields et Domains
    for fld in df_chart.Field_Name.unique():
        node_count[fld] = df_chart.loc[df_chart.Field_Name == fld, 'count'].sum()

    for dom in domains:
        node_count[dom] = df_chart.loc[df_chart.Domain_Name == dom, 'count'].sum()

    # ---- 5) LISTES labels/parents/values/colors ----
    labels, parents, values, colors = [], [], [], []

    for dom in domains:
        labels.append(dom)
        parents.append("")
        values.append(int(node_count[dom]))
        colors.append(cmap[dom])

        fields = df_chart[df_chart.Domain_Name == dom].Field_Name.unique()
        for fld in fields:
            labels.append(fld)
            parents.append(dom)
            values.append(int(node_count[fld]))
            colors.append(cmap[fld])

            subs = df_chart[(df_chart.Domain_Name == dom) & (df_chart.Field_Name == fld)].Subfield_Name.unique()
            for sub in subs:
                labels.append(sub)
                parents.append(fld)
                values.append(int(node_count[sub]))
                colors.append(cmap[sub])

    # ---- 6) SUNBURST PLOTLY ----
    fig = go.Figure(go.Sunburst(
        labels=labels,
        parents=parents,
        values=values,
        marker=dict(colors=colors),
        branchvalues="total",
        hovertemplate='<b>%{label}</b><br>Count: %{value}<extra></extra>'
    ))

    fig.update_layout(
        margin=dict(t=50, l=0, r=0, b=0), height=750,
        title=f"Cartographie de {institution} — {period}"
    )

    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Données Utilisées (Top Subfields)")
    st.dataframe(df_chart[["Domain_Name","Field_Name","Subfield_Name","count"]])

# --------------------------------------------------------
# INTERFACE STREAMLIT
# --------------------------------------------------------
st.set_page_config(page_title="OpenAlex Sunburst", layout="wide")
st.title("Sunburst chart sur les domaines OpenAlex – Domains / Fields / Subfields")

col1, col2 = st.columns(2)
institution = col1.text_input("Identifiant Institution OpenAlex (i...) - séparez deux identifiants avec |", "i4210138474")
period = col2.text_input("Période (YYYY ou YYYY-YYYY)", "2025")
max_sf = st.slider("Nombre max de Subfields", 10, 200, 50, 10)

if st.button("Générer la Cartographie"):
    build_chart(institution.strip(), period.strip(), max_sf)
