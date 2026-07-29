from pathlib import Path

import ollama

from config import BASE_DIR, LETTRES_DIR, OLLAMA_HOST, OLLAMA_MODEL


def generate_cover_letter(
    cv_text: str,
    job: dict,
    lm_template: str,
    entry_id: str,
) -> str:
    """Generate a personalized cover letter and save it to disk."""
    LETTRES_DIR.mkdir(parents=True, exist_ok=True)

    prompt = f"""Tu es un assistant de rédaction ultra-précis. 

Ta mission est de compléter le MODÈLE DE LETTRE fourni en remplaçant UNIQUEMENT les variables entre accolades : 
- {{{{Entreprise}}}}
- {{{{Poste}}}}
- {{{{Intro_Entreprise}}}}
- {{{{Pourquoi_Moi}}}}

--- RÈGLES STRICTES DE REMPLISSAGE ---
1. Conserve TOUT le reste du texte de la lettre MOT POUR MOT. Ne modifie pas les paragraphes concernant Foundever, le Futuroscope, Angular/Java/Spring, ni les formules de politesse.
2. Remplis les variables ainsi :
   - {{{{Entreprise}}}} : Le nom de l'entreprise qui recrute (ou "votre entreprise" si non spécifié).
   - {{{{Poste}}}} : Le titre exact du poste de l'offre d'emploi.
   - {{{{Intro_Entreprise}}}} : Une à deux phrases courtes montrant que tu as compris l'activité de l'entreprise ou le secteur de l'offre, et pourquoi cela donne envie d'y postuler.
   - {{{{Pourquoi_Moi}}}} : Une à deux phrases percutantes faisant le pont direct entre une compétence RÉELLE du CV (et uniquement du CV !) et un besoin clé mentionné dans la description de l'offre d'emploi.
3. INTERDICTION d'inventer des compétences, outils ou diplômes qui ne sont pas dans le CV.
4. Le résultat final doit être une lettre fluide, prête à l'envoi. Ne renvoie AUCUN commentaire, uniquement la lettre complétée.

--- MODÈLE DE LETTRE DE DEPART ---
{lm_template}

--- CV (SOURCE UNIQUE DE VÉRITÉ) ---
{cv_text[:4000]}

--- OFFRE D'EMPLOI ---
Titre : {job.get("titre", "")}
Entreprise : {job.get("entreprise", "")}
Lieu : {job.get("lieu", "")}
Description : {job.get("description", "")[:3000]}
"""

    client = ollama.Client(host=OLLAMA_HOST)
    response = client.chat(
        model=OLLAMA_MODEL,
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": 0.2},  # Température très basse (0.2) pour un respect strict des consignes et du texte d'origine
    )

    letter_text = response["message"]["content"].strip()
    file_path = LETTRES_DIR / f"{entry_id}.txt"
    file_path.write_text(letter_text, encoding="utf-8")

    return str(file_path.relative_to(BASE_DIR))
