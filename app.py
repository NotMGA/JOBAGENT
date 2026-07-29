import uuid
import pandas as pd
import streamlit as st

from config import DEFAULT_SCORE_THRESHOLD
from services.history_store import (
    append_entry,
    clear_history,
    load_history,
    read_letter_file,
)
from services.job_search_orchestrator import search_all_sources
from services.lm_generator import generate_cover_letter
from services.pdf_parser import extract_text_from_pdf
from services.profile_store import (
    get_user_profile,
    save_cv,
    save_lm_template,
)
from services.scorer import score_coherence

# --- CONFIGURATION PAGE & INITIALISATION ---
st.set_page_config(page_title="JOBAGENT", page_icon="💼", layout="wide")

st.title("JOBAGENT")
st.caption("Assistant local de candidature — CV, offres France Travail, scoring Ollama")

# Chargement du profil sauvegardé (CV & LM) au premier démarrage de la session
if "cv_text" not in st.session_state or "lm_template" not in st.session_state:
    saved_cv, saved_lm = get_user_profile()
    st.session_state.cv_text = saved_cv
    st.session_state.lm_template = saved_lm


# --- FONCTIONS UTILITAIRES ---
def format_publication_date(date_value: str) -> str:
    if not date_value:
        return "Date inconnue"

    parsed = pd.to_datetime(date_value, errors="coerce")
    if pd.isna(parsed):
        return date_value

    return parsed.strftime("%d/%m/%Y")


