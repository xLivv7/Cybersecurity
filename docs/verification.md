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

## T004 Podstawa testów i automatycznych kontroli

Data: 2026-10-25

Wynik: zakończone pomyślnie lokalnie; workflow gotowy do pierwszego wykonania na GitHubie

### Zakres wykonanych zmian

- Dodano konfigurację pytest w `pyproject.toml`: katalog `tests`, wzorzec plików, ścisłą kontrolę ustawień i markerów, ścieżkę importów oraz domyślną konfigurację Django `config.settings.test`. Opcja `--ds` w `addopts` ma pierwszeństwo przed odziedziczoną zmienną środowiskową wskazującą inne środowisko.
- Dodano konfigurację Ruff dla Pythona 3.13: reguły błędów składni, niezdefiniowanych lub nieużywanych nazw, importów i nieużywanych wyłączeń `noqa`, formatowanie oraz wykluczenia lokalnych narzędzi i cache.
- `.gitattributes` ustala LF dla plików źródłowych i konfiguracji, aby formatowanie nie zależało od domyślnego `core.autocrlf` na Windows. Normalizacja istniejącej migracji nie zmienia jej operacji ani schematu bazy.
- `tests/conftest.py` zawiera `user_factory`, `admin_factory`, `admin` oraz `clock`. Konta są tworzone przez właściwy manager w izolowanej bazie; fabryki nie nadają domyślnie używalnego hasła ani uprawnień frameworka.
- Kontrolowany zegar zastępuje `django.utils.timezone.now()` na czas jednego testu. Fabryki pobierają z niego czas utworzenia konta. Istniejący test logicznego usunięcia przesuwa czas o dobę bez oczekiwania i sprawdza zapisane daty oraz dalszą rezerwację loginu.
- Workflow `.github/workflows/ci.yml` obejmuje push, pull request i ręczne wywołanie. Macierz obejmuje `ubuntu-latest` i `windows-latest`, a każde zadanie ma limit 10 minut.
- Workflow korzysta z Python 3.13.17 według `.python-version`, uv 0.13.5 i `uv.lock`. Akcje checkout oraz setup-uv są przypięte do konkretnych SHA, uprawnienia ograniczono do odczytu repozytorium, a checkout nie utrwala poświadczeń.
- Lokalne polecenia w README odpowiadają kontrolom workflow. Działanie aplikacji i zależności nie zostały zmienione.

### Przeprowadzone kontrole

| Kontrola | Wynik |
|---|---|
| `uv sync --locked --dev` z dodatkowym lokalnym `--offline` | Zależności zgodne z istniejącym plikiem blokady; 17 zainstalowanych pakietów |
| `uv run --locked ruff check .` | Brak błędów z konfiguracją projektu |
| `uv run --locked ruff format --check .` | Formatowanie zgodne z konfiguracją projektu |
| `uv run --locked python manage.py check --settings=config.settings.test` | Brak problemów |
| `uv run --locked python manage.py makemigrations --check --dry-run --noinput --settings=config.settings.test` | Brak brakujących migracji |
| `uv run --locked pytest` bez ręcznego wskazania ustawień | Wszystkie 53 testy zakończone sukcesem |
| Kolekcja testów przy `DJANGO_SETTINGS_MODULE=config.settings.production` w procesie | Wybrana konfiguracja testowa; zebrano 53 testy bez wymagania produkcyjnego sekretu |
| SHA-256 lokalnego `db.sqlite3` przed i po kontrolach | Niezmieniony |
| Walidacja workflow przez actionlint 1.7.12 | Brak błędów składni, wyrażeń i konfiguracji workflow |

Actionlint pobrano z oficjalnego wydania do ignorowanego katalogu `.tools`, a przed uruchomieniem sprawdzono SHA-256 archiwum względem opublikowanego pliku sum kontrolnych. Nie dodano go do zależności aplikacji.

Pełne kontrole lokalne wykonano na Windows, poza ograniczeniami środowiska wykonawczego wymaganymi przez test asynchroniczny. Środowisko Linux i integracja z runnerami GitHub Actions nie były uruchamiane z tego komputera. Nie wykonywano commita ani pushu w ramach T004; zdalny wynik będzie można potwierdzić dopiero po wysłaniu workflow. Lokalnych ustawień `.vscode` nie zmieniano.

## T005 Ustawienia bezpieczeństwa i stałe polityki

Data: 2026-10-26

Wynik: zakończone pomyślnie

### Zakres wykonanych zmian

- Dodano `apps.security.models.SecuritySettings`: stały klucz `1`, `levenshtein_enabled=True`, `password_max_age_days=0`, `idle_timeout_minutes=15` i `updated_at`. Walidacja działa przed zapisem, a częściowy zapis przez `update_fields` obejmuje datę modyfikacji.
- Ograniczenie bazy dopuszcza tylko identyfikator `1`; razem z unikalnością klucza głównego pozwala przechowywać najwyżej jeden rekord. Migracja danych tworzy wymagany rekord początkowy.
- Pola `PolicyIntegerField` odrzucają wartości ułamkowe przed konwersją Django, także przy zwykłych aktualizacjach querysetu. Walidatory określają nieujemną liczbę dni i dodatnią liczbę minut. Ograniczenia bazy chronią zakres oraz całkowitość także przy zapisie wyrażeń omijających konwersję pola.
- `apps.security.constants` definiuje minimalną długość `14`, odległość `4`, historię `5`, długość hasła tymczasowego `16` i czas ważności `timedelta(hours=4)`. Istniejąca konfiguracja walidatora długości Django używa teraz wspólnej stałej, bez zmiany zachowania.
- `get_security_settings()` pobiera rekord z bazy przy każdym wywołaniu; nie używa cache ani zastępczych wartości ukrywających brak migracji danych.
- Dodano migrację schematu `security.0001_initial` i odwracalną migrację danych `security.0002_initial_settings`, używającą modelu historycznego i aliasu połączenia migracji.
- README opisuje model, odczyt i stałe; lista zadań oznacza T005 jako ukończone. Zakres zachowania nie wymagał zmiany specyfikacji ani planu.

