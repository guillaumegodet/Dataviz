import json
import pandas as pd
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from tqdm import tqdm
import os

# =============================================================================
# STRATEGIC AXES DEFINITION
# =============================================================================
AXES = {
    "Production et gestion des énergies renouvelables": "",
    "Mobilités décarbonnées": "",
    "Matériaux, procédés et process industriels durables": "",
    "Ingénierie pour la santé": "",
}
AXIS_NAMES = list(AXES.keys())

# =============================================================================
# LEVEL 1 — KEYWORD DICTIONARY ON OPENALEX TOPICS
# These are English terms that appear in OpenAlex topic names ("display_name"
# of topics, subfields, fields).  Match is case-insensitive substring.
# Higher-confidence terms come first, because the first match wins if the
# score already reaches the "high confidence" threshold.
# =============================================================================
TOPIC_KEYWORDS = {
    # ── Energies renouvelables ──────────────────────────────────────────────
    "Production et gestion des énergies renouvelables": [
        "offshore wind", "wind turbine", "wind energy", "wind power",
        "tidal energy", "tidal turbine", "wave energy", "ocean energy",
        "marine energy", "tidal current",
        "photovoltaic", "solar energy", "solar cell", "solar panel",
        "hydrogen production", "hydrogen storage", "fuel cell",
        "energy storage", "battery storage", "grid energy",
        "smart grid", "microgrid", "power grid", "energy management",
        "energy harvesting", "renewable energy", "energy transition",
        "hydropower", "geothermal",
        "electrolyzer", "electrolysis",
    ],

    # ── Mobilités décarbonnées ──────────────────────────────────────────────
    "Mobilités décarbonnées": [
        "electric vehicle", "electric car", "electric mobility",
        "battery electric", "hybrid vehicle", "plug-in hybrid",
        "charging station", "ev battery",
        "autonomous vehicle", "self-driving", "autonomous driving",
        "connected vehicle", "vehicle automation",
        "ship propulsion", "maritime propulsion", "vessel propulsion",
        "sailing", "wind-assisted propulsion", "wind sail",
        "hydrogen propulsion", "hydrogen vehicle", "hydrogen aircraft",
        "sustainable aviation", "aircraft propulsion",
        "decarbonization of transport", "low-carbon transport",
        "urban mobility", "public transport", "rail transport",
        "vehicle dynamics", "automotive engineering",
    ],

    # ── Matériaux & procédés ────────────────────────────────────────────────
    "Matériaux, procédés et process industriels durables": [
        "additive manufacturing", "3d printing",
        "composite material", "fiber reinforced",
        "bio-based material", "biopolymer", "biosourced",
        "recycling", "circular economy", "life cycle assessment",
        "digital twin",
        "welding", "machining", "manufacturing process",
        "surface treatment", "coating",
        "fatigue crack", "fracture mechanics",
        "corrosion",
        "polymer", "ceramic", "alloy",
        "industrial process", "process optimization",
        "virtual reality", "augmented reality",
        "robot manipulator", "industrial robot",
        "non-destructive testing",
    ],

    # ── Ingénierie pour la santé ────────────────────────────────────────────
    # NOTE: avoid single generic words (eeg, ecg alone are ok but short terms
    # like 'health' or 'monitoring' are too broad)
    "Ingénierie pour la santé": [
        "medical imaging", "magnetic resonance imaging", "computed tomography",
        "ultrasound imaging", "echography",
        "bioinformatics", "genomics", "proteomics", "transcriptomics",
        "metagenomics", "microbiome", "microbial ecology",
        "virology", "bacteriophage", "virus diversity",
        "biomechanics", "musculoskeletal", "gait analysis", "joint kinematics",
        "robot-assisted surgery", "surgical robot", "laparoscopic surgery",
        "prosthetic limb", "orthotic device", "lower limb exoskeleton",
        "clinical decision", "medical diagnosis", "clinical trial",
        "drug delivery", "tissue engineering", "bioprinting", "scaffold",
        "electroencephalography", "electromyography",
        "patient outcome", "telemedicine", "brain-computer interface",
        "computational medicine", "in silico medicine", "physiological signal",
        "neural interface", "health informatics",
        "ecology", "biodiversity", "species diversity", "microbial community",
    ],
}

