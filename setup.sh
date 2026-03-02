#!/usr/bin/env bash
set -euo pipefail

# --------- Paramètres à adapter ---------
ENV_NAME="test-GUI"
PY_VER="3.10"

# Chemin absolu vers ton script GUI
MOSNA_SCRIPT="/home/owen.griere/Desktop/Mosna_GUI/GUI_MOSNA.py"
APP_DIR="/home/owen.griere/Desktop/Mosna_GUI"

# Où créer l'icône + launcher (Desktop)
DESKTOP_DIR="${HOME}/Desktop"

# Nom affiché
APP_NAME="Mosna GUI"
LAUNCHER_SH="${APP_DIR}/MosnaGUI.sh"
DESKTOP_FILE="${DESKTOP_DIR}/MosnaGUI.desktop"
# ---------------------------------------

# Init conda pour que conda activate marche dans un script
CONDA_BASE="$(conda info --base)"
source "${CONDA_BASE}/etc/profile.d/conda.sh"

echo "[1/4] Création de l'environnement conda ${ENV_NAME}"
conda create -y -n "${ENV_NAME}" -c conda-forge python="${PY_VER}" scanpy

conda activate "${ENV_NAME}"

echo "[2/4] Installation dépendances"
conda install -y -c conda-forge "scipy<1.14" "lifelines<0.28" pyside6 pyyaml ipykernel ipywidgets markdown
pip install markdown || true

echo "[3/4] Installation de mosna en editable"
# adapte si besoin
cd mosna-package
pip install -e .
cd ..

echo "[4/4] Création du launcher + icône de bureau"

# 4a) Script launcher (active conda + lance la GUI)
cat > "${LAUNCHER_SH}" <<EOF
#!/usr/bin/env bash
set -e
source "${CONDA_BASE}/etc/profile.d/conda.sh"
conda activate "${ENV_NAME}"
python "${MOSNA_SCRIPT}"
EOF

chmod +x "${LAUNCHER_SH}"

# 4b) Fichier .desktop (icône cliquable)
cat > "${DESKTOP_FILE}" <<EOF
[Desktop Entry]
Type=Application
Name=${APP_NAME}
Comment=Lance l'interface MOSNA dans l'environnement conda
Exec=/bin/bash -lc "${LAUNCHER_SH}"
Icon=${APP_DIR}/package/DOC/logo_Mosna_GUI.png
Terminal=false
Categories=Science;Utility;
StartupNotify=true
EOF

chmod +x "${DESKTOP_FILE}"

echo "Raccourci créé : ${DESKTOP_FILE}"
echo "Launcher créé  : ${LAUNCHER_SH}"
echo
echo "Sur GNOME/Ubuntu, il faudra peut-être clic droit sur l'icône -> 'Allow Launching'."