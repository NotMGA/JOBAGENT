import os
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
st.set_page_config(
    page_title="JOBAGENT — Assistant de Candidature",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Chargement dynamique du fichier CSS externe s'il existe
CSS_FILE = "style.css"
if os.path.exists(CSS_FILE):
    with open(CSS_FILE, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Initialisation du Session State
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


def render_dashboard_metrics(history_df: pd.DataFrame) -> None:
    """Affiche des indicateurs clés modernes en haut du dashboard."""
    col1, col2, col3 = st.columns(3)
    
    total_offers = len(history_df)
    avg_score = round(history_df["score_coherence"].mean(), 1) if not history_df.empty else 0.0
    total_letters = len(history_df[history_df["lm_generee"].str.lower() == "oui"]) if not history_df.empty else 0

    with col1:
        st.metric(label="📊 Offres analysées", value=total_offers)
    with col2:
        st.metric(label="🎯 Score moyen", value=f"{avg_score} / 10" if total_offers > 0 else "N/A")
    with col3:
        st.metric(label="📝 Lettres générées", value=total_letters)


def render_history_section() -> None:
    history = load_history()

    if history.empty:
        st.info("💡 Aucune candidature analysée pour le moment. Renseignez vos critères dans le menu à gauche et lancez le traitement !")
        return

    # Indicateurs visuels du tableau de bord
    render_dashboard_metrics(history)
    st.divider()

    # --- En-tête de la section Tableau + Bouton effacer ---
    col_title, col_clear = st.columns([3, 1])
    with col_title:
        st.subheader("📋 Historique des recherches")
    with col_clear:
        if st.button("🗑️ Effacer l'historique", type="secondary", width="stretch"):
            clear_history()
            st.toast("L'historique a été réinitialisé.", icon="🧹")
            st.rerun()

    display_df = history.copy()
    display_df["date_traitement"] = pd.to_datetime(
        display_df["date_traitement"], errors="coerce"
    ).dt.strftime("%d/%m/%Y %H:%M")
    display_df["date_publication"] = display_df["date_publication"].apply(format_publication_date)

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
            "titre": "Titre du poste",
            "entreprise": "Entreprise",
            "score_coherence": "Score /10",
            "lm_generee": "LM Générée",
            "url_offre": "Lien de l'offre",
        }
    )

    st.dataframe(
        table_df,
        column_config={
            "Lien de l'offre": st.column_config.LinkColumn(
                "Lien de l'offre",
                display_text="Consulter ↗",
            ),
            "Score /10": st.column_config.ProgressColumn(
                "Score /10",
                format="%d/10",
                min_value=0,
                max_value=10,
            ),
        },
        width="stretch",
        hide_index=True,
    )

    st.write("---")
    st.subheader("📩 Lettres de motivation générées")
    has_letters = False

    # Cartes modernes pour les lettres de motivation disponibles
    for _, row in history.iterrows():
        if str(row.get("lm_generee")).lower() != "oui" or not row.get("chemin_lm"):
            continue

        letter_content = read_letter_file(str(row["chemin_lm"]))
        if not letter_content:
            continue

        has_letters = True
        with st.container(border=True):
            c_info, c_score, c_actions = st.columns([3, 1, 2])
            
            with c_info:
                st.markdown(f"### **{row['titre']}**")
                st.caption(f"🏢 **{row['entreprise']}**")
            
            with c_score:
                st.metric("Score", f"{row['score_coherence']}/10")

            with c_actions:
                safe_title = sanitize_filename(str(row['titre']))
                safe_company = sanitize_filename(str(row['entreprise']))
                filename = f"LM_{safe_title}_{safe_company}.txt"

                if row.get("url_offre"):
                    st.link_button("🔗 Voir l'offre", str(row["url_offre"]), width="stretch")

                st.download_button(
                    label="📥 Télécharger la LM (.txt)",
                    data=letter_content,
                    file_name=filename,
                    mime="text/plain",
                    key=f"dl_{row['id']}",
                    type="primary",
                    width="stretch",
                )

    if not has_letters:
        st.caption("Aucune lettre de motivation disponible au téléchargement pour le moment.")


# ==========================================
# HEADER PRINCIPAL
# ==========================================
st.title("💼 JOBAGENT")
st.caption("Assistant local intelligent — Scoring IA de profil & Génération de lettres sur-mesure")
st.divider()


