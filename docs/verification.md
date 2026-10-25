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

Na etapie T001 nie uruchamiano testów zachowania aplikacji ani migracji. Sprawdzenie hashera dotyczyło dostępności biblioteki; docelowa konfiguracja bezpieczeństwa Django pozostawała częścią kolejnych prac. W chwili zakończenia T001 zadania T002–T035 były jeszcze nieukończone.

## T002 Szkielet Django i konfiguracja środowisk

Data: 2026-10-25

Wynik: zakończone pomyślnie

### Zakres wykonanych zmian

- Dodano `manage.py`, projekt `config` i moduły `accounts`, `security` oraz `documents` z własnymi konfiguracjami aplikacji i punktami rozszerzania adresów.
- Rozdzielono ustawienia wspólne, lokalne, testowe i produkcyjne.
- Włączono standardowe middleware Django, w tym CSRF i obsługę sesji przechowywanych w bazie.
- SQLite używa `IMMEDIATE` w krótkich transakcjach, bez `ATOMIC_REQUESTS`. Zapis czasu jest świadomy stref i używa UTC, a prezentacja `Europe/Warsaw`.
- Konfiguracja testowa nie ładuje `.env`, generuje własny sekret i używa bazy w pamięci. Hasher pozostaje rzeczywistym Argon2id.
- Konfiguracja produkcyjna nie ładuje `.env`, wymaga silnego sekretu i listy hostów bez `*`, wyłącza debugowanie oraz włącza przekierowanie HTTPS i bezpieczne ciasteczka. Polityka HSTS obejmuje na razie jedną domenę przez godzinę, bez preload; konfiguracja rzeczywistego serwera i proxy należy do przyszłego wdrożenia.
- Dodano `.env.example` bez sekretu oraz lokalny, ignorowany `.env` z losowym kluczem. Wartość klucza nie została wypisana ani umieszczona w dokumentacji.
- Dodano szablon bazowy, stronę startową i podstawowy arkusz CSS z obsługą małego ekranu, fokusu i przejścia do treści.
- README opisuje uruchomienie, konfiguracje i weryfikację. Lokalna instalacja narzędzi w `.tools` jest wyraźnie oznaczona jako opcjonalna.

### Przeprowadzone kontrole

| Kontrola | Wynik |
|---|---|
| `python manage.py check` | Brak problemów w konfiguracji lokalnej |
| `python manage.py check --settings=config.settings.test` | Brak problemów w konfiguracji testowej |
| `python manage.py check --settings=config.settings.production` z tymczasowymi zmiennymi środowiskowymi | Brak problemów; rzeczywisty lokalny sekret nie był używany |
| `pytest tests/test_settings.py --basetemp=.tools/t002-pytest -q` | 17 testów zakończonych sukcesem |
| `ruff check --isolated --select E4,E7,E9,F,I manage.py config apps tests` | Brak błędów |
| `ruff format --isolated --check manage.py config apps tests` | Wszystkie 22 pliki Pythona poprawnie sformatowane |
| Strona główna przez klienta Django | HTTP 200, język polski, odwołanie do istniejącego CSS, zero zapytań do bazy |
| Adres `/admin/` | HTTP 404; brak wbudowanego panelu Django Admin |
| Sesje i middleware | Skonfigurowany bazodanowy silnik sesji i aktywne middleware CSRF |
| SQLite w konfiguracji testowej | Rzeczywista transakcja rozpoczyna się przez `BEGIN IMMEDIATE` w bazie w pamięci |
| WSGI i ASGI | Oba punkty wejścia uruchamiają się z jawnie wybranymi ustawieniami testowymi |
| Brak lub nieprawidłowy sekret oraz brak hostów lub wildcard w produkcji | Start konfiguracji jest odrzucany, bez wypisywania wartości sekretu |
| Brak dostępu konfiguracji testowej i produkcyjnej do `.env` | Testy przechodzą także z funkcją ładowania `.env` zastąpioną funkcją zgłaszającą błąd |
| `.env` i `.env.example` w Git | Sekret ignorowany; plik przykładowy dopuszczony do wersjonowania |
| Lokalna baza `db.sqlite3` | Nie istnieje po kontrolach; nie uruchamiano migracji |

Testy konfiguracji działają w osobnych procesach, z jawnym kodowaniem UTF-8, również przy polskich znakach w ścieżce projektu. Kontrole Ruff używają `--isolated`, aby nie zależały od ustawień narzędzia spoza repozytorium. Wspólna konfiguracja narzędzi i CI powstanie w T004.

W ramach T002 nie implementowano własnego modelu użytkownika ani działania kont i sesji w bazie. Nie wykonano `migrate` ani `makemigrations`; pierwsze migracje przewidziano po ustawieniu `AUTH_USER_MODEL` w T003. W trakcie realizacji T002 nie wykonywano publicznego wdrożenia, commita ani pushowania zmian.

