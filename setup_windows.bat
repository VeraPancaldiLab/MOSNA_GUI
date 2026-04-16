@echo off
setlocal EnableExtensions

title MOSNA GUI - Installation Windows

rem ---------------------------------------------------------------------------
rem Configuration fixe du projet
rem ---------------------------------------------------------------------------
set "ENV_NAME=mosna-GUI"
set "PYTHON_VERSION=3.10"

set "PROJECT_DIR=%~dp0"
if "%PROJECT_DIR:~-1%"=="\" set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"

set "MINICONDA_DIR=%USERPROFILE%\miniconda3"
set "MINICONDA_INSTALLER=%TEMP%\Miniconda3-latest-Windows-x86_64.exe"
set "MINICONDA_URL=https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe"

set "CONDA_BAT="
set "GUI_SCRIPT=%PROJECT_DIR%\GUI_MOSNA.py"
set "ICON_FILE=%PROJECT_DIR%\assets\logo.ico"
set "PACKAGE_DIR=%PROJECT_DIR%\mosna-package"

set "DESKTOP_SHORTCUT=%USERPROFILE%\Desktop\MOSNA GUI.lnk"
set "EXE_DIR=%PROJECT_DIR%\dist\MosnaGUI"
set "EXE_FILE=%EXE_DIR%\MosnaGUI.exe"
set "EXE_FILE_ONEFILE=%PROJECT_DIR%\dist\MosnaGUI.exe"

echo.
echo ============================================================
echo                MOSNA GUI - Installation Windows
echo ============================================================
echo.
echo Dossier du projet :
echo %PROJECT_DIR%
echo.

rem ---------------------------------------------------------------------------
rem Verification de l'arborescence attendue
rem ---------------------------------------------------------------------------
if not exist "%GUI_SCRIPT%" (
    echo [ERREUR] Le fichier GUI_MOSNA.py est introuvable.
    echo Le script .bat doit etre lance depuis la racine du projet.
    goto :fail
)

if not exist "%PACKAGE_DIR%\setup.py" (
    echo [ERREUR] Le package local attendu est introuvable :
    echo %PACKAGE_DIR%\setup.py
    goto :fail
)

cd /d "%PROJECT_DIR%"

rem ---------------------------------------------------------------------------
rem Recherche de Conda
rem ---------------------------------------------------------------------------
call :find_conda
if errorlevel 1 (
    echo [INFO] Conda n'a pas ete trouve. Installation automatique de Miniconda.
    call :install_miniconda
    if errorlevel 1 goto :fail

    call :find_conda
    if errorlevel 1 (
        echo [ERREUR] Conda reste introuvable apres l'installation de Miniconda.
        goto :fail
    )
)

echo [INFO] Conda detecte ici :
echo %CONDA_BAT%
echo.

rem ---------------------------------------------------------------------------
rem Creation de l'environnement si besoin
rem ---------------------------------------------------------------------------
echo [ETAPE 1/7] Verification de l'environnement Conda "%ENV_NAME%"...

call "%CONDA_BAT%" env list | findstr /R /C:"\<%ENV_NAME%\>" >nul 2>nul
if errorlevel 1 (
    echo [INFO] L'environnement n'existe pas encore. Creation en cours...
    call "%CONDA_BAT%" create -n "%ENV_NAME%" python=%PYTHON_VERSION% -y
    if errorlevel 1 (
        echo [ERREUR] Echec lors de la creation de l'environnement Conda.
        goto :fail
    )
) else (
    echo [INFO] L'environnement "%ENV_NAME%" existe deja.
)

echo.
echo [ETAPE 2/7] Installation des dependances Conda...
call "%CONDA_BAT%" install -n "%ENV_NAME%" -y -c conda-forge ^
    pyside6 pandas scipy networkx scikit-learn matplotlib seaborn pillow openpyxl xlsxwriter
if errorlevel 1 (
    echo [ERREUR] Echec lors de l'installation des dependances Conda.
    goto :fail
)

echo.
echo [ETAPE 3/7] Installation des outils Python...
call "%CONDA_BAT%" run -n "%ENV_NAME%" python -m pip install --upgrade pip setuptools wheel pyinstaller
if errorlevel 1 (
    echo [ERREUR] Echec lors de l'installation de pip, setuptools, wheel ou pyinstaller.
    goto :fail
)

echo.
echo [ETAPE 4/7] Installation du package local...
call "%CONDA_BAT%" run -n "%ENV_NAME%" python -m pip install -e "%PACKAGE_DIR%"
if errorlevel 1 (
    echo [ERREUR] Echec lors de l'installation du package local.
    goto :fail
)

echo.
echo [ETAPE 5/7] Nettoyage des anciens fichiers de build...
if exist "%PROJECT_DIR%\build" rmdir /s /q "%PROJECT_DIR%\build"
if exist "%PROJECT_DIR%\dist" rmdir /s /q "%PROJECT_DIR%\dist"
if exist "%PROJECT_DIR%\MosnaGUI.spec" del /f /q "%PROJECT_DIR%\MosnaGUI.spec"

echo.
echo [ETAPE 6/7] Construction de l'executable avec PyInstaller...
call :build_pyinstaller
if errorlevel 1 goto :fail

