import json
import pandas as pd
from tqdm import tqdm

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
        "ship hydrodynamics", "vessel hydrodynamics", "ship resistance",
        "ship maneuvering", "vessel maneuvering", "naval architecture",
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
        "composite material", "fiber reinforced", "mechanical behavior of composite",
        "bio-based material", "biopolymer", "biosourced",
        "recycling", "circular economy", "life cycle assessment",
        "welding", "machining", "manufacturing process",
        "surface treatment", "coating",
        "fatigue crack", "fracture mechanics",
        "corrosion",
        "polymer", "ceramic", "alloy",
        "virtual reality", "augmented reality",
        "robot manipulator", "industrial robot",
        "non-destructive testing",
        "concrete", "cement", "reinforced concrete", "geopolymer",
        "elasticity and material", "rock mechanics",
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

    # Accept if ≥2 hits with a clear lead, OR exactly 1 hit with no competition
    if (best_score >= 2 and (best_score - second_score) >= 1) or (best_score == 1 and second_score == 0):
        matched_kw = [
            kw for kw in TOPIC_KEYWORDS[best_axis] if kw in topic_text
        ]
        motivation = (
            f"[Topics OpenAlex] Correspondance directe sur "
            f"{best_score} mot(s)-clé(s) : {', '.join(matched_kw[:5])}."
        )
        return best_axis, motivation, scores

    return None, "", scores




# =============================================================================
# MAIN PROCESSING
# =============================================================================

def process_data(input_file, output_file):
    print(f"Loading {input_file}...")
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    results = data.get("results", [])
    processed_results = []

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

        # ── Level 1: Topic keyword matching ────────────────────────────────
        chosen_axis, motivation, l1_scores = classify_by_topics(topic_display_names)

        if chosen_axis is None:
            chosen_axis = "Autre / Non classé"
            motivation = "Aucune correspondance sur les topics OpenAlex."
        axis_scores = {ax: float(l1_scores.get(ax, 0)) for ax in AXIS_NAMES}

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
