import json
import re

import ollama

from config import OLLAMA_HOST, OLLAMA_MODEL


def _parse_score_response(response_text: str) -> tuple[float, str]:
    """Parse LLM response to extract score and justification."""
    text = response_text.strip()

    try:
        data = json.loads(text)
        score = float(data.get("score", 0))
        justification = str(data.get("justification", ""))
        return min(max(score, 0), 10), justification
    except (json.JSONDecodeError, ValueError, TypeError):
        pass

    json_match = re.search(r"\{[^{}]*\}", text, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group())
            score = float(data.get("score", 0))
            justification = str(data.get("justification", ""))
            return min(max(score, 0), 10), justification
        except (json.JSONDecodeError, ValueError, TypeError):
            pass

    score_match = re.search(r"(\d+(?:\.\d+)?)\s*/\s*10", text)
    if score_match:
        return min(max(float(score_match.group(1)), 0), 10), text

    number_match = re.search(r"\b(\d+(?:\.\d+)?)\b", text)
    if number_match:
        return min(max(float(number_match.group(1)), 0), 10), text

    return 0.0, "Score non interprétable"


def score_coherence(cv_text: str, job: dict) -> tuple[float, str]:
    """Score CV/job offer coherence from 0 to 10 using Ollama."""
    prompt = f"""Tu es un expert RH. Évalue la cohérence entre ce CV et cette offre d'emploi.

Réponds UNIQUEMENT avec un JSON valide au format :
{{"score": <nombre entre 0 et 10>, "justification": "<explication courte en français>"}}

--- CV ---
{cv_text[:4000]}

--- OFFRE ---
Titre : {job.get("titre", "")}
Entreprise : {job.get("entreprise", "")}
Lieu : {job.get("lieu", "")}
Description : {job.get("description", "")[:3000]}
"""

    client = ollama.Client(host=OLLAMA_HOST)
    response = client.chat(
        model=OLLAMA_MODEL,
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": 0.2},
    )

    content = response["message"]["content"]
    return _parse_score_response(content)
