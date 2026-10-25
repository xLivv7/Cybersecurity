# Wyniki weryfikacji projektu

## T001 Środowisko i zależności

Data: 2026-10-22  
Wynik: zakończone pomyślnie

### Zakres wykonanych zmian

- `pyproject.toml`: projekt aplikacji bez instalowania go jako pakietu, Python z serii 3.13, Django 5.2 z dodatkiem Argon2, `python-dotenv` i grupa `dev`.
- `.python-version`: Python 3.13.17.
- `uv.lock`: dokładne wersje i hashe dystrybucji zależności.
- `.gitignore`: lokalne środowiska, narzędzia, cache, sekrety, bazy i artefakty testów.
- `README.md`: odtworzenie środowiska i korzystanie z lokalnego uv na Windows.

`uv` 0.13.5 i zarządzany Python zostały zainstalowane lokalnie w `.tools`, a zależności w `.venv`. Nie zmieniano systemowego PATH ani rejestru. Katalogi narzędzi i cache nie są przeznaczone do wersjonowania.

### Zainstalowane główne narzędzia

| Narzędzie | Wersja |
|---|---|
| Python | 3.13.17 |
| uv | 0.13.5 |
| Django | 5.2.18 |
| argon2-cffi | 25.1.0 |
| python-dotenv | 1.2.4 |
| pytest | 9.1.1 |
| pytest-django | 4.14.0 |
| Ruff | 0.17.1 |

### Przeprowadzone kontrole

| Kontrola | Wynik |
|---|---|
| `uv lock --check --offline` | Plik blokady zgodny z deklaracją zależności |
| `uv pip check` na `.venv` | Wszystkie 17 zainstalowanych pakietów jest zgodnych |
| Uruchomienie Pythona, Django, pytest i Ruff | Polecenia wersji kończą się sukcesem |
| Import metadanych pytest-django i python-dotenv | Pakiety dostępne we właściwych wersjach |
| Hasher Django Argon2 | Utworzenie hasha Argon2id i weryfikacja przykładowego tekstu zakończone sukcesem |
| Drugie środowisko z `uv sync --locked --offline --link-mode copy` | Odtworzone bez sieci z lokalnego cache |
| Porównanie obu środowisk | Wersja Pythona i pełna lista wersji pakietów identyczne |
| Hash pliku `uv.lock` przed i po odtworzeniu | Niezmieniony |
| `git check-ignore --no-index` | 17 przykładowych lokalnych ścieżek ignorowanych; 7 ścieżek projektu dopuszczonych do wersjonowania |

Reguły ignorowania sprawdzono przy użyciu tymczasowego repozytorium technicznego, bez inicjalizacji repozytorium Git w katalogu głównym projektu. Próby objęły m.in. `.venv`, `.tools`, cache, `.env`, `.env.local`, SQLite i pliki dzienników, wyniki testów oraz plik klucza. Potwierdzono, że `pyproject.toml`, `.python-version`, `uv.lock`, `.gitignore`, `.env.example`, README i dokument zadań nie są wykluczone.

Drugie środowisko i tymczasowe repozytorium weryfikacyjne usunięto po kontroli. Oryginalne `.venv` pozostało gotowe do dalszej pracy. Odtworzenie offline dotyczy pobranych pakietów i platformy Windows; pierwszy start na innym komputerze lub platformie wymaga dostępu do źródeł zależności.

Nie uruchamiano testów zachowania aplikacji ani migracji: powstaną w następnych zadaniach. Sprawdzenie hashera dotyczy dostępności biblioteki; docelowa konfiguracja bezpieczeństwa Django będzie częścią kolejnych prac. T002–T035 pozostają nieukończone.
