# repositories/file_repository.py
import uuid
from pathlib import Path
from typing import List, Optional
import pandas as pd

from models import ApplicationEntry, UserProfile, JobOffer
from config import BASE_DIR, CSV_COLUMNS


class FileStorageRepository:
    """Implémentation du stockage basé sur des fichiers locaux (CSV / TXT)."""

    def __init__(self, base_dir: Path = BASE_DIR / "data"):
        self.base_dir = base_dir

    def _get_user_dir(self, user_id: str) -> Path:
        user_dir = self.base_dir / user_id
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir

    def _get_user_paths(self, user_id: str) -> tuple[Path, Path]:
        user_dir = self._get_user_dir(user_id)
        letters_dir = user_dir / "letters"
        letters_dir.mkdir(parents=True, exist_ok=True)
        csv_path = user_dir / "history.csv"
        return csv_path, letters_dir

    # --- ProfileRepository Implementation ---

    def get_profile(self, user_id: str = "default") -> UserProfile:
        user_dir = self._get_user_dir(user_id)
        cv_path = user_dir / "cv_profil.txt"
        lm_path = user_dir / "lettre_motivation_type.txt"

        cv = cv_path.read_text(encoding="utf-8").strip() if cv_path.exists() else ""
        lm = lm_path.read_text(encoding="utf-8").strip() if lm_path.exists() else ""
        return UserProfile(cv_text=cv, lm_template_text=lm)

    def save_cv(self, content: str, user_id: str = "default") -> None:
        cv_path = self._get_user_dir(user_id) / "cv_profil.txt"
        cv_path.write_text(content, encoding="utf-8")

    def save_lm_template(self, content: str, user_id: str = "default") -> None:
        lm_path = self._get_user_dir(user_id) / "lettre_motivation_type.txt"
        lm_path.write_text(content, encoding="utf-8")

    # --- HistoryRepository Implementation ---

    def _ensure_csv_exists(self, csv_path: Path) -> None:
        if not csv_path.exists():
            df = pd.DataFrame(columns=CSV_COLUMNS)
            df.to_csv(csv_path, index=False, encoding="utf-8-sig")

    def load_history(self, user_id: str = "default") -> List[ApplicationEntry]:
        csv_path, _ = self._get_user_paths(user_id)
        self._ensure_csv_exists(csv_path)

        try:
            df = pd.read_csv(csv_path, encoding="utf-8-sig")
        except Exception:
            return []

        entries = []
        for _, row in df.iterrows():
            job = JobOffer(
                title=str(row.get("titre", "")),
                company=str(row.get("entreprise", "")),
                location=str(row.get("lieu", "")),
                url=str(row.get("url_offre", "")),
                description=str(row.get("description_offre", "")),
                publication_date=str(row.get("date_publication", "")),
            )
            entries.append(
                ApplicationEntry(
                    id=str(row.get("id", "")),
                    job=job,
                    coherence_score=float(row.get("score_coherence", 0.0)),
                    cover_letter_generated=str(row.get("lm_generee", "")).lower() == "oui",
                    cover_letter_path=str(row.get("chemin_lm", "")),
                )
            )
        return entries

    def append_entry(self, entry: ApplicationEntry, user_id: str = "default") -> None:
        csv_path, _ = self._get_user_paths(user_id)
        self._ensure_csv_exists(csv_path)

        df = pd.read_csv(csv_path, encoding="utf-8-sig")
        new_row = pd.DataFrame([entry.to_csv_dict()])
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")

    def read_letter(self, raw_path: str, user_id: str = "default") -> Optional[str]:
        if not raw_path:
            return None
        path_obj = Path(raw_path)
        if path_obj.is_absolute() and path_obj.exists():
            return path_obj.read_text(encoding="utf-8")

        _, letters_dir = self._get_user_paths(user_id)
        user_letter_path = letters_dir / path_obj.name
        if user_letter_path.exists():
            return user_letter_path.read_text(encoding="utf-8")
        return None

    def clear_history(self, user_id: str = "default") -> None:
        csv_path, letters_dir = self._get_user_paths(user_id)
        df = pd.DataFrame(columns=CSV_COLUMNS)
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")

        if letters_dir.exists():
            for file in letters_dir.glob("*.txt"):
                try:
                    file.unlink()
                except Exception as e:
                    print(f"[Storage] Erreur suppression {file}: {e}")