echo.
echo [ETAPE 7/7] Creation du raccourci bureau...
call :resolve_final_exe
if errorlevel 1 (
    echo [ERREUR] L'executable n'a pas ete trouve apres la compilation.
    goto :fail
)

call :create_desktop_shortcut
if errorlevel 1 (
    echo [ERREUR] Echec lors de la creation du raccourci bureau.
    goto :fail
)

echo.
echo ============================================================
echo Installation terminee avec succes.
echo ============================================================
echo.
echo Executable :
echo %FINAL_EXE%
echo.
echo Raccourci bureau :
echo %DESKTOP_SHORTCUT%
echo.
goto :eof


rem ===========================================================================
rem Sous-routines
rem ===========================================================================

:find_conda
set "CONDA_BAT="

if exist "%MINICONDA_DIR%\condabin\conda.bat" (
    set "CONDA_BAT=%MINICONDA_DIR%\condabin\conda.bat"
    exit /b 0
)

if exist "%USERPROFILE%\anaconda3\condabin\conda.bat" (
    set "CONDA_BAT=%USERPROFILE%\anaconda3\condabin\conda.bat"
    exit /b 0
)

for /f "delims=" %%I in ('where conda.bat 2^>nul') do (
    set "CONDA_BAT=%%I"
    exit /b 0
)

exit /b 1


:install_miniconda
echo.
echo ============================================================
echo                 Installation de Miniconda
echo ============================================================
echo.

echo [INFO] Telechargement de l'installeur...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "try { Invoke-WebRequest -Uri '%MINICONDA_URL%' -OutFile '%MINICONDA_INSTALLER%' } catch { exit 1 }"
if errorlevel 1 (
    echo [ERREUR] Echec du telechargement de Miniconda.
    exit /b 1
)

if not exist "%MINICONDA_INSTALLER%" (
    echo [ERREUR] Le fichier d'installation de Miniconda est introuvable apres telechargement.
    exit /b 1
)

echo [INFO] Installation silencieuse de Miniconda dans :
echo %MINICONDA_DIR%
echo.

start /wait "" "%MINICONDA_INSTALLER%" /InstallationType=JustMe /RegisterPython=0 /S /D=%MINICONDA_DIR%
if errorlevel 1 (
    echo [ERREUR] L'installation de Miniconda a echoue.
    exit /b 1
)

if not exist "%MINICONDA_DIR%\condabin\conda.bat" (
    echo [ERREUR] Miniconda semble installe, mais conda.bat est introuvable.
    exit /b 1
)

echo [INFO] Miniconda a ete installe correctement.
exit /b 0


:build_pyinstaller
if exist "%ICON_FILE%" (
    call "%CONDA_BAT%" run -n "%ENV_NAME%" pyinstaller ^
        --noconfirm ^
        --windowed ^
        --name MosnaGUI ^
        --icon "%ICON_FILE%" ^
        --add-data "%PROJECT_DIR%\docs;docs" ^
        --add-data "%PROJECT_DIR%\stylesheet.css;." ^
        --add-data "%PROJECT_DIR%\config.json;." ^
        --add-data "%PROJECT_DIR%\package;package" ^
        "%GUI_SCRIPT%"
) else (
    call "%CONDA_BAT%" run -n "%ENV_NAME%" pyinstaller ^
        --noconfirm ^
        --windowed ^
        --name MosnaGUI ^
        --add-data "%PROJECT_DIR%\docs;docs" ^
        --add-data "%PROJECT_DIR%\stylesheet.css;." ^
        --add-data "%PROJECT_DIR%\config.json;." ^
        --add-data "%PROJECT_DIR%\package;package" ^
        "%GUI_SCRIPT%"
)

if errorlevel 1 (
    echo [ERREUR] PyInstaller a echoue.
    exit /b 1
)

exit /b 0


:resolve_final_exe
set "FINAL_EXE="

if exist "%EXE_FILE%" set "FINAL_EXE=%EXE_FILE%"
if not defined FINAL_EXE if exist "%EXE_FILE_ONEFILE%" set "FINAL_EXE=%EXE_FILE_ONEFILE%"

if defined FINAL_EXE (
    exit /b 0
)

exit /b 1


:create_desktop_shortcut
if not defined FINAL_EXE (
    echo [ERREUR] FINAL_EXE n'est pas defini.
    exit /b 1
)

set "SHORTCUT_ICON=%FINAL_EXE%"
if exist "%ICON_FILE%" set "SHORTCUT_ICON=%ICON_FILE%"

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$WshShell = New-Object -ComObject WScript.Shell; ^
    $Shortcut = $WshShell.CreateShortcut('%DESKTOP_SHORTCUT%'); ^
    $Shortcut.TargetPath = '%FINAL_EXE%'; ^
    $Shortcut.WorkingDirectory = [System.IO.Path]::GetDirectoryName('%FINAL_EXE%'); ^
    $Shortcut.IconLocation = '%SHORTCUT_ICON%'; ^
    $Shortcut.Description = 'Launch MOSNA GUI'; ^
    $Shortcut.Save()"

if errorlevel 1 (
    exit /b 1
)

exit /b 0


:fail
echo.
echo ============================================================
echo Le processus s'est arrete a cause d'une erreur.
echo ============================================================
echo.
exit /b 1