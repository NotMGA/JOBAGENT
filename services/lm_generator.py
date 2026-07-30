import os
from typing import Any, Dict
from groq import Groq

from models import JobOffer
from repositories.file_repository import FileStorageRepository

MODEL_NAME = "llama-3.3-70b-versatile"


def get_groq_client() -> Groq:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        try:
            import streamlit as st
            api_key = st.secrets.get("GROQ_API_KEY")
        except Exception:
            pass

    if not api_key:
        raise ValueError("La clé GROQ_API_KEY est manquante.")
    return Groq(api_key=api_key)


def generate_cover_letter(
    cv_text: str,
    job: JobOffer,  # 👈 Utilisation du modèle Pydantic
    lm_template: str,
    entry_id: str,
    user_id: str = "default",
    repository: FileStorageRepository = None,
) -> str:
    client = get_groq_client()
    repo = repository or FileStorageRepository()

    system_instruction = (
        "Tu es un assistant rédactionnel expert en recrutement. "
        "Ton objectif est de rédiger une lettre de motivation personnalisée, percutante et professionnelle en français. "
        "Inspire-toi de la lettre type fournie tout en l'adaptant précisément au profil du candidat et à l'offre. "
        "Consignes strictes : Rédige UNIQUEMENT le corps de la lettre. Pas de titre, pas d'amorce ni de commentaires d'introduction."
    )

    user_content = f"""### CV DU CANDIDAT :
{cv_text[:4000]}

### OFFRE D'EMPLOI :
Titre : {job.title}
Entreprise : {job.company}
Description : {job.description[:3000]}

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

    # Sauvegarde via le repository
    _, letters_dir = repo._get_user_paths(user_id)
    file_path = letters_dir / f"LM_{entry_id}.txt"
    file_path.write_text(letter_text, encoding="utf-8")

    return str(file_path.as_posix())