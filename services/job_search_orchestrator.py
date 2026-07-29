from services.job_search import search_jobs as search_france_travail
from services.adzuna_search import search_jobs as search_adzuna


def search_all_sources(
    keywords: str,
    location: str = "",
    max_results: int = 10,
    distance: int = 10,
) -> list[dict]:
    """Combine France Travail et Adzuna, nettoie les doublons et trie par date."""
    all_offers = []
    seen_signatures = set()

    # 1. France Travail (Prioritaire)
    try:
        ft_offers = search_france_travail(
            keywords=keywords,
            location=location,
            max_results=max_results,
            distance=distance,
        )
        for offer in ft_offers:
            sig = f"{offer['titre'].lower().strip()}-{offer['entreprise'].lower().strip()}"
            seen_signatures.add(sig)
            all_offers.append(offer)
        print(f"[Orchestrateur] {len(ft_offers)} offres France Travail.")
    except Exception as e:
        print(f"[Orchestrateur] Erreur France Travail : {e}")

    # 2. Adzuna (Indeed, HelloWork, etc.)
    try:
        adz_offers = search_adzuna(
            keywords=keywords,
            location=location,
            max_results=max_results + 5,
            distance=distance,
        )
        added_adzuna = 0
        for offer in adz_offers:
            sig = f"{offer['titre'].lower().strip()}-{offer['entreprise'].lower().strip()}"
            if sig not in seen_signatures:
                seen_signatures.add(sig)
                all_offers.append(offer)
                added_adzuna += 1
        print(f"[Orchestrateur] {added_adzuna} nouvelles offres Adzuna ajoutées.")
    except Exception as e:
        print(f"[Orchestrateur] Erreur Adzuna : {e}")

    # 3. Tri du plus récent au plus ancien
    all_offers.sort(key=lambda x: x.get("date_publication") or "", reverse=True)

    return all_offers[:max_results]