# =============================================================================
# LEVEL 2 — TFIDF on title + abstract in English  (extended English lexicon)
# We use English descriptions of the axes, much richer than the French ones,
# so that the TF-IDF works in the same language as the abstracts.
# =============================================================================
# TF-IDF axis descriptions — ONLY use specific multi-word phrases or rare
# domain nouns.  Avoid generic single words (computer, signal, model, system,
# method, analysis, simulation, data, network, control, performance, etc.)
# that would appear in abstracts for ANY engineering discipline.
AXIS_DESCRIPTIONS_EN = {
    "Production et gestion des énergies renouvelables": """
    offshore wind turbine tidal stream tidal turbine wave energy converter
    ocean energy photovoltaic solar panel solar cell hydrogen fuel cell
    electrolyzer power-to-gas energy storage battery pack grid-scale storage
    smart grid microgrid islanded grid power flow energy management system
    renewable energy transition energy harvesting wind farm floating offshore
    hydropower geothermal district heating
    """,

    "Mobilités décarbonnées": """
    electric vehicle electric car hybrid electric vehicle plug-in hybrid
    charging station battery electric drivetrain vehicle powertrain
    autonomous vehicle self-driving vehicle connected vehicle
    ship propulsion maritime propulsion vessel propulsion wind-assisted propulsion
    sailing decarbonization of shipping hydrogen aircraft sustainable aviation
    urban mobility public transport rail freight low-carbon transport
    vehicle dynamics automotive engineering fleet electrification
    """,

    "Matériaux, procédés et process industriels durables": """
    additive manufacturing 3d printing fused deposition selective laser sintering
    carbon fiber reinforced composite bio-based polymer biopolymer
    recycling circular economy life cycle assessment environmental impact
    digital twin manufacturing welding friction stir welding machining
    surface coating fatigue crack fracture mechanics corrosion resistance
    ceramic alloy thermomechanical industrial process robot manipulator
    non-destructive testing structural health monitoring of structures
    """,

    "Ingénierie pour la santé": """
    medical imaging magnetic resonance imaging ultrasound imaging computed tomography
    bioinformatics genomics proteomics transcriptomics metagenomics sequencing
    microbiome microbial community microbial ecology virology bacteriophage
    virus diversity ecological role biodiversity species diversity
    musculoskeletal biomechanics gait analysis joint kinematics
    robot-assisted surgery surgical robot laparoscopic surgery
    prosthetic limb orthotic device lower limb rehabilitation exoskeleton
    clinical diagnosis medical decision electroencephalography electromyography
    drug delivery tissue engineering scaffold bioprinting
    brain computer neural interface telemedicine
    physiological patient outcome healthcare
    """,
}

# =============================================================================
# INSTITUTION / LAB MAPPING
# =============================================================================
LAB_ID_MAP = {
    "I4210117005": "LS2N",
    "I4210137520": "GeM",
    "I4210153154": "LHEEA",
    "I4210162214": "AAU",
    "I4210153365": "LMJL",
}

# =============================================================================
# HELPERS
# =============================================================================

def get_abstract_text(inverted_index):
    if not inverted_index:
        return ""
    positions = {}
    for word, pos_list in inverted_index.items():
        for pos in pos_list:
            positions[pos] = word
    return " ".join([positions[p] for p in sorted(positions.keys())])


def clean_text(text):
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return text


# =============================================================================
# CLASSIFICATION — LEVEL 1 : Topic keyword matching
# =============================================================================

