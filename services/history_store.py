import uuid
from datetime import datetime, timezone

import pandas as pd

from config import BASE_DIR, CSV_COLUMNS, HISTORY_CSV


def _ensure_csv_exists() -> None:
    if not HISTORY_CSV.exists():
        df = pd.DataFrame(columns=CSV_COLUMNS)
        df.to_csv(HISTORY_CSV, index=False, encoding="utf-8-sig")


def load_history() -> pd.DataFrame:
    """Load application history from CSV."""
    _ensure_csv_exists()
    df = pd.read_csv(HISTORY_CSV, encoding="utf-8-sig")

    for col in CSV_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    return df[CSV_COLUMNS]


def append_entry(
    job: dict,
    score: float,
    lm_generated: bool,
    lm_path: str = "",
    entry_id: str | None = None,
) -> dict:
    """Append a new entry to the history CSV."""
    entry = {
        "id": entry_id or uuid.uuid4().hex[:8],
        "date_traitement": datetime.now(timezone.utc).isoformat(),
        "date_publication": job.get("date_publication", ""),
        "titre": job.get("titre", ""),
        "entreprise": job.get("entreprise", ""),
        "lieu": job.get("lieu", ""),
        "url_offre": job.get("url", ""),
        "score_coherence": round(score, 1),
        "lm_generee": "oui" if lm_generated else "non",
        "chemin_lm": lm_path if lm_generated else "",
        "description_offre": (job.get("description", "") or "")[:500],
    }

    df = load_history()
    df = pd.concat([df, pd.DataFrame([entry])], ignore_index=True)
    df.to_csv(HISTORY_CSV, index=False, encoding="utf-8-sig")

    return entry


def read_letter_file(relative_path: str) -> str | None:
    """Read a generated cover letter from disk."""
    if not relative_path:
        return None

    file_path = BASE_DIR / relative_path

    if not file_path.exists():
        return None

    return file_path.read_text(encoding="utf-8")

def clear_history() -> None:
    """Réinitialise le fichier CSV de l'historique et supprime les fichiers de lettres générées."""
    # 1. Réinitialise le CSV avec les en-têtes vides
    df = pd.DataFrame(columns=CSV_COLUMNS)
    df.to_csv(HISTORY_CSV, index=False, encoding="utf-8-sig")

    # 2. Nettoie le dossier des lettres de motivation s'il existe
    letters_dir = BASE_DIR / "output"  # Remplace "output" par le nom de ton dossier de lettres s'il est différent
    if letters_dir.exists() and letters_dir.is_dir():
        for file in letters_dir.glob("*.txt"):
            try:
                file.unlink()
            except Exception as e:
                print(f"[History] Impossible de supprimer {file} : {e}")