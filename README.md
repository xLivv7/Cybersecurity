# Cybersecurity Identity Access

Edukacyjny projekt aplikacji webowej w Pythonie do zarządzania kontami, hasłami i uprawnieniami. Dostępny jest szkielet Django ze stroną startową, konfiguracjami środowisk i własnym modelem użytkownika. Logowanie, zarządzanie kontami i dokumenty powstaną w kolejnych zadaniach.

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

Uruchom kontrolę konfiguracji, zastosuj migracje i uruchom serwer:

```powershell
uv run --locked python manage.py check
uv run --locked python manage.py migrate --noinput
uv run --locked python manage.py runserver
```

Strona startowa jest dostępna pod adresem [http://127.0.0.1:8000/](http://127.0.0.1:8000/). Serwer zatrzymasz przez `Ctrl+C`.

Pierwsza migracja tworzy własną tabelę `accounts_user` zamiast domyślnej `auth_user`. Migracje można bezpiecznie uruchamiać ponownie; Django pomija już zastosowane operacje. Lokalna baza nie jest wersjonowana. Migracja nie tworzy jeszcze żadnych kont, również `ADMIN`; komendy inicjalizacji i odzyskiwania administratora powstaną w T017.

## Model konta

Każde konto ma jedną rolę: Administrator, Kierownik, Redaktor, Pracownik albo Czytelnik. Login jest niezmienny po utworzeniu, a unikalność jest sprawdzana na podstawie `strip().casefold()`, również dla znaków spoza ASCII.

Rola Administrator jest zarezerwowana dla loginu `ADMIN`, zapisywanego zawsze w tej postaci. Konto to nie może zostać zablokowane, usunięte ani pozbawione roli. Nie używamy flag `is_staff` i `is_superuser`; próby ich nadania są odrzucane, a komenda `createsuperuser` nie służy do inicjalizacji kont projektu. Wbudowany panel Django Admin nie jest udostępniony.

Model przechowuje także tryb poświadczeń, datę ostatniej zmiany hasła, znacznik usunięcia i wersję sesji. Te pola stanowią podstawę przyszłych serwisów bezpieczeństwa. Reguły logowania i unieważniania sesji powstaną w kolejnych zadaniach.

## Ustawienia bezpieczeństwa

Migracje modułu `security` tworzą jeden rekord `SecuritySettings` o identyfikatorze `1`. Domyślnie reguła Levenshteina jest włączona, ważność hasła stałego wynosi `0` (bez okresowego wygasania), a limit bezczynności sesji to 15 minut. Dni muszą być całkowite i nieujemne, minuty całkowite i dodatnie.

Kod aplikacji pobiera bieżące wartości przez `apps.security.selectors.get_security_settings()`, wykonujący nowy odczyt z bazy przy każdym wywołaniu. Brak rekordu jest błędem inicjalizacji, bez zastępowania ustawień domyślnymi w pamięci. Zmiany zapisane przez model aktualizują `updated_at`, również przy użyciu `update_fields`.

Moduł `apps.security.constants` definiuje stałe: minimalną długość hasła 14, minimalną odległość Levenshteina 4, historię 5 haseł stałych, długość hasła tymczasowego 16 i jego ważność 4 godziny. Konfiguracja walidatora długości Django korzysta ze wspólnej stałej. Pozostałe walidatory, serwisy i obsługa sesji zostaną podłączone w kolejnych zadaniach; panel zmiany ustawień powstanie w T021.

Testy T005 można uruchomić osobno:

```powershell
uv run --locked pytest tests/security/test_security_settings.py
```

## Historia haseł i poświadczenia tymczasowe

`PasswordHistory` przechowuje użytkownika, hash wycofanego hasła stałego i czas jego zastąpienia (`replaced_at`). Wpisy są uporządkowane od najnowszego. `TemporaryCredential` ma osobny hash, `issued_at`, `expires_at`, opcjonalne `consumed_at` i `revoked_at` oraz `credential_version` odpowiadającą wersji konta w chwili wydania. Dla konta można zapisać tylko jedno poświadczenie danej wersji. Poświadczenie może być zużyte, a następnie unieważnione.

Oba modele przyjmują hash Argon2id z solą, bez automatycznego hashowania podanego tekstu. Pola odrzucają jawne hasła również w zwykłych zapisach zbiorczych ORM. Ograniczenia bazy wymagają dodatniej wersji, wygaśnięcia po wydaniu, zużycia przed wygaśnięciem i unieważnienia nie wcześniej niż wydanie. Powiązane konta są chronione przed fizycznym usunięciem; logiczne usunięcie zachowuje rekordy.

Te modele przygotowują dane dla kolejnych zadań. Generowanie i reset poświadczeń powstaną w T009, ograniczanie historii do pięciu poprzednich haseł w T010, a atomowe zużycie i kontrola współbieżności w T011. Testy modeli:

```powershell
uv run --locked pytest tests/security/test_credentials.py
```

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

## Testy i kontrola kodu

Konfiguracja pytest i Ruff znajduje się w `pyproject.toml`. Lokalnie wykonuj te same kontrole co GitHub Actions:

```powershell
uv sync --locked --dev
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked python manage.py check --settings=config.settings.test
uv run --locked python manage.py makemigrations --check --dry-run --noinput --settings=config.settings.test
uv run --locked pytest
```

Pytest domyślnie wybiera `config.settings.test`, także gdy zmienna środowiskowa `DJANGO_SETTINGS_MODULE` wskazuje inne środowisko. Ustawienia testowe nie odczytują `.env`, a migracje są stosowane w izolowanej bazie w pamięci. Testy używają rzeczywistego Argon2id i nie korzystają z lokalnej `db.sqlite3`.

Testy sprawdzają izolację ustawień, obsługę sekretów i hostów, wymuszenie HTTPS, uruchomienie WSGI/ASGI, renderowanie strony bez zapytań do bazy, tryb transakcji SQLite oraz ochronę modelu konta. Aby uruchomić tylko testy modelu:

```powershell
uv run --locked pytest tests/accounts/test_models.py
```

Ruff sprawdza i formatuje kod dla Pythona 3.13, z limitem linii 88 znaków. Pomija lokalne narzędzia i cache, również przy wskazaniu ich ścieżek w poleceniu. `.gitattributes` ustala końce linii LF dla źródeł, konfiguracji i dokumentacji, aby kontrole działały tak samo na Windows i Linux.

### Wspólne fixtures

`tests/conftest.py` udostępnia:

- `user_factory`: tworzy konta w izolowanej bazie, z kolejnymi loginami lub wskazanym loginem i rolą. Domyślnie nie ustawia używalnego hasła; podanie `password` korzysta z rzeczywistego hashera.
- `admin_factory` i `admin`: tworzą chronione konto `ADMIN` w początkowym trybie poświadczeń, bez flag uprzywilejowania frameworka.
- `clock`: kontroluje `django.utils.timezone.now()`; udostępnia `now()`, `set(świadoma_strefy_data)` i `advance(timedelta(...))`. Po teście oryginalny zegar jest automatycznie przywracany.

Fabryki ustawiają `date_joined` według aktualnego zegara testowego. Kod sprawdzający terminy powinien wywoływać `timezone.now()` przez moduł Django, aby testy mogły sterować czasem bez oczekiwania przez `sleep`. Zegar nie zastępuje funkcji czasu w innych procesach ani całej bibliotece standardowej.

### GitHub Actions

Workflow `.github/workflows/ci.yml` uruchamia się na push, pull request i ręcznie. Na Windows i Linux instaluje Python z `.python-version`, uv 0.13.5 i zależności z `uv.lock`, po czym wykonuje sześć poleceń z bloku powyżej. Używa konfiguracji testowej bez sekretów i przypiętych identyfikatorów akcji. Pierwszy wynik zdalny będzie dostępny w zakładce Actions po wysłaniu workflow do GitHuba.

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

[Wyniki weryfikacji](docs/verification.md) opisują kontrole dotychczas wykonanych zadań.
