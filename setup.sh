#!/bin/bash

set -e  # Quitter en cas d'erreur

# === Étape 0 : Vérification de Conda ===
if ! command -v conda &> /dev/null; then
    echo "❌ Conda n'est pas installé. Installe Miniconda ou Anaconda avant de continuer."
    exit 1
fi

# === Étape 1 : Vérifier que le fichier mosna.yml existe ===
if [ ! -f mosna.yml ]; then
    echo "❌ Fichier mosna.yml introuvable dans le répertoire courant."
    exit 1
fi

# === Étape 2 : Création de l'environnement Conda ===
echo "🛠️  Création de l'environnement conda 'mosna'..."
conda env create -f mosna.yml

# === Étape 3 : Installation des bibliothèques système ===
echo "🔧 Installation des dépendances système (nécessite sudo)..."
sudo apt update && sudo apt install -y \
    build-essential \
    libglib2.0-0 \
    libgl1 \
    libgomp1 \
    libhdf5-dev \
    libzstd1 \
    libxml2 \
    libffi-dev \
    libxcb-xinerama0 \
    jq

echo "✅ Installation terminée !"
echo "➡️ Active l'environnement avec : conda activate mosna"