# ==========================================
# SIDEBAR : CONFIGURATION & PARAMS
# ==========================================
with st.sidebar:
    st.header("⚙️ Paramètres & Profil")

    # --- Section CV ---
    st.subheader("1. Mon CV")
    cv_file = st.file_uploader("Importer un CV (PDF)", type=["pdf"], help="Le texte extrait servira d'évaluation pour le scoring.")
    if cv_file is not None:
        try:
            extracted_cv = extract_text_from_pdf(cv_file.read())
            st.session_state.cv_text = extracted_cv
            save_cv(extracted_cv)
            st.toast("CV importé avec succès !", icon="✅")
        except ValueError as exc:
            st.error(str(exc))

    if st.session_state.cv_text:
        st.success("CV prêt et chargé en mémoire", icon="🟢")
        with st.popover("👁️ Examiner le texte extrait du CV", width="stretch"):
            st.text_area(
                "Aperçu du texte brut",
                value=st.session_state.cv_text,
                height=300,
                disabled=True,
            )

    st.divider()

    # --- Section LM Type ---
    st.subheader("2. Modèle de Lettre (Optionnel)")
    lm_file = st.file_uploader("Importer un modèle (TXT ou PDF)", type=["txt", "pdf"])
    if lm_file is not None:
        try:
            if lm_file.name.endswith(".pdf"):
                imported_lm = extract_text_from_pdf(lm_file.read())
            else:
                imported_lm = lm_file.read().decode("utf-8")

            st.session_state.lm_template = imported_lm
            save_lm_template(imported_lm)
            st.toast("Modèle de lettre mis à jour !", icon="📄")
        except Exception as exc:
            st.error(f"Erreur d'importation LM : {exc}")

    lm_template_input = st.text_area(
        "Modèle texte personnalisé",
        value=st.session_state.lm_template,
        height=140,
        placeholder="Collez ou adaptez votre trame de lettre type ici...",
    )

    if lm_template_input != st.session_state.lm_template:
        st.session_state.lm_template = lm_template_input
        save_lm_template(lm_template_input)

    st.divider()

    # --- Critères de génération ---
    st.subheader("3. Moteur de Recherche")
    keywords = st.text_input("Mots-clés", placeholder="Ex : Développeur Python")
    location = st.text_input("Lieu", placeholder="Ex : Pau, Toulouse, 64000")
    
    col_r, col_m = st.columns(2)
    with col_r:
        distance = st.number_input("Rayon (km)", min_value=0, max_value=100, value=10, step=5)
    with col_m:
        max_results = st.number_input("Offres max", min_value=1, max_value=50, value=10)

    score_threshold = st.number_input(
        "Seuil minimum (/10) pour LM",
        min_value=0.0,
        max_value=10.0,
        value=float(DEFAULT_SCORE_THRESHOLD),
        step=0.5,
    )

    auto_generate = st.toggle("Générer automatiquement la LM si le seuil est atteint", value=True)

    can_process = bool(st.session_state.cv_text and st.session_state.cv_text.strip())
    if not can_process:
        st.warning("Veuillez importer un CV pour pouvoir lancer la recherche.")

    process_button = st.button(
        "🚀 Lancer la recherche",
        type="primary",
        disabled=not can_process,
        width="stretch",
    )


# ==========================================
# ZONE PRINCIPALE : EXECUTION DU MOTEUR
# ==========================================
if process_button:
    if not keywords.strip():
        st.error("Veuillez entrer au moins un mot-clé de recherche.")
    else:
        try:
            history_df = load_history()
            existing_urls = set()
            if not history_df.empty and "url_offre" in history_df.columns:
                existing_urls = set(history_df["url_offre"].dropna().astype(str))

            with st.status("Recherche et analyse en cours...", expanded=True) as status:
                st.write("🔍 Collecte des offres auprès des sources configurées...")
                
                offers = search_all_sources(
                    keywords=keywords,
                    location=location,
                    max_results=int(max_results),
                    distance=int(distance),
                )

                if not offers:
                    st.warning("Aucune offre trouvée correspondant aux critères renseignés.")
                    status.update(label="Recherche terminée — 0 résultat", state="complete")
                else:
                    st.write(f"🎯 **{len(offers)}** offre(s) identifiée(s). Traitement IA en cours...")
                    progress = st.progress(0)
                    total = len(offers)

                    has_lm_template = bool(
                        st.session_state.lm_template and st.session_state.lm_template.strip()
                    )

                    for index, offer in enumerate(offers):
                        offer_url = str(offer.get("url_offre", ""))

                        if offer_url in existing_urls:
                            st.write(
                                f"⏭️ *Offre déjà analysée* : **{offer['titre']}** chez {offer['entreprise']}"
                            )
                            progress.progress((index + 1) / total)
                            continue

                        published_on = format_publication_date(offer.get("date_publication", ""))
                        st.write(
                            f"⚡ [{index + 1}/{total}] **{offer['titre']}** — *{offer['entreprise']}* ({published_on})"
                        )

                        score, justification = score_coherence(
                            st.session_state.cv_text, offer
                        )
                        st.write(f"&nbsp;&nbsp;&nbsp;&nbsp;⭐ Score de correspondance : **{score}/10** | *{justification}*")

                        entry_id = uuid.uuid4().hex[:8]
                        lm_path = ""
                        lm_generated = False

                        if auto_generate and score >= score_threshold:
                            if has_lm_template:
                                st.write("&nbsp;&nbsp;&nbsp;&nbsp;✍️ Rédaction de la lettre de motivation...")
                                lm_path = generate_cover_letter(
                                    st.session_state.cv_text,
                                    offer,
                                    st.session_state.lm_template,
                                    entry_id,
                                )
                                lm_generated = True
                            else:
                                st.caption("&nbsp;&nbsp;&nbsp;&nbsp;ℹ️ Pas de modèle de lettre configuré : génération ignorée.")

                        append_entry(
                            offer,
                            score,
                            lm_generated,
                            lm_path,
                            entry_id=entry_id,
                        )

                        progress.progress((index + 1) / total)

                    status.update(
                        label=f"Traitement terminé avec succès ({total} offres évaluées)",
                        state="complete",
                    )
                    st.toast("Recherche terminée et historique mis à jour !", icon="🎉")

        except Exception as exc:
            st.error(f"Une erreur est survenue pendant le traitement : {exc}")

# Affichage du dashboard/historique
render_history_section()