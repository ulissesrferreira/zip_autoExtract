@echo off
title ZipAutoExtract - Instalador
color 0A
echo.
echo  ╔══════════════════════════════════════════════════════════════╗
echo  ║           ZipAutoExtract — Instalador v1.0                 ║
echo  ║           Extrator Automatico de Arquivos ZIP              ║
echo  ╚══════════════════════════════════════════════════════════════╝
echo.

:: Check Python
echo [1/3] Verificando Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python nao encontrado! Instale o Python e tente novamente.
    echo Acesse: https://python.org
    pause
    exit /b 1
)
echo ✅ Python encontrado!
echo.

:: Install dependencies
echo [2/3] Instalando dependencias necessarias...
pip install -r "%~dp0requirements.txt" --quiet
if errorlevel 1 (
    echo ❌ Erro ao instalar dependencias! Verifique sua conexao ou o pip.
    pause
    exit /b 1
)
echo ✅ Dependencias instaladas com sucesso!
echo.

:: Run app
echo [3/3] Iniciando o Auto-Extrator em segundo plano...
start "" pythonw "%~dp0monitor.pyw"

echo.
echo ══════════════════════════════════════════════════════════════
echo   Instalacao concluida!
echo   - O icone aparecera na area de notificacao (perto do relogio)
echo   - Para iniciar junto com o Windows, clique direito no icone
echo     e ative "Executar na Inicializacao"
echo ══════════════════════════════════════════════════════════════
echo.
timeout /t 5
