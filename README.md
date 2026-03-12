# 🔬 Dashboard Coopérations Internationales — Nantes Université

> **Application en ligne :** [un-collab.streamlit.app](https://un-collab.streamlit.app/)

---

## 🎯 Objectif

Ce tableau de bord interactif permet d'explorer les **collaborations scientifiques internationales** de **Nantes Université** (et de ses unités de recherche) à partir des données de l'API [OpenAlex](https://openalex.org/).

Il visualise les co-publications entre des chercheurs nantais et leurs partenaires internationaux, et permet de les filtrer selon de multiples dimensions.

---

## 🖥️ Fonctionnalités

### Filtres disponibles (barre latérale)
| Filtre | Description |
|---|---|
| 📅 **Période** | Plage d'années de publication (2020–2025) |
| 🌍 **Pays partenaire** | Filtrage par pays + établissement étranger |
| 🎓 **Domaine de recherche** | Sous-champ disciplinaire (OpenAlex subfields) |
| 🔬 **Sujet de recherche** | Thème fin (OpenAlex topics) |
| 🏢 **Unité de recherche** | Filtrage par labo nantais (LS2N, CEISAM, etc.) |
| 👤 **Chercheur nantais** | Filtrage par auteur individuel |

### Trois modes d'affichage
- **Par Publications** : liste paginée des publications avec détail auteurs, domaines, DOI
- **Par Universités partenaires** : classement des institutions, avec chercheurs nantais impliqués, domaines et publications associées
- **Par Carte** : carte mondiale interactive (clic sur une bulle = détail de la relation)

---

## 🗂️ Structure du projet

```
studies/202603-unresearchcollab/
├── app.py                        # Application Streamlit principale
├── extract_coop.py               # Extraction des données depuis OpenAlex
├── fetch_coords.py               # Géocodage des institutions (lat/lon)
├── cooperations_nantesu.parquet  # Données (générées, versionnées pour Streamlit Cloud)
└── requirements.txt              # Dépendances Python
```

---

## 🚀 Utilisation en local

### 1. Installer les dépendances

Avec [uv](https://github.com/astral-sh/uv) (recommandé) :

```bash
uv run --with streamlit --with plotly --with pandas --with pycountry --with pyarrow streamlit run app.py
```

Ou avec pip :

```bash
pip install streamlit plotly pandas pycountry pyarrow pyalex tqdm
streamlit run app.py
```

### 2. Régénérer les données (optionnel)

Si vous souhaitez rafraîchir les données depuis l'API OpenAlex :

```bash
# Étape 1 : extraction des publications et co-auteurs
uv run --with pyalex --with tqdm --with pandas --with pyarrow extract_coop.py

# Étape 2 : géocodage des institutions
uv run --with pyalex --with tqdm --with pandas --with pyarrow fetch_coords.py
```

> ⚠️ L'extraction complète pour Nantes Université (2020–2025) prend environ **2–3 minutes** (pagination de l'API OpenAlex, ~10 000 publications).

---

## 🔧 Données

Les données proviennent de l'API ouverte **[OpenAlex](https://openalex.org/)** et couvrent :
- **Institution** : Nantes Université (`I97188460`) et les **42 unités de recherche** sous sa tutelle ainsi que Centrale Nantes (`i100445878`) 
- **Période** : 2020–2025
- **Colonnes** : DOI, titre, année, auteur, institution(s), pays, identifiants OpenAlex, domaines, sujets, coordonnées géographiques

---

## 🏢 Unités de recherche couvertes

AAU · CAPHI · CDMO · CEISAM · CENS · CFV · CR2TI · CRCI2NA · CReAAH · CREN · CRHIA · CRINI · DCS · ESO · GeM · GEPEA · IETR · IICiMed · IMN · INCIT · IRDP · IREENA · ISOMER · ITX · LAMO · LEMNA · LETG · LHEEA · LLING · LMJL · LPG · LS2N · LTeN · MIP · PHAN · RMeS · SPHERE · SUBATECH · TaRGeT · TENS · US2B · Centrale Nantes · LPPL

---

**Développé par :** [guillaumegodet](https://github.com/guillaumegodet)  
**Données :** [OpenAlex](https://openalex.org/) (licence CC0)