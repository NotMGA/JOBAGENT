from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()

# Modèles & Paramètres
MODEL_NAME = "llama-3.3-70b-versatile"
OLLAMA_MODEL = "llama3.2"
OLLAMA_HOST = "http://localhost:11434"
DEFAULT_SCORE_THRESHOLD = 7.0

# APIs Externes
FRANCE_TRAVAIL_TOKEN_URL = "https://entreprise.francetravail.fr/connexion/oauth2/access_token?realm=/partenaire"
FRANCE_TRAVAIL_SEARCH_URL = "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search"

# Structure de l'historique
CSV_COLUMNS = [
    "id",
    "date_traitement",
    "date_publication",
    "titre",
    "entreprise",
    "lieu",
    "url_offre",
    "score_coherence",
    "lm_generee",
    "chemin_lm",
    "description_offre",
]
