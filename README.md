# JOBAGENT

Application web locale en Python (Streamlit) pour automatiser la recherche d'offres d'emploi, évaluer la cohérence CV/offre via Ollama, et générer des lettres de motivation personnalisées.

## Fonctionnalités

- Import de CV au format PDF
- Saisie ou import d'une lettre de motivation type
- Toggle et seuil de score modifiable pour activer la génération automatique de LM
- Recherche des X dernières offres publiées via l'API France Travail (tri par date décroissante)
- Scoring de cohérence CV/offre via Ollama (LLM local)
- Historique persistant dans `historique_candidatures.csv`
- Téléchargement des lettres générées

## Prérequis

1. **Python 3.10+**
2. **Ollama** installé et démarré :
   ```bash
   ollama serve
   ollama pull llama3.2
   ```
3. **Clé API France Travail** (gratuite) : [francetravail.io](https://francetravail.io)

## Installation

```bash
cd D:\DEV\JOBAGENT
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Copiez `.env.example` vers `.env` et renseignez vos identifiants :

```bash
copy .env.example .env
```

```env
FRANCE_TRAVAIL_CLIENT_ID=votre_client_id
FRANCE_TRAVAIL_CLIENT_SECRET=votre_client_secret
```

## Lancement

```bash
streamlit run app.py
```

L'application s'ouvre dans le navigateur à l'adresse `http://localhost:8501`.

## Utilisation

1. Importez votre CV (PDF) dans la barre latérale
2. Collez ou importez votre lettre de motivation type
3. Activez ou désactivez la génération automatique (seuil : score >= 7)
4. Renseignez les mots-clés, le lieu et le nombre de **dernières offres** à traiter
5. Cliquez sur **Lancer le traitement**
6. Consultez l'historique et téléchargez les lettres générées

## Structure du projet

```
JOBAGENT/
├── app.py                          # Interface Streamlit
├── config.py                       # Configuration
├── requirements.txt
├── historique_candidatures.csv     # Historique (créé au runtime)
├── services/
│   ├── pdf_parser.py
│   ├── job_search.py
│   ├── scorer.py
│   ├── lm_generator.py
│   └── history_store.py
└── data/
    └── lettres/                    # Lettres générées
```

## Fichier CSV

Le fichier `historique_candidatures.csv` contient :

| Colonne | Description |
|---------|-------------|
| id | Identifiant unique |
| date_traitement | Date du traitement |
| date_publication | Date de publication de l'offre |
| titre | Titre du poste |
| entreprise | Nom de l'employeur |
| lieu | Localisation |
| url_offre | Lien vers l'offre |
| score_coherence | Note de 0 à 10 |
| lm_generee | oui / non |
| chemin_lm | Chemin vers la lettre générée |
| description_offre | Extrait de l'offre |