### Przeprowadzone kontrole

| Kontrola | Wynik |
|---|---|
| Testy `tests/security/test_security_settings.py` | 30 przypadków zakończonych sukcesem |
| Pełny `python -m pytest -q` | 83 testy zakończone sukcesem |
| `ruff check .` | Brak błędów |
| `ruff format --check .` | Wszystkie 40 plików Pythona poprawnie sformatowane |
| `manage.py check --settings=config.settings.test` | Brak problemów |
| `manage.py makemigrations --check --dry-run --noinput --settings=config.settings.test` | Brak brakujących migracji |
| Migracje w izolowanej bazie testowej oraz ponowne utworzenie schematu modułu przez `MigrationExecutor` | Jeden rekord z wymaganymi wartościami początkowymi |
| Próby błędnych zakresów, ułamków, pustych i niepoprawnych danych | Odrzucone bez zmiany zapisanych ustawień |
| Próba dodatkowego rekordu oraz aktualizacje omijające walidację modelu | Odrzucone przez ograniczenia bazy lub konwersję pola |
| Odczyt po zmianie wszystkich trzech ustawień | Jedno nowe zapytanie zwraca aktualne wartości; data modyfikacji zgodna z kontrolowanym zegarem |
| `manage.py migrate --noinput` na istniejącej lokalnej bazie | Obie nowe migracje zastosowane poprawnie |
| Odczyt lokalnego rekordu po migracji | Liczba rekordów `1`, klucz `1`, reguła `True`, ważność `0`, bezczynność `15` |

Polecenia wykonywano narzędziami z istniejącego `.venv`. Pierwsza próba pełnego zestawu w sandboxie zatrzymała się w istniejącym teście asynchronicznego managera kont przy tworzeniu lokalnego `socketpair` na Windows, tak jak podczas E1. Zatrzymano tę próbę i uruchomiono pełny zestaw poza sandboxem; wszystkie 83 testy przeszły. Testy używały izolowanej bazy, a lokalną bazę zmieniło wyłącznie jawne zastosowanie migracji i dodanie ustawień początkowych.

Nie implementowano formularzy ustawień, middleware, historii haseł ani serwisów zmiany i resetu haseł; pozostają w kolejnych zadaniach. Nie wykonywano commita, pushu ani publicznego wdrożenia. Nie zmieniano lokalnych ustawień `.vscode`.

## T006 Historia i poświadczenia tymczasowe

Data: 2026-10-26

Wynik: zakończone pomyślnie

Przed rozpoczęciem T006 zapisano ukończone T005 w commicie `2a0c6b8` (`feat: add security settings and policy constants (T005)`). Katalog `.vscode` pozostał poza commitem.

### Zakres wykonanych zmian

- Dodano `PasswordHistory`: relacja do użytkownika, `password_hash` i `replaced_at`. Kolejność to czas zastąpienia malejąco, a przy równych czasach klucz główny malejąco.
- Dodano `TemporaryCredential`: relacja do użytkownika, osobny `password_hash`, `issued_at`, `expires_at`, opcjonalne `consumed_at` i `revoked_at` oraz `credential_version`. Hash ostatniego hasła stałego pozostaje w `User.password`; poświadczenia tymczasowe nie zajmują miejsc w historii.
- `PasswordHashField` i jego walidator przyjmują kodowanie Argon2id z niepustą solą i hashem. Nie haszują automatycznie wejścia i nie umieszczają jego wartości w komunikacie błędu. Zwykłe zapisy przez model, `bulk_create` i `QuerySet.update` odrzucają jawne hasła. Dowolne wyrażenia SQL nie stanowią publicznego interfejsu zapisu sekretów.
- Klucze obce używają `PROTECT`: logiczne usunięcie konta zachowuje dane, a fizyczne usunięcie konta posiadającego historię lub poświadczenia jest odrzucane.
- Ograniczenia modelu i bazy wymagają dodatniej wersji, unikalnej pary użytkownik–wersja, wygaśnięcia po wydaniu, zużycia od momentu wydania do chwili przed wygaśnięciem oraz unieważnienia nie wcześniej niż wydanie. Zużyte poświadczenie może być później unieważnione.
- Domyślne czasy wywołują bieżący `timezone.now()` przez funkcję pośrednią, dzięki czemu wspólna fixture zegara kontroluje je w testach.
- Dodano migrację `security.0003_passwordhistory_temporarycredential`, z zależnością od modelu użytkownika. Zaktualizowano README i listę zadań. Zachowanie mieści się w specyfikacji i planie.

### Przeprowadzone kontrole

