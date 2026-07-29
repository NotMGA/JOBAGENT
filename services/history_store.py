import uuid
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

from config import BASE_DIR, CSV_COLUMNS, HISTORY_CSV, LETTERS_DIR


def _ensure_csv_exists() -> None:
    if not HISTORY_CSV.exists():
        HISTORY_CSV.parent.mkdir(parents=True, exist_ok=True)
        df = pd.DataFrame(columns=CSV_COLUMNS)
        df.to_csv(HISTORY_CSV, index=False, encoding="utf-8-sig")


def load_history() -> pd.DataFrame:
    """Load application history from CSV."""
    _ensure_csv_exists()
    try:
        df = pd.read_csv(HISTORY_CSV, encoding="utf-8-sig")
    except Exception as e:
        print(f"[History] Erreur de lecture du CSV ({e}), réinitialisation...")
        df = pd.DataFrame(columns=CSV_COLUMNS)

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
        "chemin_lm": str(lm_path) if lm_generated else "",
        "description_offre": (job.get("description", "") or "")[:500],
    }

    df = load_history()
    df = pd.concat([df, pd.DataFrame([entry])], ignore_index=True)
    df.to_csv(HISTORY_CSV, index=False, encoding="utf-8-sig")

    return entry


def read_letter_file(raw_path: str) -> str | None:
    """Read a generated cover letter from disk safely."""
    if not raw_path:
        return None

    path_obj = Path(raw_path)

    # Si le chemin est déjà absolu et existe
    if path_obj.is_absolute() and path_obj.exists():
        return path_obj.read_text(encoding="utf-8")

    # Sinon, tester la résolution relative depuis BASE_DIR
    resolved_path = BASE_DIR / raw_path
    if resolved_path.exists():
        return resolved_path.read_text(encoding="utf-8")

    return None


def clear_history() -> None:
    """Réinitialise le CSV de l'historique et supprime les lettres générées."""
    # 1. Réinitialise le CSV avec les en-têtes vides
    HISTORY_CSV.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(columns=CSV_COLUMNS)
    df.to_csv(HISTORY_CSV, index=False, encoding="utf-8-sig")

    # 2. Nettoie le dossier configuré des lettres (LETTERS_DIR)
    if LETTERS_DIR.exists() and LETTERS_DIR.is_dir():
        for file in LETTERS_DIR.glob("*.txt"):
            try:
                file.unlink()
            except Exception as e:
                print(f"[History] Impossible de supprimer {file} : {e}")