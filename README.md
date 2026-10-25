# Cybersecurity Identity Access

Edukacyjny projekt aplikacji webowej w Pythonie do zarządzania kontami, hasłami i uprawnieniami. Dostępny jest szkielet Django ze stroną startową oraz konfiguracjami środowisk. Logowanie, model użytkownika i pozostałe funkcje powstaną w kolejnych zadaniach.

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

## Uruchomienie lokalne

Jeżeli plik `.env` już istnieje, zachowaj jego zawartość. W bieżącym folderze został przygotowany podczas konfiguracji projektu.

Przy pierwszym uruchomieniu z nowej kopii projektu utwórz `.env` z losowym sekretem. Poniższe polecenie PowerShell nie nadpisze istniejącego pliku i nie wypisze sekretu w terminalu:

```powershell
@'
from pathlib import Path
from secrets import token_urlsafe

with Path(".env").open("x", encoding="utf-8") as config_file:
    config_file.write(
        "DJANGO_SECRET_KEY=" + token_urlsafe(64)
        + "\nDJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,[::1]\n"
    )
'@ | uv run --locked python -
```

Nazwy ustawień są opisane także w `.env.example`. Lokalnie `.env` jest odczytywany bez nadpisywania zmiennych już ustawionych w procesie.

Uruchom kontrolę konfiguracji i serwer:

```powershell
uv run --locked python manage.py check
uv run --locked python manage.py runserver
```

Strona startowa jest dostępna pod adresem [http://127.0.0.1:8000/](http://127.0.0.1:8000/). Serwer zatrzymasz przez `Ctrl+C`.

Przed ukończeniem T003 nie wykonuj `migrate` ani `makemigrations`. Najpierw powstanie własny model użytkownika. Serwer może na tym etapie informować o niezastosowanych migracjach frameworka; strona startowa działa bez tabel i nie wymaga ich zastosowania.

## Konfiguracje środowisk

| Moduł ustawień | Zastosowanie |
|---|---|
| `config.settings.local` | Domyślny dla `manage.py`, debugowanie, `.env`, lokalny plik SQLite |
| `config.settings.test` | Brak odczytu `.env`, własny losowy sekret, baza w pamięci, rzeczywisty Argon2id |
| `config.settings.production` | Sekret i jawne hosty ze zmiennych środowiskowych, wyłączone debugowanie, przekierowanie HTTPS i bezpieczne ciasteczka |

Przykładowa kontrola z izolowaną konfiguracją:

```powershell
uv run --locked python manage.py check --settings=config.settings.test
```

Punkty wejścia WSGI i ASGI domyślnie używają konfiguracji produkcyjnej, chyba że proces ma już ustawione `DJANGO_SETTINGS_MODULE`. Konfiguracja produkcyjna nie odczytuje `.env`. Rzeczywista konfiguracja serwera HTTPS i zaufanego proxy pozostaje częścią przyszłego wdrożenia.

## Weryfikacja szkieletu

```powershell
uv run --locked pytest tests/test_settings.py --basetemp=.tools/t002-pytest -q
uv run --locked ruff check --isolated --select E4,E7,E9,F,I manage.py config apps tests
uv run --locked ruff format --isolated --check manage.py config apps tests
```

Testy sprawdzają izolację ustawień, obsługę sekretów i hostów, wymuszenie HTTPS, uruchomienie WSGI/ASGI, renderowanie strony bez zapytań do bazy oraz tryb transakcji SQLite. Nie stosują migracji. Kontrole Ruff są na tym etapie niezależne od ustawień narzędzia spoza projektu.

## Lokalne narzędzia na Windows jako opcja

Jeśli masz już działające `uv` w PATH, korzystaj ze zwykłych komend powyżej i pomiń tę sekcję. Alternatywnie `uv` i Python mogą być umieszczone w ignorowanym katalogu `.tools`, bez zmiany systemowego PATH ani rejestru. W tym układzie można używać ich w PowerShell:

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

Środowisko `.venv`, lokalne narzędzia, cache, pliki `.env`, bazy SQLite i wyniki testów są wykluczone przez `.gitignore`. Pliki `pyproject.toml`, `.python-version`, `uv.lock` i przykładowa konfiguracja `.env.example` podlegają wersjonowaniu.

## Dokumentacja projektu

- [Specyfikacja](specs/001-identity-access/spec.md)
- [Plan techniczny](specs/001-identity-access/plan.md)
- [Zadania implementacyjne](specs/001-identity-access/tasks.md)

Wspólna konfiguracja pytest, Ruff oraz CI powstanie w T004. [Wyniki weryfikacji](docs/verification.md) opisują kontrole dotychczas wykonanych zadań.