| Kontrola | Wynik |
|---|---|
| `python -m pytest tests/security/test_credentials.py -q` po poprawkach | 25 nowych przypadków zakończonych sukcesem w zestawie modułu |
| `python -m pytest tests/security -q` | 55 testów zakończonych sukcesem |
| Pełny `python -m pytest -q` poza sandboxem Windows | 108 testów zakończonych sukcesem |
| `ruff check .` | Brak błędów |
| `ruff format --check .` | Wszystkie 43 pliki Pythona poprawnie sformatowane |
| `manage.py check --settings=config.settings.test` | Brak problemów |
| `manage.py makemigrations --check --dry-run --noinput --settings=config.settings.test` | Brak brakujących migracji |
| Migracje na pustej bazie testowej i ponowne utworzenie schematu `security` przez `MigrationExecutor` | Obie tabele istnieją i pozostają puste, ustawienia początkowe są zachowane |
| Prawdziwe hashowanie Argon2id | Dwa hashe tego samego hasła różnią się dzięki soli; oba poprawnie weryfikują hasło |
| Zapisy jawnych haseł, pustych wartości, znacznika hasła nieużywalnego i uszkodzonego kodowania | Odrzucone; zwykłe aktualizacje i zapisy zbiorcze również sprawdzone |
| Niespójne terminy, wersja `0` i powtórzenie wersji dla konta | Odrzucone przez walidację oraz bazę przy pominięciu walidacji modelu |
| Trzy kolejne generacje poświadczeń tymczasowych | Bieżący hash stały oraz identyfikator, hash i czas wpisu historii nie zmieniają się |
| Logiczne i fizyczne usunięcie konta | Logiczne zachowuje dane obu modeli; fizyczne jest chronione |
| `manage.py migrate --noinput` | Nowa migracja zastosowana poprawnie w lokalnej bazie |

Test kolejnych generacji zapisuje stany modeli bezpośrednio, aby sprawdzić ich niezależność; nie zastępuje przyszłych testów serwisu resetu. Limit pięciu poprzednich haseł, generowanie czterogodzinnego poświadczenia, porównanie wersji z kontem i atomowe zużycie pozostają w T009–T011. Kontrole używały rzeczywistego Argon2id i izolowanych baz testowych; pełny zestaw uruchomiono poza sandboxem z uwagi na znane ograniczenie testu asynchronicznego Windows z E1.

Zmiany T006 pozostawiono do przeglądu bez osobnego commita. Nie wykonywano pushu ani publicznego wdrożenia i nie zmieniano `.vscode`.

## T007 Walidacja haseł i konfiguracja Argon2id

Data: 2026-10-26. Wynik: zakończone pomyślnie.

Dodano `validate_permanent_password`: bez zapisu i normalizacji sprawdza stary sekret, potwierdzenie, walidatory Django (14 znaków i lista popularnych haseł), hash bieżącego hasła stałego i pięć najnowszych wpisów historii. Parametr `source_hash` pozwala w kolejnych serwisach sprawdzać hasło tymczasowe, zachowując kontrolę historii haseł stałych. Błędy mają pola i kody, bez wartości sekretów. Istniejąca konfiguracja Django używa rzeczywistego Argon2id.

Dodano 8 przypadków testowych: granica 13/14, potwierdzenie i stary sekret, popularne hasło, brak wymagań klas znaków, historia pięciu haseł (z pominięciem szóstego), historia po przełączeniu w tryb tymczasowy, spacje/Unicode i brak skutków ubocznych. Pełny pytest: **116 testów przeszło**. Ruff, formatowanie, kontrola Django i brakujących migracji przeszły. Pełne testy uruchomiono poza sandboxem Windows ze względu na istniejący test asynchroniczny. Nowych migracji brak.

## T008 Reguła odległości Levenshteina

Data: 2026-10-26. Wynik: zakończone pomyślnie.

Dodano czystą funkcję `levenshtein_distance` o jednostkowych kosztach operacji i pamięci proporcjonalnej do krótszego tekstu. Nie normalizuje Unicode, spacji ani wielkości liter. Wspólny walidator pobiera aktualne ustawienia (lub używa jawnego obrazu polityki przekazanego przez przyszły serwis), sprawdzając próg 4 tylko przy włączonej regule. Porównuje teksty sekretów, bez porównywania tekstu z hashem.

13 nowych testów obejmuje puste ciągi, trzy operacje edycyjne, Unicode i reprezentacje złożone, wielkość liter, spacje, granicę 3/4 oraz wyłączenie i ponowne włączenie reguły. Przy wyłączonej regule nadal odrzucane są hasła krótkie, popularne, bieżące, niezgodne potwierdzenie i zły stary sekret. Testy T007 nadal potwierdzają kontrolę historii. Pełny pytest: **129 testów przeszło**. Ruff, formatowanie, Django i kontrola migracji przeszły; brak nowych migracji. Pełne testy wykonano poza sandboxem Windows.

## T009 Generowanie i resetowanie hasła tymczasowego

Data: 2026-10-26. Wynik: zakończone pomyślnie.

`issue_temporary_credential(user_id)` używa `secrets.choice` z alfabetem ASCII liter i cyfr. Hash Argon2id powstaje poza transakcją. Krótka transakcja unieważnia wcześniejsze poświadczenia, przełącza konto w `TEMPORARY`, zwiększa `session_version` i zapisuje nowe poświadczenie ważne cztery godziny. Nie zmienia `User.password` ani historii. Wynik zawiera identyfikatory, wersję, termin i jednorazowy sekret; sekret jest wyłączony z repr, a funkcja oznacza wrażliwe zmienne dla raportowania błędów.

