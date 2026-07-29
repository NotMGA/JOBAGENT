from pathlib import Path

DATA_DIR = Path("data")
CV_PATH = DATA_DIR / "cv_profil.txt"
LETTRE_TYPE_PATH = DATA_DIR / "lettre_motivation_type.txt"


def ensure_data_dir() -> None:
    """S'assure que le dossier data/ existe."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_document(file_path: Path) -> str:
    """Lit un document s'il existe, sinon renvoie une chaîne vide."""
    ensure_data_dir()
    if file_path.exists():
        try:
            return file_path.read_text(encoding="utf-8").strip()
        except Exception as e:
            print(f"[ProfileStore] Erreur lors de la lecture de {file_path}: {e}")
            return ""
    return ""


def save_document(file_path: Path, content: str) -> None:
    """Sauvegarde le contenu texte dans le fichier spécifié."""
    ensure_data_dir()
    file_path.write_text(content, encoding="utf-8")


def get_user_profile() -> tuple[str, str]:
    """Charge le CV et la lettre type depuis les fichiers locaux."""
    cv = load_document(CV_PATH)
    lettre = load_document(LETTRE_TYPE_PATH)
    return cv, lettre


def save_cv(content: str) -> None:
    """Sauvegarde le texte du CV."""
    save_document(CV_PATH, content)


def save_lm_template(content: str) -> None:
    """Sauvegarde le texte de la lettre type."""
    save_document(LETTRE_TYPE_PATH, content)