**Publiez l’article le plus récent d’un flux RSS sur votre timeline Bluesky**

## Pré-requis 
- Python >= 3.x
- pip3
- feedparser
- atproto
- yaml

## Configuration
- Renommez le fichier de Configuration en `config.yaml` en retirant ".sample"
- Editez selon les paramètres de votre compte Bluesky et Flux RSS

## Installation
- Installez Python3
- Créez et activez un environnement Python (venv)
  
  `python3 -m venv venv`

   `source ./venv/bin/activate`

- Installez les dépendences 

  `pip install feedparser atproro yaml`
  
- Clonez le projet
- Lancez le script. Un job cron est possible pour automatiser les publications

   `./rss2bluesky/rss2bluesky.py`
   
   Sortie du script : L’article publié est confirmé
   
Note : Un fichier cache est créé afin d’eviter les doublons