def classify_by_topics(topic_names: list[str]) -> tuple[str | None, str, dict]:
    """
    Returns (chosen_axis, motivation, scores_dict) where scores_dict contains
    the raw keyword hit counts per axis.

    The topic_names list contains OpenAlex display_names for topics, subfields
    and fields associated with the work.
    """
    topic_text = " ".join(topic_names).lower()
    scores = {ax: 0 for ax in AXIS_NAMES}

    for axis, keywords in TOPIC_KEYWORDS.items():
        for kw in keywords:
            if kw in topic_text:
                scores[axis] += 1

    best_axis = max(scores, key=scores.get)
    best_score = scores[best_axis]

    if best_score == 0:
        return None, "", scores

    # Require a meaningful advantage over the second-best axis to avoid
    # borderline cases.  If the winner has ≥ 2 hits AND leads by ≥ 1 hit
    # over the second, we accept it.
    sorted_scores = sorted(scores.values(), reverse=True)
    second_score = sorted_scores[1] if len(sorted_scores) > 1 else 0

    if best_score >= 2 and (best_score - second_score) >= 1:
        # Find matching keywords for the motivation text
        matched_kw = [
            kw for kw in TOPIC_KEYWORDS[best_axis] if kw in topic_text
        ]
        motivation = (
            f"[Topics OpenAlex] Correspondance directe sur "
            f"{best_score} mot(s)-clé(s) : {', '.join(matched_kw[:5])}."
        )
        return best_axis, motivation, scores

    # Weak or ambiguous → let TF-IDF decide
    return None, "", scores


# =============================================================================
# CLASSIFICATION — LEVEL 2 : TF-IDF on title + abstract
# =============================================================================

def build_tfidf_classifier():
    axis_names = list(AXIS_DESCRIPTIONS_EN.keys())
    axis_texts = [AXIS_DESCRIPTIONS_EN[n] for n in axis_names]
    # ngram (1,2): unigrams + bigrams — good balance between recall and precision.
    # The axis descriptions are carefully curated to avoid generic terms, so
    # unigrams here are already domain-specific ('genomics', 'photovoltaic', etc.)
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1, sublinear_tf=True)
    axis_vectors = vectorizer.fit_transform(axis_texts)
    return vectorizer, axis_vectors, axis_names


def classify_by_tfidf(vectorizer, axis_vectors, axis_names, text) -> tuple[str, str, dict]:
    if not text.strip():
        return (
            "Autre / Non classé",
            "Données textuelles insuffisantes.",
            {ax: 0.0 for ax in axis_names},
        )

    work_vector = vectorizer.transform([text])
    similarities = cosine_similarity(work_vector, axis_vectors)[0]
    scores = {axis_names[i]: float(similarities[i]) for i in range(len(axis_names))}

    max_idx = int(similarities.argmax())
    best_score = similarities[max_idx]

    # Raised threshold to 0.05 — good balance: avoid weak matches but don't over-exclude
    if best_score < 0.05:
        return (
            "Autre / Non classé",
            "Aucune similarité significative avec les axes stratégiques.",
            scores,
        )

    chosen_axis = axis_names[max_idx]

    # Build motivation from shared keywords (bigrams/trigrams)
    feature_names = vectorizer.get_feature_names_out()
    work_tfidf = work_vector.toarray()[0]
    axis_doc_vector = axis_vectors[max_idx].toarray()[0]
    combined_importance = work_tfidf * axis_doc_vector
    top_indices = combined_importance.argsort()[-15:][::-1]
    matching_keywords = [
        feature_names[i]
        for i in top_indices
        if combined_importance[i] > 0
    ]

    if matching_keywords:
        kw_str = ", ".join(matching_keywords[:5])
        motivation = (
            f"[TF-IDF Sémantique] Similarité {best_score:.2f} — "
            f"termes communs : {kw_str}."
        )
    else:
        motivation = f"[TF-IDF Sémantique] Score de similarité globale : {best_score:.2f}."

    return chosen_axis, motivation, scores


# =============================================================================
# MAIN PROCESSING
# =============================================================================

