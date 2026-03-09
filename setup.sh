#!/usr/bin/env bash
set -euo pipefail

# --------- Paramètres à adapter ---------
ENV_NAME="mosna-GUI"
PY_VER="3.10"

# Chemin absolu vers ton script GUI
APP_DIR="${HOME}/Desktop/MOSNA_GUI"
MOSNA_SCRIPT="${APP_DIR}/GUI_MOSNA.py"

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
conda install -y -c conda-forge "scipy<1.14" pyside6 pyyaml ipykernel ipywidgets markdown
pip install markdown || true

echo "[3/4] Installation de mosna en editable"
# adapte si besoin
cd mosna-package
pip install -e .
cd ..
conda install -y -c conda-forge "lifelines<0.28"

if [ "${GITHUB_ACTIONS:-false}" != "true"]; then
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

    cat > "${DESKTOP_FILE}" <<EOF
[Desktop Entry]
Type=Application
Name=${APP_NAME}
Comment=Lance l'interface MOSNA dans l'environnement conda
Exec=/bin/bash -lc "${LAUNCHER_SH}"
Icon=${APP_DIR}/DOC/logo.png
Terminal=false
Categories=Science;Utility;
StartupNotify=true
EOF

    chmod +x "${DESKTOP_FILE}"

    echo "Raccourci créé : ${DESKTOP_FILE}"
    echo "Launcher créé  : ${LAUNCHER_SH}"
    echo
    echo -e "Sur GNOME/Ubuntu, il faudra peut-être clic droit sur l'icône -> 'Allow Launching'."
else
    echo "[4/4] Environnement GitHub Actions détecté, création du launcher ignorée"
fi