Pomocnicze kontrole czytają bieżący stan z bazy. Hasło stałe jest odrzucane w trybie tymczasowym; kontrola poświadczenia tymczasowego sprawdza wersję, aktywność konta, tryb, zużycie, unieważnienie i granicę czasu. To odczyt wstępny; atomowe zużycie i kontekst ograniczonego dostępu powstaną w T011/E3. Integracja WWW i jednokrotna prezentacja administratorowi pozostają w E4.

5 nowych testów sprawdza format, losowość kolejnych wydań, rzeczywisty hash, brak sekretu w repr/logach, kolejne resety i zachowanie historii, odrzucenie poprzednich poświadczeń, dokładny termin wygaśnięcia, rollback przy błędzie zapisu oraz odrzucenie zużytych poświadczeń, konta zablokowanego i niezgodnej wersji. Pełny pytest: **134 testy przeszły**. Ruff, formatowanie, Django i kontrola migracji przeszły. Brak nowych migracji; pełne testy poza sandboxem Windows.

## T010 Transakcyjna zmiana hasła

Data: 2026-10-26. Wynik: zakończone pomyślnie.

`change_password` obsługuje konteksty `VOLUNTARY`, `INITIAL`, `EXPIRED` i `RESET`. Wymaga aktualnej wersji konta z zaufanego kontekstu wywołującego. Reset wymaga identyfikatora zużytego, aktualnego poświadczenia z przyszłej ograniczonej sesji. Stary sekret jest ponownie weryfikowany; reguła odległości przy resecie odnosi się do hasła tymczasowego, a kontrola historii nadal do haseł stałych. Kontekst wygasłego hasła wymaga rzeczywistego wygaśnięcia według ustawień.

Walidacja i Argon2id odbywają się przed transakcją. W transakcji ponownie sprawdzany jest stan konta i poświadczenia, aktualizowane są hash, data, tryb i wersja sesji, archiwizowane poprzednie hasło stałe i usuwane wpisy poza pięcioma najnowszymi, a poświadczenia tymczasowe są unieważniane. Pierwsze hasło operatora ADMIN i hasła tymczasowe nie zajmują miejsc historii. Wynik zawiera tylko identyfikator i nową wersję; operacje na sesjach HTTP pozostają w E3.

12 nowych przypadków obejmuje sukces dobrowolny, odrzucenia walidacji bez zapisu, rollback wymuszonego błędu historii, pierwszą zmianę ADMIN, wygaśnięcie, reset z ponownym podaniem sekretu i zakazem powrotu do hasła stałego, pierwszą zmianę konta z hasłem nieużywalnym, siedem kolejnych zmian z zachowaniem pięciu wpisów oraz nieaktualny/zablokowany kontekst. Pełny pytest: **146 testów przeszło**. Ruff, formatowanie, Django i kontrola migracji przeszły; nowych migracji brak. Pełne testy poza sandboxem Windows. Testy kolizji na osobnych połączeniach i obsługa blokady bazy są zakresem T011.

## T011 Jednorazowe zużycie i kontrola współbieżności

Data: 2026-10-26. Wynik: zakończone pomyślnie.

`consume_temporary_credential` weryfikuje hash poza transakcją, następnie ponownie odczytuje konto i poświadczenie. W krótkiej transakcji wykonuje warunkowy zapis, sprawdzając wersję, tryb i aktywność konta, hash, zużycie, unieważnienie i czas `issued_at <= teraz < expires_at`. Tylko dokładnie jeden zmieniony rekord daje wynik `ConsumedCredential` dla przyszłego ograniczonego kontekstu. Nie tworzy jeszcze sesji HTTP.

Zmiana hasła porównuje dane źródłowe sprzed walidacji z aktualnym stanem konta, poświadczenia, pięciu najnowszych wpisów historii i polityki. Ponownie sprawdza terminy; kosztowne hashowanie pozostaje poza transakcją. Zapis wersji konta jest warunkowy i sprawdza liczbę rekordów. Reset również sprawdza liczbę zmienionych kont. Błędy operacyjne bazy, w tym blokada SQLite, są tłumaczone na `SecurityConflict` dopiero po wyjściu z transakcji, bez częściowego zapisu i przyznania dostępu. Nie korzystamy z `select_for_update()`.

Weryfikacja hasła stałego ponownie potwierdza stan po kosztownym porównaniu, aby odrzucić reset wykonany w trakcie. Jest nadal kontrolą odczytową; tworzenie i sprawdzanie sesji z wersją konta pozostaje w E3. Oznaczono również zmienne walidatora i osłony operacji bazodanowych jako wrażliwe w raportach błędów.

Przegląd końcowy wykrył przypadek resetu ADMIN przed pierwszą zmianą hasła operatora. Archiwizujemy tylko hash hasła mającego datę ustawienia hasła stałego; hasło początkowe nie trafia do historii również po odzyskaniu konta.

14 nowych przypadków testowych obejmuje:

