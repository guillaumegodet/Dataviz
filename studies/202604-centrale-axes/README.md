# 📊 Dashboard Axes Stratégiques — Centrale Nantes

Tableau de bord interactif pour l'analyse et la curation des publications scientifiques de Centrale Nantes (2022–2026), classées selon les **4 axes stratégiques de recherche** de l'établissement.

> **Déployé via Streamlit Cloud** : [Accéder au dashboard](https://enjeux-strategiques-centrale.streamlit.app/)

---

## 🎯 Objectif

Ce projet permet de :

1. **Visualiser** la répartition des publications de Centrale Nantes par axe stratégique
2. **Corriger collaborativement** les classifications via la plateforme Grist
3. **Exporter** les données filtrées en CSV

Les 4 axes stratégiques couverts :

| Axe | Couleur |
|-----|---------|
| 🟡 Production et gestion des énergies renouvelables | Or |
| 🔵 Mobilités décarbonnées | Bleu |
| 🟢 Matériaux, procédés et process industriels durables | Vert |
| 🔴 Ingénierie pour la santé | Rouge |

---

## 🗂️ Structure du projet

```
.
├── app_axes.py                              # Application Streamlit principale
├── process_axes.py                          # Script de classification des publications
├── centrale_axes_data.parquet               # Données traitées (généré par process_axes.py)
├── requirements.txt                         # Dépendances Python
└── README.md                                # Documentation
```

---

## ⚙️ Architecture de la classification

Le script `process_axes.py` utilise une approche **hybride en 2 niveaux** :

### Niveau 1 — Correspondance sur les Topics OpenAlex *(priorité haute)*

Les publications OpenAlex sont associées à des `topics` structurés (ex: `"Electric Vehicles and Infrastructure"`). Ces topics sont comparés à un **dictionnaire de mots-clés par axe** :

- Si ≥ 2 mots-clés correspondent à un axe avec une avance claire → classification directe
- La motivation affiche : `[Topics OpenAlex] Correspondance directe sur N mot(s)-clé(s)`

### Niveau 2 — TF-IDF sémantique sur titre + abstract *(fallback)*

Si les topics ne permettent pas de trancher, on compare le texte de la publication avec des **descriptions enrichies de chaque axe en anglais** via TF-IDF (unigrammes + bigrammes).

- Seuil de confiance : 0.05 (en dessous → `Autre / Non classé`)
- La motivation affiche : `[TF-IDF Sémantique] Similarité X.XX — termes communs : ...`

---

## 🔁 Curation collaborative via Grist

Les chercheurs peuvent corriger les classifications directement dans l'application. Les corrections sont synchronisées avec la table Grist via l'API REST.

**Configuration Grist** (dans `app_axes.py`) :

```python
GRIST_DOC_ID = "..."           # ID du document Grist
GRIST_TABLE_NAME = "..."       # Table ID (sensible à la casse)
# GRIST_API_KEY est récupéré via st.secrets sur Streamlit Cloud
```

> ⚠️ La clé API doit disposer d'un accès **lecture/écriture** sur le document. Elle doit être ajoutée dans les **Secrets** de Streamlit Cloud (`GRIST_API_KEY`).

---

## 🚀 Lancer localement

### Prérequis

- Python 3.11+
- [`uv`](https://github.com/astral-sh/uv) (gestionnaire de packages rapide)

### Installation

```bash
# Cloner le projet
git clone https://github.com/guillaumegodet/Dataviz.git
cd Dataviz/studies/202604-centrale-axes

# Installer les dépendances
uv pip install -r requirements.txt

# Configuration des secrets locaux (pour l'accès Grist)
mkdir .streamlit
# Ajoutez votre clé API Grist dans .streamlit/secrets.toml :
# GRIST_API_KEY = "votre_cle_api"
```

### Générer les données

Si vous avez le fichier source JSON d'OpenAlex :

```bash
uv run python process_axes.py
```

Cela génère `centrale_axes_data.parquet`.

### Lancer le dashboard

```bash
uv run streamlit run app_axes.py
```

---

## 📦 Déploiement Streamlit Cloud

L'application est configurée pour être déployée sur **Streamlit Cloud**. 

1. Connectez votre dépôt GitHub à Streamlit Cloud.
2. Pointez vers le fichier `studies/202604-centrale-axes/app_axes.py`.
3. Ajoutez le secret `GRIST_API_KEY` dans les paramètres de l'application sur Streamlit Cloud.

Contrairement à la version *stlite* précédente, la synchronisation avec Grist est pleinement opérationnelle car le code s'exécute côté serveur.

---

## 📋 Données source

Les publications sont extraites depuis **[OpenAlex](https://openalex.org/)**, filtrées sur les affiliations de Centrale Nantes et de ses laboratoires.

---

## 🛠️ Dépendances

| Package | Usage |
|---------|-------|
| `streamlit` | Interface web |
| `plotly` | Graphiques interactifs |
| `pandas` / `pyarrow` | Manipulation des données |
| `scikit-learn` | TF-IDF vectorisation |
| `requests` | API Grist |
| `tqdm` | Barre de progression (process_axes.py) |

---

## 👤 Auteur

Développé par le service **Bibliométrie** de Nantes Université.

Pour toute question : ouvrir une issue sur le dépôt GitHub.
