# repositories/base.py
from typing import Protocol, List, Optional
from models import ApplicationEntry, UserProfile, JobOffer


class HistoryRepository(Protocol):
    """Interface pour le stockage et la lecture de l'historique."""
    
    def load_history(self, user_id: str) -> List[ApplicationEntry]:
        ...

    def append_entry(self, entry: ApplicationEntry, user_id: str) -> None:
        ...

    def clear_history(self, user_id: str) -> None:
        ...

    def read_letter(self, raw_path: str, user_id: str) -> Optional[str]:
        ...


class ProfileRepository(Protocol):
    """Interface pour le stockage du profil utilisateur."""

    def get_profile(self, user_id: str) -> UserProfile:
        ...

    def save_cv(self, content: str, user_id: str) -> None:
        ...

    def save_lm_template(self, content: str, user_id: str) -> None:
        ...