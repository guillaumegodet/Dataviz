# 📊 Cartographie Dynamique des domaines OpenAlex

## 🎯 Objectif du Projet

Ce projet vise à fournir un outil interactif et dynamique pour visualiser la cartographie scientifique d'une institution (laboratoire, université, etc.) en exploitant les données de l'API OpenAlex.

L'outil permet de :

1.  **Générer automatiquement** un Diagramme Solaire (**Sunburst Chart**) basé sur une institution et une période de temps définies.
2.  Visualiser la répartition des publications selon la **hiérarchie disciplinaire OpenAlex** : **Domain** \> **Field** \> **Subfield**.
3.  Analyser l'évolution des thèmes de recherche et identifier les domaines de force et les sujets émergents.

⚠️ Note Importante sur la Portée de l'Analyse :

L'API OpenAlex, lors du groupement (group_by), retourne par défaut les 200 premières catégories ayant le plus grand nombre de publications liées.

Par conséquent, cette cartographie se concentre sur les 200 Subfields (sous-domaines) qui ont été les plus productifs pour l'institution et la période sélectionnées. Elle offre une vue ciblée des sujets dominants.

-----

## 🚀 Technologie et Installation

L'application est développée en Python et utilise le framework **Streamlit** pour l'interface web interactive.

### Prérequis

Assurez-vous d'avoir **Python 3.8+** installé.

### Installation des Dépendances

Clonez le dépôt et installez les bibliothèques nécessaires :

```bash
# Cloner le dépôt (adapter avec votre URL)
git clone [URL_DE_VOTRE_DEPOT]
cd [NOM_DU_DOSSIER]

# Installer les dépendances Python
pip install streamlit pandas requests plotly
```

-----

## 🛠️ Utilisation de l'Application

### 1\. Structure du Fichier

Le script principal qui exécute l'application est :

  * `app_auto_generator.py` (ou le nom que vous lui avez donné).

### 2\. Démarrage

Pour lancer l'application, exécutez la commande suivante dans votre terminal :

```bash
streamlit run app_auto_generator.py
```

L'application s'ouvrira automatiquement dans votre navigateur par défaut (généralement à `http://localhost:8501`).

### 3\. Saisie des Paramètres

Dans l'interface Streamlit, vous devrez renseigner deux champs :

| Paramètre | Description | Format d'Exemple |
| :--- | :--- | :--- |
| **Identifiant OpenAlex de l'Institution** | L'identifiant unique OpenAlex de l'institution (commence par `i`). | `i4210117005` |
| **Année ou Période** | La période de publication à analyser. | `2022`, `2020-2023` |

### 4\. Fonctionnement

1.  Après avoir cliqué sur **"Générer la Cartographie"**, l'application effectue un premier appel à l'API OpenAlex pour obtenir les publications de l'institution groupées par **Subfield** et leur **compte**.
2.  Elle interroge ensuite l'API OpenAlex pour chaque Subfield afin de récupérer son **Field** et son **Domain** parent (cette étape est parallélisée pour optimiser le temps d'attente).
3.  Enfin, elle génère le **Diagramme Solaire Plotly** interactif.

-----

## 📂 Structure du Code (Aperçu)

Le script s'organise autour de trois fonctions clés :

  * `fetch_subfield_counts(institution_id, period)` : Récupère les données brutes des comptes de publication par Subfield.
  * `fetch_subfield_hierarchy(subfield_id)` : Récupère la classification complète (Domain, Field, Subfield) pour un identifiant donné.
  * `get_full_data_and_generate_chart(...)` : Orchestre les appels, fusionne les données, et génère le graphique Streamlit/Plotly.

-----

## 🤝 Contribution

Les contributions, signalements de bugs et suggestions d'améliorations sont les bienvenus \!

1.  Faire un fork du projet.
2.  Créer votre branche de fonctionnalité (`git checkout -b feature/NouvelleFonctionnalite`).
3.  Committer vos modifications (`git commit -am 'Ajouter Nouvelle Fonctionnalité'`).
4.  Pousser vers la branche (`git push origin feature/NouvelleFonctionnalite`).
5.  Créer une nouvelle Pull Request.

-----

**Développé par :** guillaumegodet
**Basé sur :** Données OpenAlex