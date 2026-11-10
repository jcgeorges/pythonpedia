
import json

# Lecture de la base de données
with open("data/topics.json", "r", encoding="utf-8") as fichier:
    topics = json.load(fichier)

# Affichage des topics disponibles
print("Topics disponibles :")

for topic in topics:
    print("-", topic)

# Affichage des références du topic fonctions
print("\nRéférences du topic fonctions :")
print(topics["fonctions"])
