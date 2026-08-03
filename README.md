# 💼 JOBAGENT — Assistant Intelligents de Candidature

**JOBAGENT** est un assistant IA local développé avec Streamlit et Python. Il automatise le processus de recherche d'emploi en collectant des offres depuis différentes sources, en évaluant leur cohérence avec votre CV via un LLM, et en générant automatiquement des lettres de motivation personnalisées.

---

## 🚀 Fonctionnalités Principales

- 🔍 **Agrégation d'Offres :** Recherche multi-sources basée sur vos mots-clés, localisation et rayon géographique.
- 🎯 **Scoring de Cohérence IA :** Évaluation automatique (score sur 10 + justification) entre votre CV et l'offre d'emploi.
- ✍️ **Génération Automatique de Lettres :** Rédaction de lettres de motivation adaptées aux compétences demandées et basées sur votre propre modèle/trame.
- 📊 **Tableau de Bord & Historique :** Suivi dynamique des candidatures analysées, dédoublonnage automatique des URLs déjà traitées et exportation CSV.
- 📁 **Gestion de Profil :** Importation et sauvegarde locale de votre CV (PDF) et de vos trames de lettre.

---

## 🛠️ Spécifications Techniques & Stack

- **Frontend / UI :** [Streamlit](https://streamlit.io/)
- **Data Validation & Modèles :** [Pydantic v2](https://docs.pydantic.dev/)
- **Traitement de Données :** [Pandas](https://pandas.pydata.org/)
- **Parsing PDF :** PyPDF / pdfplumber
- **Langage :** Python 3.10+

---

## 📂 Structure du Projet

```text
.
├── app.py                            # Interface Streamlit et logique principale
├── models.py                         # Modèles de données Pydantic (JobOffer, ApplicationEntry, UserProfile)
├── config.py                         # Configuration globale (seuils, constantes)
├── style.css                         # Custom CSS pour Streamlit (optionnel)
├── repositories/
│   └── file_repository.py            # Gestion de la persistance locale (historique, CV, modèles)
├── services/
│   ├── job_search_orchestrator.py   # Orchestration de la collecte multi-sources d'offres
│   ├── lm_generator.py               # Génération de lettres de motivation
│   ├── pdf_parser.py                 # Extraction de texte à partir des fichiers PDF
│   └── scorer.py                     # Algorithme/Prompt de scoring de cohérence
└── data/                             # Stockage local des historiques et fichiers générés