def process_data(input_file, output_file):
    print(f"Loading {input_file}...")
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    results = data.get("results", [])
    processed_results = []

    # Build TF-IDF classifier once
    vectorizer, axis_vectors, axis_names = build_tfidf_classifier()

    print("Processing publications...")
    for work in tqdm(results):
        work_full_id = work.get("id")
        work_id = work_full_id.split("/")[-1] if work_full_id else "unknown"
        title = work.get("title", "")
        abstract = get_abstract_text(work.get("abstract_inverted_index"))

        # Collect all topic-related names from OpenAlex
        topic_display_names = []
        subfields_list = []
        topics_list = []
        for t in work.get("topics", []):
            if t.get("display_name"):
                topic_display_names.append(t["display_name"])
                topics_list.append(t["display_name"])
            if t.get("subfield", {}).get("display_name"):
                sn = t["subfield"]["display_name"]
                topic_display_names.append(sn)
                subfields_list.append(sn)
            if t.get("field", {}).get("display_name"):
                topic_display_names.append(t["field"]["display_name"])

        keywords = " ".join([kw.get("display_name", "") for kw in work.get("keywords", [])])
        concepts = " ".join([c.get("display_name", "") for c in work.get("concepts", [])])

        # ── Level 1: Topic keyword matching ────────────────────────────────
        chosen_axis, motivation, l1_scores = classify_by_topics(topic_display_names)

        # ── Level 2: TF-IDF fallback ────────────────────────────────────────
        if chosen_axis is None:
            full_text = clean_text(f"{title} {abstract} {keywords} {concepts}")
            chosen_axis, motivation, l2_scores = classify_by_tfidf(
                vectorizer, axis_vectors, axis_names, full_text
            )
            axis_scores = l2_scores
        else:
            axis_scores = {ax: float(l1_scores.get(ax, 0)) for ax in axis_names}

        # ── Lab & Authors ────────────────────────────────────────────────────
        nantes_authors = []
        author_labs = set()

        for auth in work.get("authorships", []):
            author_name = auth.get("author", {}).get("display_name", "Unknown")
            is_centrale = False
            labs_for_this_author = []

            for inst in auth.get("institutions", []):
                inst_full_id = inst.get("id")
                inst_id = inst_full_id.split("/")[-1] if inst_full_id else ""
                if inst_id == "I100445878":
                    is_centrale = True
                if inst_id in LAB_ID_MAP:
                    labs_for_this_author.append(LAB_ID_MAP[inst_id])
                for lid_full in inst.get("lineage", []):
                    lid = lid_full.split("/")[-1] if lid_full else ""
                    if lid in LAB_ID_MAP:
                        labs_for_this_author.append(LAB_ID_MAP[lid])

            if is_centrale or labs_for_this_author:
                nantes_authors.append(author_name)
                for lab in labs_for_this_author:
                    author_labs.add(lab)

        # ── Publication metadata ─────────────────────────────────────────────
        primary_loc = work.get("primary_location") or {}
        source_data = primary_loc.get("source") or {}
        journal = source_data.get("display_name", "Inconnu")
        issn_list = source_data.get("issn", [])
        issn = issn_list[0] if issn_list else "N/A"
        labs_str = "|".join(list(author_labs)) if author_labs else "Inconnu"

        processed_results.append(
            {
                "doi": work.get("doi"),
                "work_id": work_id,
                "title": title,
                "year": work.get("publication_year"),
                "authors": "|".join(nantes_authors),
                "labs": labs_str,
                "journal": journal,
                "issn": issn,
                "subfields": "|".join(dict.fromkeys(subfields_list)),
                "topics": "|".join(dict.fromkeys(topics_list)),
                "abstract": abstract,
                "chosen_axis": chosen_axis,
                "motivation": motivation,
                **axis_scores,
            }
        )

    df = pd.DataFrame(processed_results)
    df.to_parquet(output_file, index=False)
    print(f"Saved {len(df)} publications to {output_file}")

    # CSV export for Grist import
    csv_output = "publications_centrale_axes_strategiques.csv"
    rename_map = {
        "year": "Année",
        "title": "Titre",
        "authors": "Auteurs (Centrale)",
        "journal": "Revue",
        "issn": "ISSN",
        "subfields": "Sous-disciplines",
        "topics": "Sujets",
        "chosen_axis": "Axe Retenu",
        "motivation": "Motivation",
        "abstract": "Résumé",
    }
    df_csv = df.rename(columns=rename_map)
    df_csv.to_csv(csv_output, index=False, encoding="utf-8")
    print(f"Exported {csv_output} for Grist import.")


if __name__ == "__main__":
    process_data("centrale-2022-2026.json", "centrale_axes_data.parquet")
