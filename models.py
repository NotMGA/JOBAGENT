# models.py
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from pydantic import AliasChoices, BaseModel, Field


class JobOffer(BaseModel):
    """Représente une offre d'emploi normalisée quelle que soit la source."""

    id: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("id", "id_offre"),
    )
    title: str = Field(
        default="Titre inconnu",
        validation_alias=AliasChoices("title", "titre", "intitule", "label"),
    )
    company: str = Field(
        default="Entreprise inconnue",
        validation_alias=AliasChoices("company", "entreprise", "nom_entreprise"),
    )
    location: str = Field(
        default="Non précisé",
        validation_alias=AliasChoices("location", "lieu", "ville"),
    )
    url: str = Field(
        default="",
        validation_alias=AliasChoices("url", "url_offre", "link"),
    )
    description: str = Field(
        default="",
        validation_alias=AliasChoices("description", "description_offre", "details"),
    )
    publication_date: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("publication_date", "date_publication", "date"),
    )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "JobOffer":
        """Instancie une JobOffer à partir d'un dictionnaire brut (français ou anglais)."""
        return cls.model_validate(data)

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