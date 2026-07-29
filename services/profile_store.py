from pathlib import Path

BASE_DATA_DIR = Path("data")


def get_user_dir(user_id: str = "default") -> Path:
    """Retourne et crée le dossier dédié à un user_id spécifique."""
    user_dir = BASE_DATA_DIR / user_id
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir


def load_document(file_path: Path) -> str:
    """Lit un document s'il existe, sinon renvoie une chaîne vide."""
    if file_path.exists():
        try:
            return file_path.read_text(encoding="utf-8").strip()
        except Exception as e:
            print(f"[ProfileStore] Erreur lors de la lecture de {file_path}: {e}")
            return ""
    return ""


def save_document(file_path: Path, content: str) -> None:
    """Sauvegarde le contenu texte dans le fichier spécifié."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")


def get_user_profile(user_id: str = "default") -> tuple[str, str]:
    """Charge le CV et la lettre type depuis le dossier de l'utilisateur."""
    user_dir = get_user_dir(user_id)
    cv_path = user_dir / "cv_profil.txt"
    lettre_path = user_dir / "lettre_motivation_type.txt"

    cv = load_document(cv_path)
    lettre = load_document(lettre_path)
    return cv, lettre


def save_cv(content: str, user_id: str = "default") -> None:
    """Sauvegarde le texte du CV pour l'utilisateur spécifié."""
    cv_path = get_user_dir(user_id) / "cv_profil.txt"
    save_document(cv_path, content)


def save_lm_template(content: str, user_id: str = "default") -> None:
    """Sauvegarde le texte de la lettre type pour l'utilisateur spécifié."""
    lettre_path = get_user_dir(user_id) / "lettre_motivation_type.txt"
    save_document(lettre_path, content)