import csv
import random

# Nombre total de cellules à générer
n_cells = 100
id_index = 600
# Définition des phénotypes avec leurs probabilités
phenotypes = ["cancer", "immune", "fibroblast"]
probabilities = [0.6, 0.25, 0.15]

# Ouverture du fichier CSV en écriture
with open("cells_dataset.csv", "w", newline="") as f:
    writer = csv.writer(f)

    # Écriture de l'en-tête du fichier
    writer.writerow(["id", "X", "Y", "phenotype"])

    # Génération des cellules
    for i in range(1, n_cells + 1):
        # Coordonnées spatiales aléatoires
        x = random.uniform(0, 100)
        y = random.uniform(0, 100)

        # Choix du phénotype selon les probabilités définies
        phenotype = random.choices(phenotypes, probabilities)[0]

        # Écriture de la ligne dans le CSV
        writer.writerow([f"cell_{i+id_index}", round(x, 2), round(y, 2), phenotype])

print("Fichier CSV généré avec 100 cellules.")
