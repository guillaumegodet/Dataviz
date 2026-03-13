# 🔬 Dashboard Coopérations Internationales — Nantes Université

> **Application en ligne :** [un-collab.streamlit.app](https://un-collab.streamlit.app/)

---

## 🎯 Objectif

Ce tableau de bord interactif permet d'explorer les **collaborations scientifiques internationales** de **Nantes Université** et de ses unités de recherche à partir des données de l'API [OpenAlex](https://openalex.org/).

Il se concentre exclusivement sur les partenariats mondiaux en filtrant les co-affiliations françaises secondaires pour une meilleure visibilité des réseaux internationaux.

---

## 🖥️ Fonctionnalités

### Filtres avancés (barre latérale)
| Filtre | Description |
|---|---|
| 📅 **Période** | Plage d'années de publication (2020–2025). |
| 🌍 **Pays partenaire** | Classés par volume de collaboration décroissant (+ volume affiché). |
| 🎯 **Thématiques (Cascade)** | Hiérarchie OpenAlex : Domaines > Disciplines > Sous-disciplines > Sujets. |
| 🏢 **Unité de recherche** | Filtrage par labo nantais (42 unités + Centrale Nantes). |
| 👤 **Chercheur nantais** | Filtrage par auteur individuel (dynamique selon l'unité). |
| 👥 **Taille de l'équipe** | Exclure les publications à très grand nombre d'auteurs (ex: CERN). |

### Trois modes d'affichage plein écran
- **🏫 Institutions** : Liste paginée des universités partenaires, avec thématiques dominantes, chercheurs nantais impliqués et publications détaillées.
- **🗺️ Carte** : Carte mondiale interactive (Mapbox/OpenStreetMap) affichant les villes partenaires. Zoom à la molette et centrage calculé par pays.
- **📊 Dataviz** : Vue d'ensemble statistique (Répartition par pays, Top auteurs nantais, Domaines et Sujets les plus publiés).

---

## 🗂️ Structure du projet

```
studies/202603-unresearchcollab/
├── app.py                        # Application Streamlit (Interface et Logique)
├── extract_coop.py               # Script d'extraction filtrée (Nantes + International)
├── fetch_coords.py               # Géocodage et enrichissement urbain
├── cooperations_nantesu.parquet  # Données optimisées (versionnées pour le Cloud)
└── requirements.txt              # Dépendances (incluant pycountry, pyalex, plotly)
```

---

## 🚀 Utilisation en local

### 1. Installer les dépendances

D'abord, placez-vous dans le dossier de l'étude :
```bash
cd studies/202603-unresearchcollab
```

Avec [uv](https://github.com/astral-sh/uv) (recommandé) :
```bash
uv run --with streamlit --with plotly --with pandas --with pycountry --with pyarrow streamlit run app.py
```

### 2. Régénérer les données

Pour rafraîchir les données et la géolocalisation :
```bash
# 1. Extraction (Filtre Nantes+International, normalisation des IDs)
uv run --with pyalex --with tqdm --with pandas --with pyarrow python extract_coop.py

# 2. Géolocalisation (Villes, Lat, Lon)
uv run --with pyalex --with tqdm --with pandas --with pyarrow python fetch_coords.py
```

---

## 🔧 Données et Optimisation

- **Filtrage International** : Les affiliations françaises non-nantaises (CNRS, INSERM, etc.) sont exclues dès l'extraction pour se concentrer sur les relations transfrontalières.
- **Performance** : Utilisation du format Parquet pour un chargement instantané.
- **Identifiants** : Utilisation des IDs OpenAlex normalisés pour Nantes Université (`I97188460`) et Centrale Nantes (`I100445878`).

---

## 🏢 Unités de recherche couvertes

AAU · CAPHI · CDMO · CEISAM · CENS · CFV · CR2TI · CRCI2NA · CReAAH · CREN · CRHIA · CRINI · DCS · ESO · GeM · GEPEA · IETR · IICiMed · IMN · INCIT · IRDP · IREENA · ISOMER · ITX · LAMO · LEMNA · LETG · LHEEA · LLING · LMJL · LPG · LS2N · LTeN · MIP · PHAN · RMeS · SPHERE · SUBATECH · TaRGeT · TENS · US2B · Centrale Nantes · LPPL

---

**Développé par :** [guillaumegodet](https://github.com/guillaumegodet)  
**Données :** [OpenAlex](https://openalex.org/) (licence CC0)