## T003 Własny użytkownik i pierwsza migracja

Data: 2026-10-25

Wynik: zakończone pomyślnie

Przed rozpoczęciem T003 zapisano ukończone T002 w commicie `cf010e6` (`feat: add Django skeleton and environment settings (T002)`). Lokalne ustawienia `.vscode` pozostawiono poza tym commitem.

### Zakres wykonanych zmian

- Dodano model `accounts.User` oparty na `AbstractUser` oraz ustawiono `AUTH_USER_MODEL = "accounts.User"`.
- Każdy użytkownik ma jedną z pięciu ról. Domyślną rolą jest Czytelnik, trybem poświadczeń `TEMPORARY`, a początkową wersją sesji `1`.
- Dodano datę logicznego usunięcia, datę ostatniej zmiany hasła i stany poświadczeń `INITIAL`, `TEMPORARY`, `PERMANENT`.
- Login jest obcinany wyłącznie z otaczających spacji. Unikalny klucz `login_key` jest wyliczany przez `casefold()`. Nie opieramy unikalności znaków spoza ASCII na funkcji SQLite `LOWER`. Hasła nie przechodzą normalizacji loginu.
- `ADMIN` jest kanonicznym zapisem zarezerwowanego loginu i jedynym kontem dopuszczającym rolę Administrator. Model i ograniczenia bazy odrzucają jego blokadę, degradację i logiczne usunięcie.
- Model oraz queryset chronią przed zmianą loginu i usunięciem `ADMIN`, również przy aktualizacji lub usuwaniu zbiorczym. Manager bazowy korzysta z tych samych zabezpieczeń. Operacje wymagające ochrony nie są wykonywane surowym SQL.
- Flagi `is_staff` i `is_superuser` są zabronione dla kont projektu, także ograniczeniem bazy. Manager odrzuca synchroniczne i asynchroniczne tworzenie superużytkownika Django.
- Utworzono jedną początkową migrację `accounts.0001_initial`. Wersjonowany jest schemat, bez lokalnej bazy i danych kont.

### Przeprowadzone kontrole

| Kontrola | Wynik |
|---|---|
| Pełny pytest z `--ds=config.settings.test` | 53 testy zakończone sukcesem: 36 przypadków modelu i 17 przypadków konfiguracji |
| Unikalność loginów | Odrzucone odpowiedniki różniące się wielkością liter, w tym `Straße`/`STRASSE` i `ŻANETA`/`żaneta` |
| Hasła a normalizacja loginu | Otaczające spacje w haśle są zachowane; zapis i weryfikacja działają przez Argon2id |
| Zmiana loginu | Odrzucona przez zapis modelu, odtworzoną instancję z istniejącym PK, queryset i aktualizację zbiorczą |
| Ochrona administratora | Odmowa rozdzielenia loginu i roli, blokady, degradacji, logicznego usunięcia i nadania uprawnień frameworka |
| Usunięcie administratora | Odmowa przez instancję, queryset, manager bazowy i usuwanie mieszanej listy kont |
| Ograniczenia bazy | Bezpośrednie aktualizacje ORM naruszające rolę, stan, aktywność, wersję sesji lub flagi uprzywilejowania odrzucane przez bazę |
| Logicznie usunięty użytkownik | Login pozostaje zarezerwowany; nie można pozostawić usuniętego konta aktywnym |
| `ruff check --isolated --select E4,E7,E9,F,I` | Brak błędów |
| `ruff format --isolated --check` | Wszystkie 26 plików Pythona poprawnie sformatowane |
| `manage.py makemigrations --check --dry-run --noinput` | Brak brakujących zmian migracji |
| `manage.py check` | Brak problemów |
| `manage.py migrate --noinput` na pustej lokalnej bazie | Migracje Django i `accounts.0001_initial` zastosowane poprawnie |
| `manage.py showmigrations accounts` | `0001_initial` oznaczona jako zastosowana |
| Kontrola schematu i danych lokalnych | Tabela `accounts_user` istnieje, `auth_user` nie istnieje, liczba kont wynosi 0 |

Testy modelu stosują migracje w izolowanej bazie w pamięci. Pełny zestaw uruchomiono poza ograniczeniami środowiska wykonawczego, ponieważ test wywołania asynchronicznego zatrzymywał się w ograniczonym środowisku Windows. Nie zmieniano konfiguracji bezpieczeństwa systemu ani nie korzystano z usług zewnętrznych.

Lokalny plik SQLite był przed zastosowaniem migracji pusty. Nie usuwano ani nie nadpisywano istniejących danych użytkowników. Inicjalizacja konta `ADMIN` i danych demonstracyjnych pozostaje zadaniem T017 oraz T029; T003 przygotowuje ich model i ograniczenia. Nie wykonywano pushowania ani publicznego wdrożenia.