- Dwie jednoczesne próby zużycia na niezależnych połączeniach do tej samej tymczasowej plikowej bazy: dokładnie jeden sukces.
- Reset pomiędzy kosztowną walidacją a zapisem starej operacji: starsze zużycie oraz starsza zmiana hasła przegrywają, a nowe poświadczenie i wersja pozostają aktualne.
- Rzeczywistą blokadę zapisu SQLite na osobnym połączeniu przy wydaniu, zużyciu i zmianie hasła: konflikt bez częściowych zmian.
- Błędny sekret, ponowne zużycie, granice czasu przed terminem i dokładnie w terminie oraz wygaśnięcie podczas weryfikacji hasha.
- Zmiany polityki, historii lub poświadczenia podczas obliczania nowego hasha: odrzucenie zapisu.
- Zerową liczbę zmienionych rekordów, reset podczas weryfikacji hasła stałego i odzyskanie początkowego ADMIN bez archiwizacji hasła operatora.

Testy używają barier i zdarzeń z limitami oczekiwania, osobnych połączeń i plików `tmp_path`; nie używają lokalnej bazy ani oczekiwania na upływ godzin. Końcowy pełny zestaw po poprawce ADMIN: **160 testów przeszło w 64,80 s**. Dodatkowo 34 testy serwisów zmiany, walidatorów i współbieżności przeszły w osobnej kontroli po poprawce. Ruff, formatowanie (50 plików Pythona), kontrola Django, brakujących migracji i `git diff --check` przeszły. Brak nowych migracji T007–T011. Pełny zestaw i testy współbieżności uruchomiono na Windows poza sandboxem; wynik zdalnego CI i platformy Linux pozostaje do sprawdzenia po publikacji.

E2 zamyka implementację reguł i serwisów. Formularze, pełne i ograniczone sesje oraz backend logowania są zakresem E3. README i lista zadań opisują aktualny stan. Nie wykonywano pushu ani publicznego wdrożenia; `.vscode` pozostało poza zmianami.

## T012 Logowanie i rozpoznanie trybu poświadczeń

Data: 2026-10-28. Wynik: zakończone pomyślnie.

Dodano `/login/`, polski formularz z maskowaniem i bez normalizacji hasła, `authenticate_login` zwracający wyłącznie identyfikatory, wersję i powód ograniczenia oraz `CredentialBackend`. Jest jedynym backendem w konfiguracji i nie nadaje logowania Django poświadczeniom początkowym, tymczasowym lub wygasłym. Wyszukiwanie używa `strip().casefold()`, nieistniejący login powoduje zastępcze hashowanie Argon2id, a zmiana stanu w trakcie weryfikacji jest ponownie sprawdzana. Każda odmowa ma komunikat „Login lub hasło niepoprawne”. Konteksty sesji podłączane są w T013.

11 nowych testów obejmuje loginy Unicode i spacje w hasłach, wszystkie tryby poświadczeń, blokadę/usunięcie, błędne dane, wygaśnięcie/zużycie/unieważnienie/reset, zastępczy hash i brak domyślnego backendu. Pełny pytest: **171 testów przeszło**. Ruff, formatowanie (54 pliki), kontrola Django i brakujących migracji przeszły. Pełny zestaw poza sandboxem Windows; nowych migracji brak.

## T013 Pełna i ograniczona sesja

Data: 2026-10-28. Wynik: zakończone pomyślnie.

Dodano sesyjny `security_context` z identyfikatorami, wersją, zakresem, powodem i czasami, bez sekretów. Pełny dostęp korzysta z `auth.login`; ograniczony z anonimowego użytkownika Django, po usunięciu poprzedniej sesji i obrocie klucza. Dla resetu wymagany jest pomyślny wynik atomowego zużycia. Każdy chroniony widok sprawdza aktualność konta i wersji, a ograniczony kontekst resetu również poświadczenie i pierwotny termin. Powstał chroniony pulpit `/` i wejście `/password/required/`; formularz zmiany będzie podłączony w T014.

5 nowych przypadków sprawdza obrót klucza i usunięcie poprzednich danych, sesję pełną, ograniczenia INITIAL/RESET/EXPIRED, anonimowość Django, brak sekretu w sesji, jednorazowość oraz utratę dostępu po resecie. Publiczny test renderowania bez zapytań został przeniesiony z chronionego `/` na `/login/`. Pełny pytest: **176 testów przeszło**; Ruff, formatowanie (57 plików), Django i kontrola migracji przeszły. Nowych migracji brak; pełny zestaw poza sandboxem Windows. Timeout będzie dodany w T015, wylogowanie w T016.

## T014 Formularze zmiany hasła

Data: 2026-10-28. Wynik: zakończone pomyślnie.

Dodano `PasswordChangeForm`, `/password/change/` i funkcjonalny `/password/required/`. Pola nie usuwają spacji i nie pokazują ponownie wpisanych sekretów. Formularze korzystają z jednego serwisu E2, a identyfikatory, wersja i powód pochodzą wyłącznie z kontekstu serwera. Przy resecie stare pole ma etykietę „Hasło tymczasowe”. Strona opisuje długość, historię, listę popularnych haseł i aktywną regułę odległości; błędy serwisu są przypisane do pól. Sukces usuwa sesję i kieruje na logowanie ze stałą informacją o zmianie; wersja konta i mechanizm Django odbierają dostęp pozostałym sesjom.

11 nowych testów HTTP sprawdza kompletne ścieżki VOLUNTARY/INITIAL/RESET/EXPIRED, błędne stare hasło, długość 13, potwierdzenie, odległość 3 i historię bez modyfikacji danych, akceptację odległości 4, wyłączenie reguły oraz drugiego klienta po zmianie. Pełny pytest: **187 testów przeszło**; Ruff, formatowanie (59 plików), Django i kontrola migracji przeszły. Nowych migracji brak; pełny zestaw poza sandboxem Windows.

