import json
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
    """Analyse l'adéquation entre le CV et l'offre via Groq (Llama 3.3)."""
    try:
        client = get_groq_client()
    except Exception as e:
        return 0.0, f"Erreur de configuration client Groq : {e}"

    system_instruction = (
        "Tu es un recruteur expert RH. Évalue la correspondance entre le CV et l'offre d'emploi. "
        "Tu dois IMPÉRATIVEMENT répondre uniquement avec un objet JSON valide contenant "
        "exactement deux clés : 'score' (un nombre float entre 0.0 et 10.0) et 'justification' (2 à 3 phrases max en français)."
    )

    user_content = f"""### CV DU CANDIDAT :
{cv_text[:4000]}

### OFFRE D'EMPLOI :
Titre : {offer.get('titre', '')}
Entreprise : {offer.get('entreprise', '')}
Description : {offer.get('description', '')[:3000]}
"""

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_content},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )

        content = response.choices[0].message.content.strip()
        data = json.loads(content)

        score = float(data.get("score", 0.0))
        score = min(max(score, 0.0), 10.0)
        justification = str(data.get("justification", "Aucune justification fournie.")).strip()

        return round(score, 1), justification

    except Exception as err:
        print(f"[Groq Scorer] Erreur lors du calcul du score : {err}")
        return 0.0, f"Erreur lors de l'évaluation : {err}"