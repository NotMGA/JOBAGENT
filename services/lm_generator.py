import os
from pathlib import Path
from typing import Any, Dict
from groq import Groq

from config import LETTERS_DIR

MODEL_NAME = "llama-3.3-70b-versatile"


def get_groq_client() -> Groq:
    """Récupère le client Groq depuis l'environnement ou les secrets Streamlit."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        try:
            import streamlit as st
            api_key = st.secrets.get("GROQ_API_KEY")
        except Exception:
            pass

    if not api_key:
        raise ValueError(
            "La clé GROQ_API_KEY est manquante."
        )
    return Groq(api_key=api_key)


def generate_cover_letter(
    cv_text: str,
    offer: Dict[str, Any],
    lm_template: str,
    entry_id: str,
) -> str:
    """Génère une lettre de motivation personnalisée via Groq et la sauvegarde sur disque."""
    client = get_groq_client()

    system_instruction = (
        "Tu es un assistant rédactionnel expert en recrutement. "
        "Ton objectif est de rédiger une lettre de motivation personnalisée, percutante et professionnelle en français. "
        "Inspire-toi de la lettre type fournie tout en l'adaptant précisément au profil du candidat et à l'offre. "
        "Consignes strictes : Rédige UNIQUEMENT le corps de la lettre. Pas de titre, pas d'amorce ni de commentaires d'introduction."
    )

    user_content = f"""### CV DU CANDIDAT :
{cv_text[:4000]}

### OFFRE D'EMPLOI :
Titre : {offer.get('titre', '')}
Entreprise : {offer.get('entreprise', '')}
Description : {offer.get('description', '')[:3000]}

### LETTRE TYPE DE RÉFÉRENCE :
{lm_template[:3000]}
"""

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_content},
        ],
        temperature=0.4,
    )

    letter_text = response.choices[0].message.content.strip()

    # Sauvegarde locale de la lettre
    LETTERS_DIR.mkdir(parents=True, exist_ok=True)
    file_path = LETTERS_DIR / f"LM_{entry_id}.txt"
    file_path.write_text(letter_text, encoding="utf-8")

    return str(file_path.as_posix())