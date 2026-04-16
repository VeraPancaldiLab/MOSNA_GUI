@echo off
setlocal EnableExtensions

title MOSNA GUI - Windows installer and builder

rem ============================================================================
rem Configuration du projet
rem ============================================================================

set "ENV_NAME=mosna-GUI"
set "PYTHON_VERSION=3.10"

set "PROJECT_DIR=%~dp0"
if "%PROJECT_DIR:~-1%"=="\" set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"

set "MINICONDA_DIR=%USERPROFILE%\miniconda3"
set "MINICONDA_INSTALLER=%TEMP%\Miniconda3-latest-Windows-x86_64.exe"
set "MINICONDA_URL=https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe"

set "CONDA_BAT="
set "PACKAGE_DIR=%PROJECT_DIR%\mosna-package"
set "GUI_SCRIPT=%PROJECT_DIR%\GUI_MOSNA.py"
set "ICON_FILE=%PROJECT_DIR%\assets\logo.ico"

set "DESKTOP_SHORTCUT=%USERPROFILE%\Desktop\MOSNA GUI.lnk"
set "EXE_PATH_ONE=%PROJECT_DIR%\dist\MosnaGUI\MosnaGUI.exe"
set "EXE_PATH_TWO=%PROJECT_DIR%\dist\MosnaGUI.exe"
set "FINAL_EXE="

echo.
echo ============================================================
echo           MOSNA GUI - Windows installation
echo ============================================================
echo.
echo Project directory:
echo %PROJECT_DIR%
echo.

rem ============================================================================
rem Verification de l'arborescence attendue
rem ============================================================================

if not exist "%GUI_SCRIPT%" (
    echo [ERROR] GUI_MOSNA.py was not found in the project directory.
    echo Please run this script from the root folder of the project.
    goto :fail
)

if not exist "%PACKAGE_DIR%\setup.py" (
    echo [ERROR] The expected local package was not found:
    echo %PACKAGE_DIR%\setup.py
    goto :fail
)

cd /d "%PROJECT_DIR%"

rem ============================================================================
rem Detection de Conda
rem ============================================================================

call :find_conda
if errorlevel 1 (
    echo [INFO] Conda was not found. Miniconda will be installed automatically.
    call :install_miniconda
    if errorlevel 1 goto :fail

    call :find_conda
    if errorlevel 1 (
        echo [ERROR] Conda is still unavailable after Miniconda installation.
        goto :fail
    )
)

echo [INFO] Conda found here:
echo %CONDA_BAT%
echo.

if exist "%ICON_FILE%" (
    echo [INFO] Icon file found:
    echo %ICON_FILE%
) else (
    echo [WARNING] No icon file found at:
    echo %ICON_FILE%
    echo The executable will be built without a custom icon.
)
echo.

rem ============================================================================
rem Installation
rem ============================================================================

echo [STEP 1/7] Checking the Conda environment "%ENV_NAME%"...
call :ensure_env
if errorlevel 1 goto :fail

echo.
echo [STEP 2/7] Installing Conda dependencies...
call "%CONDA_BAT%" install -n "%ENV_NAME%" -y -c conda-forge ^
    pyside6 pandas scipy networkx scikit-learn matplotlib seaborn pillow openpyxl xlsxwriter
if errorlevel 1 (
    echo [ERROR] Failed to install Conda dependencies.
    goto :fail
)

echo.
echo [STEP 3/7] Installing Python build tools...
call "%CONDA_BAT%" run -n "%ENV_NAME%" python -m pip install --upgrade pip setuptools wheel pyinstaller
if errorlevel 1 (
    echo [ERROR] Failed to install pip, setuptools, wheel or pyinstaller.
    goto :fail
)

echo.
echo [STEP 4/7] Installing the local package...
call "%CONDA_BAT%" run -n "%ENV_NAME%" python -m pip install -e "%PACKAGE_DIR%"
if errorlevel 1 (
    echo [ERROR] Failed to install the local package in editable mode.
    goto :fail
)

echo.
echo [STEP 5/7] Cleaning previous build folders if they exist...
if exist "%PROJECT_DIR%\build" rmdir /s /q "%PROJECT_DIR%\build"
if exist "%PROJECT_DIR%\dist" rmdir /s /q "%PROJECT_DIR%\dist"
if exist "%PROJECT_DIR%\MosnaGUI.spec" del /f /q "%PROJECT_DIR%\MosnaGUI.spec"

echo.
echo [STEP 6/7] Building MosnaGUI.exe with PyInstaller...
call :build_pyinstaller
if errorlevel 1 goto :fail

echo.
echo [STEP 7/7] Creating the desktop shortcut...
call :resolve_final_exe
if errorlevel 1 (
    echo [ERROR] The executable was not found after the build.
    goto :fail
)

call :create_desktop_shortcut
if errorlevel 1 (
    echo [ERROR] Failed to create the desktop shortcut.
    goto :fail
)

echo.
echo ============================================================
echo Installation and build completed successfully.
echo ============================================================
echo.
echo Executable created here:
echo %FINAL_EXE%
echo.
echo Desktop shortcut created here:
echo %DESKTOP_SHORTCUT%
echo.
echo You can now launch MOSNA GUI from the shortcut on the desktop.
echo.
goto :eof


rem ============================================================================
rem Sous-routines
rem ============================================================================

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
echo Miniconda installation
echo ============================================================
echo.

echo [INFO] Downloading Miniconda installer...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "try { Invoke-WebRequest -Uri '%MINICONDA_URL%' -OutFile '%MINICONDA_INSTALLER%' } catch { exit 1 }"
if errorlevel 1 (
    echo [ERROR] Failed to download Miniconda.
    exit /b 1
)

if not exist "%MINICONDA_INSTALLER%" (
    echo [ERROR] The Miniconda installer was not downloaded.
    exit /b 1
)

echo [INFO] Installing Miniconda silently into:
echo %MINICONDA_DIR%
echo.

start /wait "" "%MINICONDA_INSTALLER%" /InstallationType=JustMe /RegisterPython=0 /S /D=%MINICONDA_DIR%
if errorlevel 1 (
    echo [ERROR] Miniconda installation failed.
    exit /b 1
)

if not exist "%MINICONDA_DIR%\condabin\conda.bat" (
    echo [ERROR] Miniconda seems installed, but conda.bat was not found.
    exit /b 1
)

echo [INFO] Miniconda installed successfully.
exit /b 0


:ensure_env
call "%CONDA_BAT%" env list | findstr /R /C:"\<%ENV_NAME%\>" >nul 2>nul
if not errorlevel 1 (
    echo [INFO] The environment "%ENV_NAME%" already exists.
    exit /b 0
)

echo [INFO] Environment "%ENV_NAME%" not found. Creating it now...
call "%CONDA_BAT%" create -n "%ENV_NAME%" python=%PYTHON_VERSION% -y
if errorlevel 1 (
    echo [ERROR] Failed to create the Conda environment.
    exit /b 1
)

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
    echo [ERROR] PyInstaller failed to build the executable.
    exit /b 1
)

exit /b 0


:resolve_final_exe
set "FINAL_EXE="

if exist "%EXE_PATH_ONE%" (
    set "FINAL_EXE=%EXE_PATH_ONE%"
    exit /b 0
)

if exist "%EXE_PATH_TWO%" (
    set "FINAL_EXE=%EXE_PATH_TWO%"
    exit /b 0
)

exit /b 1


:create_desktop_shortcut
if not defined FINAL_EXE (
    echo [ERROR] FINAL_EXE is not defined.
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
echo The process stopped because of an error.
echo ============================================================
echo.
exit /b 1