import os
import re
from typing import Any, Dict, Tuple
from groq import Groq

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
            "La clé GROQ_API_KEY est manquante. "
            "Veuillez la configurer dans vos variables d'environnement ou secrets Streamlit."
        )
    return Groq(api_key=api_key)


def score_coherence(cv_text: str, offer: Dict[str, Any]) -> Tuple[float, str]:
    """Analyse la adéquation entre le CV et l'offre via Groq."""
    client = get_groq_client()

    prompt = f"""Tu es un recruteur expert. Évalue la correspondance entre le CV et l'offre d'emploi ci-dessous.

    ### CV DU CANDIDAT :
    {cv_text}

    ### OFFRE D'EMPLOI :
    Titre : {offer.get('titre', '')}
    Entreprise : {offer.get('entreprise', '')}
    Description : {offer.get('description', '')}

    ### CONSIGNES STRICTES :
    1. Attribue une note de 0.0 à 10.0 sur la cohérence globale du profil avec l'offre.
    2. Donne une justification très courte (2 à 3 phrases maximum).
    3. Respecte IMPÉRATIVEMENT le format de réponse suivant sur deux lignes :
    SCORE: <note>/10
    JUSTIFICATION: <explication>
    """

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )

    content = response.choices[0].message.content.strip()

    # Extraction du score et de la justification
    score = 0.0
    justification = content

    score_match = re.search(r"SCORE:\s*([\d\.]+)", content, re.IGNORECASE)
    if score_match:
        try:
            score = float(score_match.group(1))
        except ValueError:
            score = 0.0

    justif_match = re.search(r"JUSTIFICATION:\s*(.*)", content, re.IGNORECASE | re.DOTALL)
    if justif_match:
        justification = justif_match.group(1).strip()

    return score, justification
