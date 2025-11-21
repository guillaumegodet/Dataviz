# -*- coding: utf-8 -*-
"""
Created on Wed Nov 19 13:55:43 2025

@author: godet-g
"""

import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from concurrent.futures import ThreadPoolExecutor
from matplotlib.colors import to_rgb, to_hex
import numpy as np

# --------------------------------------------------------
# CONFIGURATION : LISTE DES INSTITUTIONS AUTORISÉES
# --------------------------------------------------------
INSTITUTIONS = {
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
}

VALID_IDS = "|".join(INSTITUTIONS.keys())

BASE_WORKS_API = "https://api.openalex.org/works"
BASE_SUBFIELD_API = "https://api.openalex.org/subfields"

# Palette Domaines
DOMAIN_COLORS = {
    "Physical Sciences": "#1E88E5",
    "Life Sciences": "#43A047",
    "Social Sciences": "#D32F2F",
    "Health Sciences": "#FB8C00",
}
DEFAULT_COLOR = "#6A5ACD"

# --------------------------------------------------------
# UTILITAIRES
# --------------------------------------------------------
def lighten(hex_color, factor):
    r, g, b = to_rgb(hex_color)
    r, g, b = [min(1, c + (1 - c) * factor) for c in (r, g, b)]
    return to_hex((r, g, b))


def color_scale(domain):
    base = DOMAIN_COLORS.get(domain, DEFAULT_COLOR)
    return base, lighten(base, 0.4), lighten(base, 0.7)

# --------------------------------------------------------
# API
# --------------------------------------------------------
@st.cache_data(show_spinner=False)
def fetch_subfield_counts(inst, period):
    url = f"{BASE_WORKS_API}?group_by=primary_topic.subfield.id&per_page=200&filter=authorships.institutions.lineage:{inst},publication_year:{period}"
    r = requests.get(url, timeout=30).json()
    if "group_by" not in r:
        return None
    return pd.DataFrame([{ "subfield_id": x["key"], "count": x["count"] } for x in r["group_by"]])


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
# SUNBURST
# --------------------------------------------------------
def build_chart(institution, period, max_subfields):

    df = fetch_subfield_counts(institution, period)
    if df is None or df.empty:
        st.error("Aucun résultat trouvé pour cette institution.")
        return

    with ThreadPoolExecutor(max_workers=12) as ex:
        details = list(filter(None, ex.map(fetch_subfield_details, df.subfield_id.unique())))

    dfh = pd.DataFrame(details)
    df_final = df.merge(dfh, on="subfield_id")
    df_final = df_final[df_final.Domain_Name != "N/A"].sort_values("count", ascending=False)
    df_chart = df_final.head(max_subfields).copy()

    # COULEURS
    cmap = {}
    for domain in df_chart.Domain_Name.unique():
        c_dom, c_field, c_sub = color_scale(domain)
        cmap[domain] = c_dom
        for f in df_chart[df_chart.Domain_Name == domain].Field_Name.unique():
            cmap[f] = c_field
        for s in df_chart[df_chart.Domain_Name == domain].Subfield_Name.unique():
            cmap[s] = c_sub

    # RECONSTRUCTION SUNBURST
    from collections import defaultdict
    node_count = defaultdict(int)
    domains = []

    for _, r in df_chart.iterrows():
        dom = r['Domain_Name']; fld = r['Field_Name']; sub = r['Subfield_Name']; cnt = int(r['count'])
        node_count[sub] += cnt
        if dom not in domains: domains.append(dom)

    for fld in df_chart.Field_Name.unique():
        node_count[fld] = df_chart[df_chart.Field_Name == fld]['count'].sum()
    for dom in domains:
        node_count[dom] = df_chart[df_chart.Domain_Name == dom]['count'].sum()

    labels, parents, values, colors = [], [], [], []

    for dom in domains:
        labels.append(dom); parents.append(""); values.append(node_count[dom]); colors.append(cmap[dom])
        fields = df_chart[df_chart.Domain_Name == dom].Field_Name.unique()
        for fld in fields:
            labels.append(fld); parents.append(dom); values.append(node_count[fld]); colors.append(cmap[fld])
            subs = df_chart[(df_chart.Domain_Name == dom) & (df_chart.Field_Name == fld)].Subfield_Name.unique()
            for sub in subs:
                labels.append(sub); parents.append(fld); values.append(node_count[sub]); colors.append(cmap[sub])

    fig = go.Figure(go.Sunburst(labels=labels, parents=parents, values=values,
                                marker=dict(colors=colors), branchvalues="total"))
    fig.update_layout(margin=dict(t=40, l=0, r=0, b=0), height=750,
                      title=f"Cartographie OpenAlex : {INSTITUTIONS[institution]} ({period})")
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(df_chart[["Domain_Name", "Field_Name", "Subfield_Name", "count"]])

# --------------------------------------------------------
# INTERFACE STREAMLIT
# --------------------------------------------------------
st.set_page_config(page_title="OpenAlex — Pôle S&T", layout="wide")
st.title("Cartographie OpenAlex — Pôle Sciences & Technologies")

# Sélecteur institution
inst_choice = st.selectbox("Choisissez un laboratoire", list(INSTITUTIONS.keys()),
                           format_func=lambda x: f"{INSTITUTIONS[x]} ({x})")

period = st.text_input("Période (YYYY ou YYYY-YYYY)", "2023")
max_sf = st.slider("Nombre max de subfields", 10, 200, 50, 10)

if st.button("Générer la Cartographie"):
    build_chart(inst_choice, period.strip(), max_sf)