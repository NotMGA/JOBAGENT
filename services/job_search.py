import os
from typing import Any
import requests
from dotenv import load_dotenv

from config import FRANCE_TRAVAIL_SEARCH_URL, FRANCE_TRAVAIL_TOKEN_URL

load_dotenv()

_token_cache: dict[str, Any] = {}
SORT_RECENT_FIRST = "1"


def get_code_insee(nom_ville: str) -> str:
    """Récupère le code INSEE d'une commune à partir de son nom."""
    ville_clean = nom_ville.strip()
    
    if ville_clean.isdigit() and len(ville_clean) == 5:
        return ville_clean
        
    try:
        url = f"https://geo.api.gouv.fr/communes?nom={ville_clean}&boost=population&limit=1"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if data:
                return data[0]['code']
    except Exception as e:
        print(f"Erreur lors de la recherche du code INSEE pour '{nom_ville}': {e}")
        
    return ville_clean


def _get_access_token() -> str:
    client_id = os.getenv("FRANCE_TRAVAIL_CLIENT_ID")
    client_secret = os.getenv("FRANCE_TRAVAIL_CLIENT_SECRET")

    # Fallback vers Streamlit Secrets si non trouvé dans les env vars
    if not client_id or not client_secret:
        try:
            import streamlit as st
            client_id = client_id or st.secrets.get("FRANCE_TRAVAIL_CLIENT_ID")
            client_secret = client_secret or st.secrets.get("FRANCE_TRAVAIL_CLIENT_SECRET")
        except Exception:
            pass

    if not client_id or not client_secret:
        raise ValueError(
            "Identifiants France Travail manquants dans .env ou Streamlit Secrets."
        )

    if _token_cache.get("token"):
        return _token_cache["token"]

    response = requests.post(
        FRANCE_TRAVAIL_TOKEN_URL,
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": "api_offresdemploiv2 o2dsoffre",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )
    response.raise_for_status()

    token = response.json()["access_token"]
    _token_cache["token"] = token
    return token


def _build_description(offer: dict) -> str:
    parts = []
    for key in ("description", "competences", "qualitesProfessionnelles"):
        value = offer.get(key)
        if value:
            parts.append(str(value))
    return "\n".join(parts).strip()


def _get_publication_date(offer: dict) -> str:
    return offer.get("dateActualisation") or offer.get("dateCreation") or ""


def _sort_by_publication_date(offers: list[dict]) -> list[dict]:
    return sorted(
        offers,
        key=lambda offer: offer.get("date_publication") or "",
        reverse=True,
    )


def _normalize_offer(offer: dict) -> dict:
    entreprise = offer.get("entreprise") or {}
    lieu = offer.get("lieuTravail") or {}
    origine = offer.get("origineOffre") or {}

    ville = lieu.get("libelle") or ""
    code_postal = lieu.get("codePostal") or ""
    location = f"{ville} {code_postal}".strip()

    offer_id = offer.get("id") or ""
    url = origine.get("urlOrigine") or (
        f"https://candidat.francetravail.fr/offres/recherche/detail/{offer_id}"
        if offer_id
        else ""
    )

    return {
        "id_offre": str(offer_id),
        "titre": offer.get("intitule") or "Sans titre",
        "entreprise": entreprise.get("nom") or "Non renseigné",
        "lieu": location or "Non renseigné",
        "description": _build_description(offer) or "Description non disponible",
        "url": url,
        "date_publication": _get_publication_date(offer),
    }


def search_jobs(
    keywords: str,
    location: str = "",
    max_results: int = 10,
    distance: int = 10,
) -> list[dict]:
    """Search the most recently published job offers via France Travail API."""
    token = _get_access_token()

    params: dict[str, Any] = {
        "motsCles": keywords,
        "range": f"0-{max(0, max_results - 1)}",
        "sort": SORT_RECENT_FIRST,
    }
    
    if location.strip():
        code_insee = get_code_insee(location)
        params["commune"] = code_insee
        if distance > 0:
            params["distance"] = distance

    response = requests.get(
        FRANCE_TRAVAIL_SEARCH_URL,
        params=params,
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )

    # ⚠️ Gestion du code HTTP 204 (No Content)
    if response.status_code == 204:
        print("[France Travail] 0 résultat (Code 204).")
        return []

    response.raise_for_status()

    data = response.json()
    raw_offers = data.get("resultats") or []
    offers = [_normalize_offer(offer) for offer in raw_offers]
    offers = _sort_by_publication_date(offers)

    return offers[:max_results]