import os
import uuid
import pandas as pd
import streamlit as st

# Config globale
from config import DEFAULT_SCORE_THRESHOLD

# --- IMPORTS DES 3 NOUVEAUX FICHIERS ---
from models import ApplicationEntry, JobOffer
from repositories.file_repository import FileStorageRepository  # Hérite de base.py pour le stockage local / fichiers

# --- IMPORTS DES SERVICES ADAPTÉS ---
from services.job_search_orchestrator import search_all_sources
from services.lm_generator import generate_cover_letter
from services.pdf_parser import extract_text_from_pdf
from services.scorer import score_coherence


# --- CONFIGURATION PAGE & INITIALISATION ---
st.set_page_config(
    page_title="JOBAGENT — Assistant Candidature",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Chargement du style CSS s'il existe
if os.path.exists("style.css"):
    with open("style.css", "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Session unique par utilisateur
if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())

user_id = st.session_state.user_id

# Instanciation du repository
repo = FileStorageRepository()

# Synchronisation du state Streamlit avec le repository
if "cv_text" not in st.session_state or "lm_template" not in st.session_state:
    profile = repo.get_profile(user_id=user_id)
    st.session_state.cv_text = profile.cv_text or ""
    st.session_state.lm_template = profile.lm_template_text or ""


# ==========================================
# FONCTIONS D'AFFICHAGE (INTERFACE & METRICS)
# ==========================================
def render_history_dashboard():
    # Récupération sous forme de liste d'objets ApplicationEntry
    entries = repo.load_history(user_id=user_id)

    if not entries:
        st.info("💡 Aucune recherche enregistrée. Définissez vos critères à gauche pour démarrer.")
        return

    # Conversion en DataFrame pour l'affichage
    data = [entry.to_dict() if hasattr(entry, "to_dict") else entry.__dict__ for entry in entries]
    history_df = pd.DataFrame(data)

    # Indicateurs clés
    total_offers = len(history_df)
    avg_score = round(history_df["score_coherence"].mean(), 1) if "score_coherence" in history_df and not history_df.empty else 0.0
    total_lm = len(history_df[history_df["lm_generee"] == True]) if "lm_generee" in history_df else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("📊 Offres analysées", total_offers)
    col2.metric("🎯 Score moyen", f"{avg_score} / 10" if total_offers > 0 else "N/A")
    col3.metric("📝 Lettres créées", total_lm)

    st.divider()

    # En-tête + bouton effacer
    col_title, col_clear = st.columns([3, 1])
    with col_title:
        st.subheader("📋 Historique des candidatures")
    with col_clear:
        if st.button("🗑️ Effacer l'historique", use_container_width=True):
            repo.clear_history(user_id=user_id)
            st.toast("Historique réinitialisé !", icon="🧹")
            st.rerun()

    # Mise en forme pour le tableau
    display_df = history_df.copy()
    if "date_traitement" in display_df.columns:
        display_df["date_traitement"] = pd.to_datetime(display_df["date_traitement"], errors="coerce").dt.strftime("%d/%m/%Y %H:%M")

    st.dataframe(
        display_df,
        column_config={
            "url_offre": st.column_config.LinkColumn("Lien offre", display_text="Consulter ↗"),
            "score_coherence": st.column_config.ProgressColumn("Score /10", format="%d/10", min_value=0, max_value=10),
        },
        use_container_width=True,
        hide_index=True,
    )

    st.divider()
    st.subheader("📩 Lettres de motivation générées")

    has_letters = False
    for entry in entries:
        # Manipulation via l'objet ApplicationEntry
        if getattr(entry, "lm_generee", False) and getattr(entry, "chemin_lm", None):
            letter_content = repo.read_letter(entry.chemin_lm)
            if letter_content:
                has_letters = True
                with st.container(border=True):
                    c_info, c_score, c_actions = st.columns([3, 1, 2])
                    with c_info:
                        st.markdown(f"### **{entry.titre}**")
                        st.caption(f"🏢 **{entry.entreprise}**")
                    with c_score:
                        st.metric("Score", f"{entry.score_coherence}/10")
                    with c_actions:
                        if getattr(entry, "url_offre", None):
                            st.link_button("🔗 Offre", entry.url_offre, use_container_width=True)
                        
                        st.download_button(
                            label="📥 Télécharger (.txt)",
                            data=letter_content,
                            file_name=f"LM_{entry.entreprise}_{entry.titre}.txt",
                            mime="text/plain",
                            key=f"dl_{entry.id}",
                            type="primary",
                            use_container_width=True,
                        )
                    
                    with st.expander("👁️ Prévisualiser la lettre"):
                        st.text_area("Contenu", value=letter_content, height=180, disabled=True, label_visibility="collapsed")

    if not has_letters:
        st.caption("Aucune lettre générée pour le moment.")


# ==========================================
# HEADER PRINCIPAL
# ==========================================
st.title("💼 JOBAGENT")
st.caption("Assistant IA local — Analyse d'offres & Génération de candidatures")
st.divider()


# ==========================================
# SIDEBAR : PARAMÈTRES & PROFIL
# ==========================================
with st.sidebar:
    st.header("⚙️ Configuration")

    # 1. Gestion du CV
    st.subheader("1. Votre CV")
    cv_file = st.file_uploader("Importer votre CV (PDF)", type=["pdf"])
    if cv_file is not None:
        try:
            extracted_cv = extract_text_from_pdf(cv_file.read())
            st.session_state.cv_text = extracted_cv
            repo.save_cv(text, user_id=user_id)
            st.toast("CV mis à jour avec succès !", icon="✅")
        except Exception as exc:
            st.error(f"Erreur d'extraction : {exc}")

    if st.session_state.cv_text:
        st.success("CV chargé et prêt", icon="🟢")
        with st.popover("👁️ Aperçu du CV", use_container_width=True):
            st.text_area("Texte extrait", value=st.session_state.cv_text, height=250, disabled=True)

    st.divider()

    # 2. Modèle de Lettre (Optionnel)
    st.subheader("2. Modèle de Lettre (Optionnel)")
    lm_input = st.text_area(
        "Modèle texte personnalisé",
        value=st.session_state.lm_template,
        height=120,
        placeholder="Collez ou adaptez votre trame de lettre...",
    )
    if lm_input != st.session_state.lm_template:
        st.session_state.lm_template = lm_input
        repo.save_lm_template(text, user_id=user_id)

    st.divider()

    # 3. Critères de Recherche
    st.subheader("3. Recherche d'emploi")
    keywords = st.text_input("Mots-clés", placeholder="Ex : Développeur Web")
    location = st.text_input("Lieu", placeholder="Ex : Pau, Toulouse")
    
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

    auto_generate = st.toggle("Générer la LM si le score suffit", value=True)

    can_launch = bool(st.session_state.cv_text and st.session_state.cv_text.strip())
    if not can_launch:
        st.warning("Veuillez d'abord importer votre CV.")

    btn_search = st.button(
        "🚀 Lancer la recherche",
        type="primary",
        disabled=not can_launch,
        use_container_width=True,
    )


# ==========================================
# ZONE PRINCIPALE : TRAITEMENT DE LA RECHERCHE
# ==========================================
if btn_search:
    if not keywords.strip():
        st.error("Veuillez renseigner au moins un mot-clé.")
    else:
        try:
            # Récupération des URLs déjà traitées pour éviter les doublons
            existing_entries = repo.load_history(user_id=user_id)
            existing_urls = {
                entry.url_offre.strip()
                for entry in existing_entries
                if getattr(entry, "url_offre", None)
            }

            with st.status("Traitement en cours...", expanded=True) as status:
                st.write("🔍 Collecte des offres depuis les sources...")
                
                raw_offers = search_all_sources(
                    keywords=keywords,
                    location=location,
                    max_results=int(max_results),
                    distance=int(distance),
                )

                if not raw_offers:
                    st.warning("Aucune offre trouvée pour ces critères.")
                    status.update(label="Recherche terminée (0 résultat)", state="complete")
                else:
                    # Conversion des dictionnaires reçus par l'orchestrateur en objets JobOffer
                    job_offers = [
                        JobOffer.from_dict(off) if hasattr(JobOffer, "from_dict") else JobOffer(**off)
                        for off in raw_offers
                    ]

                    st.write(f"🎯 **{len(job_offers)}** offre(s) identifiée(s). Évaluation par l'IA...")
                    progress = st.progress(0)
                    total = len(job_offers)

                    for idx, offer in enumerate(job_offers):
                        offer_url = str(getattr(offer, "url_offre", "")).strip()

                        # Anti-doublon
                        if offer_url and offer_url in existing_urls:
                            st.write(f"⏭️ *Déjà analysée* : **{offer.titre}** chez {offer.entreprise}")
                            progress.progress((idx + 1) / total)
                            continue

                        st.write(f"⚡ [{idx + 1}/{total}] **{offer.titre}** — *{offer.entreprise}*")

                        # Évaluation via scorer (prend l'objet JobOffer ou dict selon ton adaptation)
                        score, justification = score_coherence(
                            st.session_state.cv_text, offer
                        )
                        st.write(f"&nbsp;&nbsp;&nbsp;&nbsp;⭐ Score : **{score}/10** | *{justification}*")

                        entry_id = uuid.uuid4().hex[:8]
                        lm_path = ""
                        lm_generated = False

                        # Génération de la LM si le score dépasse le seuil
                        if auto_generate and score >= score_threshold:
                            if st.session_state.lm_template.strip():
                                st.write("&nbsp;&nbsp;&nbsp;&nbsp;✍️ Rédaction de la lettre de motivation...")
                                lm_path = generate_cover_letter(
                                    st.session_state.cv_text,
                                    offer,
                                    st.session_state.lm_template,
                                    entry_id,
                                    user_id,
                                )
                                lm_generated = True

                        # Instanciation de l'objet ApplicationEntry
                        entry = ApplicationEntry(
                            id=entry_id,
                            titre=offer.titre,
                            entreprise=offer.entreprise,
                            url_offre=offer.url_offre,
                            date_publication=getattr(offer, "date_publication", ""),
                            score_coherence=score,
                            justification=justification,
                            lm_generee=lm_generated,
                            chemin_lm=lm_path,
                        )

                        # Enregistrement via le repository
                        repo.append_entry(entry, user_id=user_id)

                        if offer_url:
                            existing_urls.add(offer_url)

                        progress.progress((idx + 1) / total)

                    status.update(label="Traitement et sauvegarde terminés !", state="complete")
                    st.toast("Historique mis à jour !", icon="🎉")
                    st.rerun()

        except Exception as exc:
            st.error(f"Une erreur est survenue pendant le traitement : {exc}")

# Affichage du dashboard et de l'historique
render_history_dashboard()