## T015 Middleware bezpieczeństwa i terminy

Data: 2026-10-28. Wynik: zakończone pomyślnie.

Dodano `SecurityContextMiddleware` po obsłudze sesji i uwierzytelniania. Dla każdego rozpoznanego widoku sprawdza aktualne konto i wersję oraz pobiera bieżące ustawienia. Najpierw weryfikuje bezczynność (granica jest już nieważna), dopiero potem zapisuje aktywność GET/POST. Nieprawidłowy lub przyszły czas kończy sesję. Pełny kontekst z wygasłym hasłem zostaje usunięty i zastąpiony ograniczonym kontekstem EXPIRED z nowym kluczem, bez logowania Django. Ograniczony kontekst dopuszcza jedynie wymuszoną zmianę i wylogowanie. Zasoby statyczne i widoki oznaczone `passive_view` nie przedłużają aktywności; przyszłe automatyczne odpytywanie musi korzystać z tego oznaczenia.

18 nowych testów kontroluje moment przed limitem, na nim i po nim, odnowienie aktywności, skrócenie limitu istniejącej sesji, brak odnowienia przez statyczne zasoby i odpytywanie, wartość 0 ważności hasła, skrócenie ważności i granice 24 godzin, wcześniejszy termin sesji ograniczonej, brak przesuwania oryginalnego terminu tymczasowego oraz brak przywrócenia przez stare ciasteczko. Sprawdzono też blokadę, usunięcie, wersję i błędny czas aktywności.

Pełny pytest: **205 testów przeszło**. Ruff, formatowanie (61 plików), Django i kontrola brakujących migracji przeszły. Nowych migracji brak; pełny zestaw poza sandboxem Windows.

Przed T015 zastany wskaźnik `.git/refs/heads/main` zawierał znaki zerowe. Potwierdzono zgodność indeksu i plików z istniejącym commitem T014 `de0d7f1` oraz wpisem refloga. Zachowano kopię uszkodzonego wskaźnika w ignorowanym `.tools/git-recovery` i przywrócono go do pełnego identyfikatora T014. Kontrola Git nie wykazała uszkodzonych obiektów ani brakujących commitów; plików aplikacji i indeksu nie zmieniano przy naprawie.

## T016 Wylogowanie i zabezpieczenia sesji

Data: 2026-10-28. Wynik: zakończone pomyślnie.

Dodano `/logout/` wyłącznie przez POST, z aktywną ochroną CSRF dla obu kontekstów. Sesja jest usuwana z bazy i przeglądarka wraca na logowanie. Pulpit i oba formularze zmiany mają przycisk wylogowania. GET zwraca 405, a żądanie bez CSRF 403, bez zakończenia aktywnej sesji.

Chronione odpowiedzi, przekierowania oraz widoki logowania, zmiany i wylogowania (również błędy CSRF) dostają nagłówki `no-store` i `private`. Istniejące `HttpOnly` i `SameSite=Lax` są utrzymane; w HTTPS działa `Secure`. Token CSRF jest obracany również w ograniczonym logowaniu, przełączeniu sesji do EXPIRED i wylogowaniu. Dodano filtr raportowania aktywny także przy lokalnym DEBUG, który wykorzystuje oznaczenia wrażliwych zmiennych i usuwa sekrety POST oraz ciasteczka z raportów błędów.

Sprawdzono również zmianę polityki po utworzeniu kontekstu EXPIRED: wyłączenie okresowego wygasania nie przyznaje automatycznie pełnego dostępu, ale pozwala dokończyć poprawną zmianę hasła wspólnym serwisem jako dobrowolną zmianę. Nadal wymagany jest stary sekret i wszystkie aktywne walidacje.

9 nowych przypadków obejmuje POST/CSRF/GET dla obu kontekstów, obrót tokenów CSRF, brak przywrócenia przez stary klucz, odrzucenie zmiany hasła bez CSRF, nagłówki, ciasteczka HTTPS, redakcję prawdziwego tekstowego raportu błędu w DEBUG, brak sekretów i klucza sesji w logach/sesjach/przekierowaniach oraz zmianę polityki ograniczonego kontekstu. README i lista zadań opisują aktualny E3 i wskazują T017 jako następny krok.

Końcowy pełny pytest E3: **214 testów przeszło w 218,90 s**. Ruff, formatowanie (63 pliki Pythona), kontrola Django, brakujących migracji i `git diff --check` przeszły. Testy używały izolowanych baz i rzeczywistego Argon2id; pełny zestaw uruchomiono na Windows poza sandboxem. W E3 nie powstały nowe migracje i nie tworzono kont w lokalnej bazie. Wynik Linux i zdalnego CI pozostaje do potwierdzenia po publikacji. Nie wykonywano pushu, publicznego wdrożenia ani zmian `.vscode`.

## Aktualizacja istniejącej lokalnej bazy po odbiorze

Data: 2026-10-28. Użytkowniczka uruchomiła istniejącą lokalną bazę na porcie 8000, w której nie była jeszcze zastosowana `documents.0001_initial`. Pulpit zgłaszał `no such table: documents_document`. Wcześniejszy odbiór dotyczył bazy QA i czystej kopii, więc nie aktualizował tej bazy.

