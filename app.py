import re
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
st.caption("Assistant local de candidature — CV, recherche multi-sources & scoring Groq (Llama 3.3)")

# Chargement du profil sauvegardé au premier démarrage
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
        return str(date_value)

    return parsed.strftime("%d/%m/%Y")


def sanitize_filename(name: str) -> str:
    clean = re.sub(r"[^\w\s-]", "", name, flags=re.UNICODE)
    return re.sub(r"[-\s]+", "_", clean).strip("_")


def render_history_table() -> None:
    history = load_history()

    if history.empty:
        st.info("Aucune candidature enregistrée pour le moment.")
        return

    # --- Bouton d'effacement de l'historique ---
    col_space, col_clear = st.columns([4, 1])
    with col_clear:
        if st.button("🗑️ Effacer l'historique", type="secondary", width="stretch"):
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
        width="stretch",
        hide_index=True,
    )

    st.subheader("Télécharger les lettres")
    has_letters = False
    for _, row in history.iterrows():
        if str(row.get("lm_generee")).lower() != "oui" or not row.get("chemin_lm"):
            continue

        letter_content = read_letter_file(str(row["chemin_lm"]))
        if not letter_content:
            continue

        has_letters = True
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            st.write(
                f"**{row['titre']}** — {row['entreprise']} "
                f"(score : {row['score_coherence']}/10)"
            )
        with col2:
            if row.get("url_offre"):
                st.link_button("Postuler", str(row["url_offre"]), width="stretch")
        with col3:
            safe_title = sanitize_filename(str(row['titre']))
            safe_company = sanitize_filename(str(row['entreprise']))
            filename = f"LM_{safe_title}_{safe_company}.txt"

            st.download_button(
                label="📥 Télécharger LM",
                data=letter_content,
                file_name=filename,
                mime="text/plain",
                key=f"dl_{row['id']}",
                width="stretch",
            )

    if not has_letters:
        st.caption("Aucune lettre de motivation disponible au téléchargement.")


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

    # --- Visualisation du CV ---
    if st.session_state.cv_text:
        st.caption("✅ CV chargé en mémoire.")
        with st.popover("👁️ Voir le CV extrait", width="stretch"):
            st.text_area(
                "Texte brut extrait du CV",
                value=st.session_state.cv_text,
                height=350,
                disabled=True,
            )

    st.divider()

    # --- Importation de la LM Type (TXT ou PDF) ---
    lm_file = st.file_uploader("Importer une LM type (TXT ou PDF, optionnel)", type=["txt", "pdf"])
    if lm_file is not None:
        try:
            if lm_file.name.endswith(".pdf"):
                imported_lm = extract_text_from_pdf(lm_file.read())
            else:
                imported_lm = lm_file.read().decode("utf-8")

            st.session_state.lm_template = imported_lm
            save_lm_template(imported_lm)
            st.success("Lettre type importée et sauvegardée !")
        except Exception as exc:
            st.error(f"Erreur d'importation LM : {exc}")

    # --- Zone de texte de la LM Type ---
    lm_template_input = st.text_area(
        "Lettre de Motivation type (optionnel)",
        value=st.session_state.lm_template,
        height=180,
        placeholder="Collez ici votre modèle (facultatif si vous souhaitez juste évaluer les offres)...",
    )

    if lm_template_input != st.session_state.lm_template:
        st.session_state.lm_template = lm_template_input
        save_lm_template(lm_template_input)

    score_threshold = st.number_input(
        "Note minimale pour générer la LM",
        min_value=0.0,
        max_value=10.0,
        value=float(DEFAULT_SCORE_THRESHOLD),
        step=0.5,
        help="Seuil de cohérence à partir duquel la lettre de motivation est générée automatiquement.",
    )

    auto_generate = st.toggle(
        f"Activer la génération automatique si score >= {score_threshold}",
        value=True,
    )

    st.divider()
    st.subheader("Recherche d'offres")

    keywords = st.text_input("Mots-clés", placeholder="Ex : développeur Python")
    location = st.text_input("Lieu (optionnel)", placeholder="Ex : Pau ou 64445")
    
    distance = st.number_input(
        "Rayon (km)",
        min_value=0,
        max_value=100,
        value=10,
        step=5,
    )

    max_results = st.number_input(
        "Offres max à traiter",
        min_value=1,
        max_value=50,
        value=10,
    )

    # ⚠️ SEUL LE CV EST DÉSORMAIS OBLIGATOIRE
    can_process = bool(st.session_state.cv_text and st.session_state.cv_text.strip())
    if not can_process:
        st.warning("Veuillez importer un CV pour lancer le traitement.")

    process_button = st.button(
        "🚀 Lancer le traitement",
        type="primary",
        disabled=not can_process,
        width="stretch",
    )


# ==========================================
# ZONE PRINCIPALE : TRAITEMENT & HISTORIQUE
# ==========================================
st.header("Historique des candidatures")

if process_button:

    # Charger les URLs ou identifiants déjà analysés
history_df = load_history()
existing_urls = set()
if not history_df.empty and "url_offre" in history_df.columns:
    existing_urls = set(history_df["url_offre"].dropna().astype(str))
    if not keywords.strip():
        st.error("Veuillez renseigner des mots-clés pour la recherche d'offres.")
    else:
        try:
            with st.status("Traitement en cours...", expanded=True) as status:
                st.write("Recherche des offres en cours...")
                
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
                    st.write(f"**{len(offers)}** offre(s) retenue(s).")
                    progress = st.progress(0)
                    total = len(offers)

                    has_lm_template = bool(st.session_state.lm_template and st.session_state.lm_template.strip())

                    for index, offer in enumerate(offers):
                        offer_url = str(offer.get("url_offre", ""))

# Si l'offre a déjà été traitée, on la saute
if offer_url in existing_urls:
    st.write(f"⏭️ Offre déjà analysée précédemment : **{offer['titre']}** ({offer['entreprise']})")
    progress.progress((index + 1) / total)
    continue
                        published_on = format_publication_date(offer.get("date_publication", ""))
                        st.write(
                            f"Analyse [{index + 1}/{total}] : **{offer['titre']}** "
                            f"({offer['entreprise']}) — {published_on}"
                        )

                        score, justification = score_coherence(
                            st.session_state.cv_text, offer
                        )
                        st.write(f"👉 Score : **{score}/10** — *{justification}*")

                        entry_id = uuid.uuid4().hex[:8]
                        lm_path = ""
                        lm_generated = False

                        if auto_generate and score >= score_threshold:
                            if has_lm_template:
                                st.write("✍️ Génération de la lettre de motivation...")
                                lm_path = generate_cover_letter(
                                    st.session_state.cv_text,
                                    offer,
                                    st.session_state.lm_template,
                                    entry_id,
                                )
                                lm_generated = True
                            else:
                                st.caption("ℹ️ Lettre non générée : aucun modèle de lettre de motivation fourni.")

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
                    st.success("Traitement terminé ! L'historique a été mis à jour.")

        except Exception as exc:
            st.error(f"Erreur lors du traitement : {exc}")

# Affichage du tableau de suivi
render_history_table()