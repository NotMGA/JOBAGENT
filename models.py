# models.py
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field


class JobOffer(BaseModel):
    """Représente une offre d'emploi normalisée quelle que soit la source."""
    id: Optional[str] = None
    title: str
    company: str
    location: str
    url: str = ""
    description: str = ""
    publication_date: Optional[str] = None

    @property
    def signature(self) -> str:
        """Génère une empreinte unique pour le dédoublonnage."""
        clean_title = "".join(c for c in self.title.lower() if c.isalnum())
        clean_company = "".join(c for c in self.company.lower() if c.isalnum())
        return f"{clean_title}-{clean_company}"


class ApplicationEntry(BaseModel):
    """Représente une candidature enregistrée dans l'historique."""
    id: str
    processed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    job: JobOffer
    coherence_score: float
    cover_letter_generated: bool
    cover_letter_path: Optional[str] = None

    def to_csv_dict(self) -> dict:
        """Exporte l'objet sous forme de dictionnaire plat pour le fichier CSV."""
        return {
            "id": self.id,
            "date_traitement": self.processed_at.isoformat(),
            "date_publication": self.job.publication_date or "",
            "titre": self.job.title,
            "entreprise": self.job.company,
            "lieu": self.job.location,
            "url_offre": self.job.url,
            "score_coherence": round(self.coherence_score, 1),
            "lm_generee": "oui" if self.cover_letter_generated else "non",
            "chemin_lm": self.cover_letter_path or "",
            "description_offre": self.job.description[:500],
        }


class UserProfile(BaseModel):
    """Profil utilisateur contenant le CV et la lettre type."""
    cv_text: str = ""
    lm_template_text: str = ""