Potwierdzono jedną brakującą migrację tworzącą tabelę dokumentów. Przed zastosowaniem wykonano spójną kopię SQLite przez API backup do ignorowanego `.tools/backups`. `migrate --noinput` zakończyło się poprawnie; porównano identyfikatory kont, loginy, hashe haseł, role, aktywność, tryby poświadczeń, daty zmiany haseł i wersje sesji przed/po — bez zmian. `showmigrations documents` wskazuje `[X] 0001_initial`, kontrola Django przechodzi, a rzeczywisty widok pulpitu ADMIN renderuje HTTP 200 z lokalnej bazy przez RequestFactory, bez tworzenia sesji i zmiany hasła. README uzupełniono o aktualizowanie istniejącej bazy po zmianie źródeł. Nie wykonywano commita.

## Odbiór T017–T035 i zamknięcie E1–E7

Data: 2026-10-28. Wynik: zakończone pomyślnie, bez commitowania.

Wykonano panel kont i bezpieczeństwa, dokumenty i macierz ról, interfejs responsywny, dane demo oraz odbiór czystej kopii. Pełny zestaw w źródłach: **256 testów przeszło**; w osobnej czystej kopii z nowym środowiskiem i bazą: **256 testów przeszło**. Ruff, Django, migracje, actionlint i kontrola diff przeszły. Użytkowniczka potwierdziła zmianę hasła i ponowne logowanie pracownik1 w QA. Brak nowych commitów, pushu i publicznego wdrożenia.

Szczegółowe dowody, zakres przeglądu, czysta kopia i ograniczenia: [pełny odbiór](final-verification.md). Decyzje: [bezpieczeństwo](decisions/security.md).


Wynik PASS oznacza potwierdzenie zachowania testem automatycznym; uwagi o ręcznym odbiorze nie są ukryte przez tę tabelę.

| Kryterium | Wynik | Dowód |
|---|---|---|
| AC-01 | PASS | `tests/accounts/test_login.py::test_refusals_share_one_message` |
| AC-02 | PASS | `tests/accounts/test_sessions.py::test_full_login_rotates_key_and_protects_dashboard`, macierz dokumentów |
| AC-03 | PASS | `test_restricted_context_has_no_full_access`, ograniczony formularz w przeglądarce |
| AC-04 | PASS | `test_minimum_length_boundary`, `test_rejection_shows_errors_and_preserves_account` |
| AC-05 | PASS | `test_minimum_length_boundary` (14 znaków) |
| AC-06 | PASS | `test_confirmation_and_old_secret_must_match_exactly`, testy formularzy |
| AC-07 | PASS | ten sam test oraz HTTP z błędnym starym hasłem |
| AC-08 | PASS | `tests/security/test_levenshtein.py::test_threshold` (3) |
| AC-09 | PASS | `test_threshold` (4), `test_four_edits_pass_and_other_sessions_lose_access` |
| AC-10 | PASS | `test_disabling_rule_only_disables_distance_check`, panel ustawień |
| AC-11 | PASS | `test_five_newest_history_entries_are_checked`, `test_admin_reset_preserves_history_and_revokes_real_sessions` |
| AC-12 | PASS | `test_issue_format_hash_deadline_and_no_logged_secret`, panel kont i demo |
| AC-13 | PASS | `test_expiration_exact_boundary`, `test_consumption_boundary_and_repeat` |
| AC-14 | PASS | `test_two_connections_can_consume_only_once`, dwa klienty przy logowaniu |
| AC-15 | PASS | `test_complete_change_flow`, bootstrap czystej kopii i osobista zmiana hasła oraz ponowne logowanie potwierdzone przez użytkowniczkę |
| AC-16 | PASS | `test_admin_reset_preserves_history_and_revokes_real_sessions`, wyścigi resetu |
| AC-17 | PASS | `tests/documents/test_access.py::test_matrix_through_http` (Czytelnik) |
| AC-18 | PASS | macierz własności Pracownika, 403 potwierdzone również w przeglądarce |
| AC-19 | PASS | macierz Redaktor/Kierownik; publikacja i wycofanie w przeglądarce |
| AC-20 | PASS | macierz Administratora dla szkiców |
| AC-21 | PASS | testy limitów/stanu konta, edycja roli w panelu, `test_unblock_never_restores_invalidated_session` |
| AC-22 | PASS | `tests/accounts/test_models.py`, `test_create_edit_block_delete_and_reset_services` |
| AC-23 | PASS | `test_logout_requires_post_and_csrf_and_invalidates_server_session` |
| AC-24 | PASS | `test_full_idle_boundary`, brak odnowienia na granicy |
| AC-25 | PASS | `test_activity_renews_but_policy_shortening_applies_immediately` |
| AC-26 | PASS | test skrócenia bezczynności i `test_expiry_policy_downgrades_existing_full_context` |
| AC-27 | PASS | `test_password_expiry_boundary_in_existing_session`, ścieżka EXPIRED przez HTTP |
| AC-28 | PASS | modele hashy, `test_credentials_do_not_appear_in_sessions_logs_or_redirects`, raport błędu DEBUG |
| AC-29 | PASS | `test_document_csrf_author_and_state_are_protected`, CSRF panelu i zmiany hasła |
| AC-30 | PASS | `test_text_is_escaped_and_authentication_cannot_be_bypassed`, znacznik skryptu w przeglądarce |
| AC-31 | PASS automatyczny | czysta kopia, nowe środowisko, migracje, ADMIN, demo i 256 testów |

## Korekta SESS-07 — automatyczne opuszczenie wygasłej strony

