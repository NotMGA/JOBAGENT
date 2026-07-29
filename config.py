from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
LETTRES_DIR = DATA_DIR / "lettres"
LETTERS_DIR = LETTRES_DIR  # Alias pour garder la compatibilité avec lm_generator.py

HISTORY_CSV = BASE_DIR / "historique_candidatures.csv"

OLLAMA_MODEL = "llama3.2"
OLLAMA_HOST = "http://localhost:11434"
DEFAULT_SCORE_THRESHOLD = 7.0

FRANCE_TRAVAIL_TOKEN_URL = "https://entreprise.francetravail.fr/connexion/oauth2/access_token?realm=/partenaire"
FRANCE_TRAVAIL_SEARCH_URL = "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search"

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
