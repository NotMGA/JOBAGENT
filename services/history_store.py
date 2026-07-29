import uuid
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

from config import BASE_DIR, CSV_COLUMNS


def get_user_data_paths(user_id: str = "default") -> tuple[Path, Path]:
    """Restaure les chemins CSV et dossier lettres spécifiques à l'utilisateur."""
    user_dir = BASE_DIR / "data" / user_id
    user_dir.mkdir(parents=True, exist_ok=True)
    
    letters_dir = user_dir / "letters"
    letters_dir.mkdir(parents=True, exist_ok=True)
    
    csv_path = user_dir / "history.csv"
    return csv_path, letters_dir


def _ensure_csv_exists(csv_path: Path) -> None:
    if not csv_path.exists():
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        df = pd.DataFrame(columns=CSV_COLUMNS)
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")


def load_history(user_id: str = "default") -> pd.DataFrame:
    """Charge l'historique des candidatures propre à un user_id depuis son CSV."""
    csv_path, _ = get_user_data_paths(user_id)
    _ensure_csv_exists(csv_path)
    
    try:
        df = pd.read_csv(csv_path, encoding="utf-8-sig")
    except Exception as e:
        print(f"[History] Erreur de lecture du CSV pour {user_id} ({e}), réinitialisation...")
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
    user_id: str = "default",
) -> dict:
    """Ajoute une nouvelle entrée dans l'historique CSV de l'utilisateur."""
    csv_path, _ = get_user_data_paths(user_id)

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

    df = load_history(user_id)
    df = pd.concat([df, pd.DataFrame([entry])], ignore_index=True)
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")

    return entry


def read_letter_file(raw_path: str, user_id: str = "default") -> str | None:
    """Lit une lettre de motivation générée depuis le disque en toute sécurité."""
    if not raw_path:
        return None

    path_obj = Path(raw_path)

    # 1. Si le chemin est déjà absolu et existe
    if path_obj.is_absolute() and path_obj.exists():
        return path_obj.read_text(encoding="utf-8")

    # 2. Tester la résolution relative depuis le dossier racine (BASE_DIR)
    resolved_path = BASE_DIR / raw_path
    if resolved_path.exists():
        return resolved_path.read_text(encoding="utf-8")

    # 3. Tester la résolution relative dans le dossier utilisateur
    _, letters_dir = get_user_data_paths(user_id)
    user_letter_path = letters_dir / path_obj.name
    if user_letter_path.exists():
        return user_letter_path.read_text(encoding="utf-8")

    return None


def clear_history(user_id: str = "default") -> None:
    """Réinitialise l'historique CSV et supprime les lettres de la session spécifiée."""
    csv_path, letters_dir = get_user_data_paths(user_id)

    # 1. Réinitialise le CSV avec les en-têtes vides
    df = pd.DataFrame(columns=CSV_COLUMNS)
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")

    # 2. Nettoie le dossier des lettres de cet utilisateur uniquement
    if letters_dir.exists() and letters_dir.is_dir():
        for file in letters_dir.glob("*.txt"):
            try:
                file.unlink()
            except Exception as e:
                print(f"[History] Impossible de supprimer {file} : {e}")