Data: 2026-10-29. Bez commita.

Zgłoszenie: otwarty pulpit ADMIN pozostawał widoczny po 15 minutach. Dotychczas middleware sprawdzał limit dopiero przy następnym żądaniu. Dodano licznik i bierny GET `/session/status/`, który nie odnawia aktywności. Middleware dopuszcza tę kontrolę również w ograniczonym kontekście, a dla wygasłej sesji zwraca JSON zamiast przekierowania HTML. Odpowiedź ma `no-store` i zawiera wyłącznie stan, zakres i pozostałe sekundy.

Skrypt sprawdza serwer co 30 sekund, przy terminie wygaśnięcia i po powrocie do karty. Przed przekierowaniem uwzględnia aktywność innej karty. Przy utracie połączenia po upływie znanego terminu ukrywa treść do ponownego potwierdzenia stanu. Serwer nadal egzekwuje limit bez JavaScript. Zaktualizowano specyfikację SESS-07, plan, T015 i README.

Weryfikacja:

- Pełny pytest: **265 passed in 47.53s**. Dziewięć nowych przypadków w `tests/security/test_session_status.py`: sesja ADMIN i dokładna granica 15 minut mimo wielokrotnego odpytywania, aktywność drugiej karty, skrócenie polityki, wygaśnięcie hasła, ograniczone konteksty INITIAL/RESET i ich terminy, anonimowy dostęp bez tworzenia sesji, brak cache, metoda GET, włączenie skryptu i nieprawidłowy czas aktywności.
- Skrypt `static/js/session.js` wykonany w Node z symulowanym DOM/zegarem/fetch: przekierowanie po wygaśnięciu, brak żądań przy samym odliczaniu, odnowienie w innej karcie, ukrycie treści offline i przywrócenie po weryfikacji, przejście do wymaganej zmiany hasła oraz odrzucenie wadliwej odpowiedzi. Lokalny harness: `.tools/check-session-script.cjs` (ignorowany). Nie wykonywano dodatkowej ręcznej próby przeglądarkowej.
- Ruff, formatowanie 86 plików, `node --check static/js/session.js`, `manage.py check` i `git diff --check`: PASS.


## T036 Modele i ustawienia ochrony logowania

Data: 2026-10-29. Dodano `login_failure_limit=5`, `LOGIN_LOCK_SECONDS=900`, `LoginAttemptState` (unikalny HMAC loginu po strip/casefold, licznik, termin, wersja) i minimalny `SecurityEvent` (zamknięte kategorie, korelacja HMAC, czas). Model i baza wymuszają poprawne zakresy; brak pól na hasła, tokeny lub surowe loginy. Migracja `0004_login_protection` jest addytywna i nie wprowadza jeszcze limitu IP. Zmiana klucza Django zmienia korelację HMAC, co wymaga traktowania rotacji jako resetu tych liczników.

Weryfikacja: 45 testów modeli logowania i ustawień PASS; w tym unikalność znormalizowanej tożsamości, błędne progi, ograniczenia bazy, dozwolone kategorie oraz migracje pustego schematu i istniejących danych. Test porównuje wszystkie pola użytkownika, historii, poświadczenia tymczasowego, dokumentu i dotychczasowej polityki przed i po migracji. Ruff, formatowanie, kontrola Django i zgodności migracji: PASS. Lokalnej bazy użytkowniczki nie migrowano; zostanie przygotowana po zakończeniu E8.


## T037 Atomowy limit prób dla konta

Data: 2026-10-29. `attempt_login()` obsługuje błędy dla istniejących i nieistniejących loginów, wspólną normalizację, próg z aktualnej polityki, blokadę na 900 sekund, brak jej odnawiania i zerowanie po sukcesie lub końcu. Nie zmienia administracyjnego stanu konta ani wcześniej otwartych sesji. Logowanie używa atomowej finalizacji licznika, ponownej kontroli snapshotu konta/poświadczenia i zapisu pełnego albo ograniczonego kontekstu. Weryfikacja Argon2 odbywa się poza blokadą zapisu, także przy haśle tymczasowym. Dotychczasowa samodzielna usługa konsumpcji nadal zachowuje pełną weryfikację sekretu.

Przeniesiono planowane w T040 rozdzielenie walidacji pól od uwierzytelnienia do T037, aby bramka blokady poprzedzała sprawdzenie hasła. T040 doda honeypot i CAPTCHA. Wspólny fixture plikowej bazy przeniesiono do `tests/conftest.py`; stary test migracji dostał jawne przygotowanie historycznej polityki, aby nie zależał od kolejności testów transakcyjnych.

Weryfikacja: pełny zestaw 297 testów PASS. Nowe testy obejmują ADMIN/INITIAL, stałe i tymczasowe hasła, nieistniejący login, dokładne granice czasu, zmianę progu podczas weryfikacji, reset poświadczenia po sprawdzeniu hasła, brak inkrementacji dla błędów pól/CSRF oraz zachowanie istniejącej sesji. Rzeczywiste oddzielne połączenia SQLite potwierdzają brak utraty inkrementacji, pierwszeństwo blokady wobec równoległego poprawnego hasła oraz jednorazową konsumpcję przy dwóch równoległych logowaniach. Testy sprawdzają brak Argon2 wewnątrz transakcji zapisu. Ruff, formatowanie 97 plików, kontrola Django, zgodności migracji i diff: PASS.