def render_history_table() -> None:
    history = load_history()

    if history.empty:
        st.info("Aucune candidature enregistrée pour le moment.")
        return

    # --- Bouton d'effacement de l'historique ---
    col_space, col_clear = st.columns([4, 1])
    with col_clear:
        if st.button("🗑️ Effacer l'historique", type="secondary", use_container_width=True):
            clear_history()
            st.success("L'historique a été réinitialisé.")
            st.rerun()

    display_df = history.copy()
    display_df["date_traitement"] = pd.to_datetime(
        display_df["date_traitement"], errors="coerce"
    ).dt.strftime("%d/%m/%Y %H:%M")
    display_df["date_publication"] = display_df["date_publication"].apply(
        format_publication_date
    )

    table_df = display_df[
        [
            "date_publication",
            "date_traitement",
            "titre",
            "entreprise",
            "score_coherence",
            "lm_generee",
            "url_offre",
        ]
    ].rename(
        columns={
            "date_publication": "Publiée le",
            "date_traitement": "Traitée le",
            "titre": "Titre",
            "entreprise": "Entreprise",
            "score_coherence": "Score",
            "lm_generee": "LM générée",
            "url_offre": "Lien offre",
        }
    )

    st.dataframe(
        table_df,
        column_config={
            "Lien offre": st.column_config.LinkColumn(
                "Lien offre",
                display_text="Postuler",
            ),
        },
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Télécharger les lettres")
    for _, row in history.iterrows():
        if row["lm_generee"] != "oui" or not row["chemin_lm"]:
            continue

        letter_content = read_letter_file(row["chemin_lm"])
        if not letter_content:
            continue

        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            st.write(
                f"**{row['titre']}** — {row['entreprise']} "
                f"(score : {row['score_coherence']})"
            )
        with col2:
            if row.get("url_offre"):
                st.link_button("Postuler", row["url_offre"])
        with col3:
            st.download_button(
                label="Télécharger LM",
                data=letter_content,
                file_name=f"LM_{row['titre']}_{row['entreprise']}.txt".replace(" ", "_"),
                mime="text/plain",
                key=f"download_{row['id']}",
            )


# ==========================================
# SIDEBAR : CONFIGURATION DE L'AGENT
# ==========================================
with st.sidebar:
    st.header("Configuration")

    # --- Importation et Sauvegarde du CV ---
    cv_file = st.file_uploader("Importer votre CV (PDF)", type=["pdf"])
    if cv_file is not None:
        try:
            extracted_cv = extract_text_from_pdf(cv_file.read())
            st.session_state.cv_text = extracted_cv
            save_cv(extracted_cv)
            st.success("CV importé et sauvegardé localement !")
        except ValueError as exc:
            st.error(str(exc))

    # --- Visualisation directe du CV en mémoire ---
    if st.session_state.cv_text:
        st.caption("✅ CV chargé en mémoire.")
        with st.popover("👁️ Voir le CV extrait", use_container_width=True):
            st.text_area(
                "Texte brut extrait du CV",
                value=st.session_state.cv_text,
                height=350,
                disabled=True,
            )

    # --- Importation de la LM Type via fichier ---
    lm_file = st.file_uploader("Importer une LM type (.txt)", type=["txt"])
    if lm_file is not None:
        imported_lm = lm_file.read().decode("utf-8")
        st.session_state.lm_template = imported_lm
        save_lm_template(imported_lm)
        st.success("Lettre type importée et sauvegardée !")

    # --- Zone de texte d'édition dynamique de la LM Type ---
    lm_template_input = st.text_area(
        "Lettre de Motivation type",
        value=st.session_state.lm_template,
        height=200,
        placeholder="Collez ici votre modèle de lettre de motivation...",
    )

    # Sauvegarde automatique si modification manuelle dans la zone de texte
    if lm_template_input != st.session_state.lm_template:
        st.session_state.lm_template = lm_template_input
        save_lm_template(lm_template_input)

    score_threshold = st.number_input(
        "Note minimale pour générer la LM",
        min_value=0.0,
        max_value=10.0,
        value=DEFAULT_SCORE_THRESHOLD,
        step=0.5,
        help="Seuil de cohérence à partir duquel la lettre de motivation est générée automatiquement.",
    )

    auto_generate = st.toggle(
        f"Activer la génération automatique de la LM si score >= {score_threshold}",
        value=True,
    )

    st.divider()
    st.subheader("Recherche d'offres")

    keywords = st.text_input("Mots-clés", placeholder="Ex : développeur Python")
    
    location = st.text_input("Lieu (optionnel)", placeholder="Ex : Pau ou 64445")
    distance = st.number_input(
        "Rayon autour de la ville (km)",
        min_value=0,
        max_value=100,
        value=10,
        step=5,
        help="Rayon de recherche géographique en kilomètres.",
    )

    max_results = st.number_input(
        "Nombre de dernières offres à traiter",
        min_value=1,
        max_value=50,
        value=10,
        help="Les offres sont triées par date de publication décroissante (les plus récentes en premier).",
    )

    can_process = bool(st.session_state.cv_text and st.session_state.lm_template.strip())
    if not can_process:
        st.warning("Importez un CV et renseignez une LM type pour lancer le traitement.")

    process_button = st.button(
        "Lancer le traitement",
        type="primary",
        disabled=not can_process,
        use_container_width=True,
    )


# ==========================================
# ZONE PRINCIPALE : TRAITEMENT & HISTORIQUE
# ==========================================
st.header("Historique des candidatures")

if process_button:
    if not keywords.strip():
        st.error("Veuillez renseigner des mots-clés pour la recherche d'offres.")
    else:
        try:
            with st.status("Traitement en cours...", expanded=True) as status:
                st.write("Recherche des offres les plus récentes...")
                
                offers = search_all_sources(
                    keywords=keywords,
                    location=location,
                    max_results=int(max_results),
                    distance=int(distance),
                )

                if not offers:
                    st.warning("Aucune offre trouvée pour ces critères.")
                    status.update(label="Terminé — aucune offre", state="complete")
                else:
                    st.write(
                        f"{len(offers)} offre(s) sélectionnée(s), "
                        "triées de la plus récente à la plus ancienne."
                    )
                    progress = st.progress(0)
                    total = len(offers)

                    for index, offer in enumerate(offers):
                        published_on = format_publication_date(offer.get("date_publication", ""))
                        st.write(
                            f"Analyse : **{offer['titre']}** ({offer['entreprise']}) "
                            f"— publiée le {published_on}"
                        )

                        score, justification = score_coherence(
                            st.session_state.cv_text, offer
                        )
                        st.write(f"Score : **{score}/10** — {justification}")

                        entry_id = uuid.uuid4().hex[:8]
                        lm_path = ""
                        lm_generated = False

                        if auto_generate and score >= score_threshold:
                            st.write("Génération de la lettre de motivation...")
                            lm_path = generate_cover_letter(
                                st.session_state.cv_text,
                                offer,
                                st.session_state.lm_template,
                                entry_id,
                            )
                            lm_generated = True

                        append_entry(
                            offer,
                            score,
                            lm_generated,
                            lm_path,
                            entry_id=entry_id,
                        )

                        progress.progress((index + 1) / total)

                    status.update(
                        label=f"Terminé — {total} offre(s) traitée(s)",
                        state="complete",
                    )
                    st.success("Traitement terminé. L'historique a été mis à jour.")

        except Exception as exc:
            st.error(f"Erreur lors du traitement : {exc}")

# Affichage du tableau de suivi des candidatures
render_history_table()