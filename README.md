# Cybersecurity Identity Access

Edukacyjny projekt aplikacji webowej w Pythonie do zarządzania kontami, hasłami i uprawnieniami. Obecny etap obejmuje przygotowanie środowiska i zależności; szkielet aplikacji Django powstanie w kolejnym zadaniu.

## Środowisko

Projekt używa Pythona wskazanego w `.python-version`, Django 5.2 z obsługą Argon2 oraz `python-dotenv`. Grupa `dev` zawiera pytest, pytest-django i Ruff. Dokładne wersje zależności zapisano w `uv.lock`.

Po [zainstalowaniu uv](https://docs.astral.sh/uv/getting-started/installation/) środowisko można odtworzyć w folderze projektu:

```powershell
uv sync --locked
uv run --locked python --version
uv run --locked python -m django --version
uv run --locked pytest --version
uv run --locked ruff --version
```

`uv sync` domyślnie instaluje również grupę deweloperską. Do synchronizacji samych zależności aplikacji służy `uv sync --locked --no-dev`.

## Lokalne narzędzia na Windows

Na potrzeby przygotowania środowiska `uv` i Python zostały umieszczone w ignorowanym katalogu `.tools`, bez zmiany systemowego PATH ani rejestru. W obecnym folderze można używać ich w PowerShell:

```powershell
$env:UV_CACHE_DIR = Join-Path (Get-Location) '.uv-cache'
$env:UV_PYTHON_INSTALL_DIR = Join-Path (Get-Location) '.tools\python'
& '.tools\uv\bin\uv.exe' sync --locked
& '.tools\uv\bin\uv.exe' run --locked python --version
```

Katalog `.tools` nie jest częścią repozytorium. Aby odtworzyć ten lokalny układ na Windows z istniejącą instalacją Pythona i pip:

```powershell
py -m pip install --target .tools/uv uv==0.13.5
$env:UV_CACHE_DIR = Join-Path (Get-Location) '.uv-cache'
$env:UV_PYTHON_INSTALL_DIR = Join-Path (Get-Location) '.tools\python'
& '.tools\uv\bin\uv.exe' python install 3.13.17 --no-bin --no-registry
& '.tools\uv\bin\uv.exe' sync --locked
```

Środowisko `.venv`, lokalne narzędzia, cache, pliki `.env`, bazy SQLite i wyniki testów są wykluczone przez `.gitignore`. Pliki `pyproject.toml`, `.python-version`, `uv.lock` i przykładowa konfiguracja `.env.example` podlegają wersjonowaniu; `.env.example` powstanie wraz z konfiguracją aplikacji.

## Dokumentacja projektu

- [Specyfikacja](specs/001-identity-access/spec.md)
- [Plan techniczny](specs/001-identity-access/plan.md)
- [Zadania implementacyjne](specs/001-identity-access/tasks.md)

Konfiguracja pytest, Ruff oraz CI zostanie dodana w kolejnych zadaniach. Na tym etapie sprawdzono dostępność narzędzi, a nie działanie nieutworzonej jeszcze aplikacji.
