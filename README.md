# Python-Renamer
rename file recursively with a pattern list in a yaml file

This script allows you to rename file folders recursively with a list of word patterns to delete or change.

This script can be called by qbitorrent after a download and delete the torrent if you want (see the call parameters)

How it works :
a yaml file contains different lists:
- connection info to a qbitorrent server - filename to delete
- word pattern to be deleted
- word pattern to replace

For example :
the yaml file contains

deletefiles:
  - 'pub file xxx'
  - 'pub file yyy'

RmoveStrings:
  - "[wordxx]"
  - _word1-word2

call the script with the following parameters

rname / my_folder_word1-word2

if the my_folder_word1-word2 folder contains the following files
- / my_folder_word1-word2
- / my_folder_word1-word2 / file1_word1-word2.xxx
- / my_folder_word1-word2 / [wordxx] file2.xxx
- / my_folder_word1-word2 / pub file xxx
- / my_folder_word1-word2 / pub file yyy

after the script:
- / my_folder
- / my_folder / file1.xxx
- / my_folder / file2.xxx

Il est aussi possible de move vers le répertoire parent si un dossier ne contient qu'un seul fichier (voir les paramètres)

Par défaut le script log les informations des fichiers et dossiers renommés

Tout fonctionne sous linux, si vous le voulez avec windows changer     simplement le path du fichier de log :

- LOG_FILE = "/var/log/rname.log"
