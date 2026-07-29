import os
import requests
from dotenv import load_dotenv

load_dotenv()


def search_jobs(
    keywords: str,
    location: str = "",
    max_results: int = 10,
    distance: int = 10,
) -> list[dict]:
    """Interroge l'API Adzuna France pour récupérer les offres d'emploi."""
    app_id = os.getenv("ADZUNA_APP_ID")
    app_key = os.getenv("ADZUNA_APP_KEY")

    if not app_id or not app_key:
        print("[Adzuna] Identifiants ADZUNA_APP_ID ou ADZUNA_APP_KEY manquants dans le .env")
        return []

    url = "https://api.adzuna.com/v1/api/jobs/fr/search/1"
    params = {
        "app_id": app_id.strip('"').strip("'"),
        "app_key": app_key.strip('"').strip("'"),
        "results_per_page": max_results,
        "what": keywords,
        "content-type": "application/json",
    }

    # Transmet le nom de la ville ou code postal, et le rayon de recherche
    if location.strip():
        params["where"] = location.strip()
        if distance > 0:
            params["distance"] = distance  # Adzuna gère la distance en kilomètres

    try:
        response = requests.get(url, params=params, timeout=15)
        if response.status_code != 200:
            print(f"[Adzuna] Erreur HTTP {response.status_code} : {response.text}")
            return []

        data = response.json()
    except Exception as e:
        print(f"[Adzuna] Erreur de connexion : {e}")
        return []

    results = data.get("results") or []
    print(f"[Adzuna] {len(results)} offres brutes reçues de l'API.")

    offers = []
    for item in results:
        company_info = item.get("company") or {}
        company_name = company_info.get("display_name") or "Non renseigné"

        raw_date = item.get("created") or ""
        date_publication = raw_date[:10] if raw_date else ""

        location_info = item.get("location") or {}
        area = location_info.get("area") or []
        lieu = area[-1] if area else "France"

        offers.append(
            {
                "id_offre": str(item.get("id") or ""),
                "titre": item.get("title") or "Sans titre",
                "entreprise": company_name,
                "lieu": lieu,
                "description": item.get("description") or "Description non disponible",
                "url": item.get("redirect_url") or "",
                "date_publication": date_publication,
            }
        )

    return offers