from io import BytesIO
from pypdf import PdfReader
from pypdf.errors import PdfReadError


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extrait le texte d'un fichier PDF (CV ou Lettre type)."""
    try:
        reader = PdfReader(BytesIO(file_bytes))
        pages_text = []

        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages_text.append(text.strip())

        full_text = "\n\n".join(pages_text).strip()
        if not full_text:
            raise ValueError(
                "Impossible d'extraire du texte du PDF. "
                "Le fichier est peut-être vide ou basé sur des images."
            )

        return full_text

    except PdfReadError:
        raise ValueError("Le fichier fourni n'est pas un document PDF valide ou est corrompu.")