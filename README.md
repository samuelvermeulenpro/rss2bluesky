**Publiez les articles les plus récents d’un ou plusieurs flux RSS sur votre timeline Bluesky**

## Pré-requis 
- Python >= 3.x
- pip3
- feedparser
- atproto
- yaml

## Configuration
- Renommez le fichier de Configuration en `config.yaml` en retirant ".sample"
- Editez selon les paramètres de votre compte Bluesky et de vos flux RSS
- Plusieurs flux peuvent être listés sous `feeds:`, chacun avec un hashtag et un nombre d’items optionnels :

  ```yaml
  feeds:
    - "https://url-flux-rss.com/"          # utilise post.hashtag, 1 item
    - url: "https://autre-flux-rss.com/feed"
      hashtag: "#AutreFlux"
      count: 3                             # publie les 3 items les plus récents
  ```

  `count` indique le nombre d’items les plus récents à publier pour ce flux.
  S’il est omis, seul l’article le plus récent est publié. Les items déjà
  publiés ne sont pas republiés, et les nouveaux sont postés du plus ancien
  au plus récent.

  L’ancien format `rss_url: "..."` (un seul flux) reste supporté.

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