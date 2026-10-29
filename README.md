# Cybersecurity Identity Access

Edukacyjna aplikacja Django do zarządzania kontami, hasłami i dokumentami. Obejmuje logowanie, cykl życia haseł, sesje, panel administratora oraz pięć ról z kontrolą dostępu po stronie serwera. Interfejs jest w języku polskim i działa na komputerze oraz telefonie. Projekt jest przeznaczony do uruchomienia lokalnego; publikacja kodu i publiczne wdrożenie są osobnymi działaniami.

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

Po aktualizacji źródeł wykonaj ponownie `migrate` również dla istniejącej bazy. Sam restart serwera nie tworzy nowych tabel. Błąd `no such table: documents_document` oznacza niezastosowaną migrację modułu dokumentów.

```powershell
uv run --locked python manage.py check
uv run --locked python manage.py migrate --noinput
uv run --locked python manage.py runserver
```

Wejście pod [http://127.0.0.1:8000/](http://127.0.0.1:8000/) kieruje niezalogowaną osobę na [formularz logowania](http://127.0.0.1:8000/login/). Serwer zatrzymasz przez `Ctrl+C`.

Pierwsza migracja tworzy własną tabelę `accounts_user` zamiast domyślnej `auth_user`. Migracje tworzą też ustawienia bezpieczeństwa oraz tabele historii haseł, poświadczeń i dokumentów. Można je bezpiecznie uruchamiać ponownie. Lokalna baza nie jest wersjonowana; migracje nie tworzą kont.

## Pierwszy ADMIN i demonstracja

Po migracjach utwórz administratora. Hasło zostanie pobrane dwukrotnie w ukrytym polu terminala, nigdy jako argument komendy:

```powershell
uv run --locked python manage.py init_admin
uv run --locked python manage.py seed_demo
uv run --locked python manage.py runserver
```

Wejdź na `/login/`, użyj loginu `ADMIN` i hasła podanego w terminalu. Pierwsze logowanie umożliwia wyłącznie ustawienie własnego hasła stałego. Po zmianie zaloguj się ponownie. Ponowne `init_admin` nie nadpisuje istniejącego konta.

`seed_demo` działa tylko w konfiguracji lokalnej. Tworzy sześć kont poza ADMIN oraz dokument opublikowany i szkice dwóch autorów. Generuje hasła przy wykonaniu i pokazuje je raz w terminalu. Każde ma 16 znaków, ważność 4 godzin i wymaga zmiany przy pierwszym logowaniu.

| Login | Rola |
|---|---|
| `kierownik` | Kierownik |
| `redaktor` | Redaktor |
| `pracownik1`, `pracownik2` | Pracownik |
| `czytelnik1`, `czytelnik2` | Czytelnik |

Ponowne wykonanie `seed_demo` nie duplikuje danych i nie zmienia istniejących haseł. Jawny reset kont demo (bez ADMIN):

```powershell
uv run --locked python manage.py seed_demo --reset-passwords
```

Zapomniane lub zużyte hasło tymczasowe wymaga nowego resetu przez administratora. Dostęp do ADMIN odzyskuje operator lokalnie, potwierdzając operację wpisaniem `ADMIN`:

```powershell
uv run --locked python manage.py recover_admin
```

Odzyskanie wydaje nowe hasło tymczasowe, unieważnia sesje i zachowuje historię. Nie ma anonimowego odzyskiwania przez WWW ani publicznej rejestracji. Haseł nie przekazuj w URL, argumentach poleceń, logach ani plikach projektu.

## Role i dokumenty

Każda rola czyta opublikowane dokumenty. Administrator zarządza kontami i bezpieczeństwem, ale nie ma dostępu do szkiców. Kierownik czyta i edytuje wszystkie szkice, tworzy je, publikuje i wycofuje publikację. Redaktor tworzy, czyta i edytuje wszystkie szkice, ale nie publikuje. Pracownik tworzy i edytuje wyłącznie własne szkice. Czytelnik ma tylko odczyt publikacji.

Publikację trzeba wycofać przed edycją. Dokumenty są tekstowe i nie mają funkcji usuwania ani załączników. Dane HTML są wyświetlane jako tekst. Konto autora można usunąć logicznie bez utraty autorstwa dokumentów; login pozostaje zarezerwowany.

Panel kont: `/management/users/`. Ustawienia bezpieczeństwa: `/management/security/`. Oba są dostępne wyłącznie dla ADMIN. Reset, blokada i usunięcie wymagają potwierdzenia z nazwą konta i opisem skutku. Wydane hasło jest pokazywane raz w odpowiedzi bez cache, nigdy w sesji. Lista dokumentów: `/documents/`; anonimowe wejście wraca po zalogowaniu do bezpiecznego lokalnego adresu. Brak uprawnień daje 403, a nieistniejący dokument 404.

## Model konta

Każde konto ma jedną rolę: Administrator, Kierownik, Redaktor, Pracownik albo Czytelnik. Login jest niezmienny po utworzeniu, a unikalność jest sprawdzana na podstawie `strip().casefold()`, również dla znaków spoza ASCII.

Rola Administrator jest zarezerwowana dla loginu `ADMIN`, zapisywanego zawsze w tej postaci. Konto to nie może zostać administracyjnie zablokowane, usunięte ani pozbawione roli. Czasowy limit błędnych logowań z modułu 2 dotyczy również ADMIN. Nie używamy flag `is_staff` i `is_superuser`; próby ich nadania są odrzucane, a komenda `createsuperuser` nie służy do inicjalizacji kont projektu. Wbudowany panel Django Admin nie jest udostępniony.

Model przechowuje także tryb poświadczeń, datę ostatniej zmiany hasła, znacznik usunięcia i wersję sesji. Serwisy bezpieczeństwa i obsługa sesji sprawdzają te pola, aby odebrać dostęp po resecie, zmianie hasła lub unieważnieniu wersji konta.

## Ustawienia bezpieczeństwa

Od E9 logowanie i zmiana hasła wymagają kluczy Turnstile. Przed użyciem formularzy wykonaj [konfigurację CAPTCHA](docs/module-2/turnstile.md); przy braku kluczy operacja zostanie odrzucona.

Migracje modułu `security` tworzą jeden rekord `SecuritySettings` o identyfikatorze `1`. Domyślnie reguła Levenshteina jest włączona, ważność hasła stałego wynosi `0` (bez okresowego wygasania), a limit bezczynności sesji to 15 minut. Dni muszą być całkowite i nieujemne, minuty całkowite i dodatnie.

Na zalogowanych stronach licznik pokazuje pozostały czas sesji. Po wygaśnięciu strona automatycznie wraca do logowania. Limit liczymy od ostatniego żądania użytkownika, np. otwarcia dokumentu lub wysłania formularza; samo poruszanie myszą i wpisywanie tekstu go nie odnawia. Bierne sprawdzanie stanu w tle nie przedłuża sesji, ale uwzględnia aktywność w innych kartach. Przy braku połączenia po upływie znanego terminu chroniona treść jest ukrywana do ponownej weryfikacji. Bez JavaScript serwer nadal odrzuca wygasłą sesję przy następnym żądaniu. Po aktualizacji aplikacji odśwież otwarte strony, aby załadować skrypt licznika.

Kod aplikacji pobiera bieżące wartości przez `apps.security.selectors.get_security_settings()`, wykonujący nowy odczyt z bazy przy każdym wywołaniu. Brak rekordu jest błędem inicjalizacji, bez zastępowania ustawień domyślnymi w pamięci. Zmiany zapisane przez model aktualizują `updated_at`, również przy użyciu `update_fields`.

Moduł `apps.security.constants` definiuje stałe: minimalną długość hasła 14, minimalną odległość Levenshteina 4, historię 5 haseł stałych, długość hasła tymczasowego 16 i jego ważność 4 godziny. Konfiguracja walidatora długości Django korzysta ze wspólnej stałej. Panel umożliwia zmianę reguły odległości, ważności hasła, bezczynności i progu błędnych logowań; pozostałe wartości są stałe.

### Limit logowania po E8

W panelu **Ustawienia → Limit błędnych logowań** ADMIN ustawia dodatni całkowity próg, domyślnie 5. Osiągnięcie progu blokuje następne logowania na 15 minut, także z poprawnym hasłem i także dla ADMIN. To oddzielny mechanizm od limitu bezczynności sesji. Wcześniej otwarte sesje działają zgodnie z ich własnymi zasadami.

Ekran logowania pokazuje pozostały czas blokady. Kolejne próby i samo odliczanie nie przesuwają terminu. Po upływie czasu należy ponownie wysłać formularz; skrypt nie wysyła hasła automatycznie. Bez JavaScript pozostały czas jest widoczny w odpowiedzi serwera. Poprawne logowanie przed blokadą i koniec blokady zerują licznik; obniżenie progu obowiązuje przy następnej próbie. Takie same komunikaty i liczniki obowiązują dla nieistniejących loginów.

Liczniki i zdarzenia zawierają HMAC znormalizowanego loginu, bez jego surowej wartości i bez haseł. Rotacja `DJANGO_SECRET_KEY` zmienia te klucze i resetuje korelację liczników. Zmiany schematu stosuje się poleceniem `uv run --locked python manage.py migrate`. E9 doda CAPTCHA i honeypot; E8 obejmuje limit konta.

Testy etapu E8:

```powershell
uv run --locked pytest tests/security/test_login_models.py tests/security/test_login_limits.py tests/security/test_login_limit_ui.py
```

Test samego skryptu odliczania, wymagający Node.js:

```powershell
node --test tests/js/login-lock.test.cjs
```

Testy T005 można uruchomić osobno:

```powershell
uv run --locked pytest tests/security/test_security_settings.py
```

## Historia haseł i poświadczenia tymczasowe

`PasswordHistory` przechowuje użytkownika, hash wycofanego hasła stałego i czas jego zastąpienia (`replaced_at`). Wpisy są uporządkowane od najnowszego. `TemporaryCredential` ma osobny hash, `issued_at`, `expires_at`, opcjonalne `consumed_at` i `revoked_at` oraz `credential_version` odpowiadającą wersji konta w chwili wydania. Dla konta można zapisać tylko jedno poświadczenie danej wersji. Poświadczenie może być zużyte, a następnie unieważnione.

Oba modele przyjmują hash Argon2id z solą, bez automatycznego hashowania podanego tekstu. Pola odrzucają jawne hasła również w zwykłych zapisach zbiorczych ORM. Ograniczenia bazy wymagają dodatniej wersji, wygaśnięcia po wydaniu, zużycia przed wygaśnięciem i unieważnienia nie wcześniej niż wydanie. Powiązane konta są chronione przed fizycznym usunięciem; logiczne usunięcie zachowuje rekordy.

Modele są używane przez serwisy wydawania, resetu i zmiany haseł. Serwis zmiany utrzymuje pięć poprzednich haseł stałych, a atomowe zużycie poświadczenia pozwala najwyżej jednej próbie otrzymać wynik dla ograniczonego kontekstu. Testy modeli:

```powershell
uv run --locked pytest tests/security/test_credentials.py
```

## Serwisy bezpieczeństwa po E2

- `validate_permanent_password` w `apps.security.validators` sprawdza stary sekret, potwierdzenie, długość, popularne hasła, historię i aktywną regułę odległości Levenshteina. Nie zmienia danych i nie normalizuje haseł.
- `issue_temporary_credential(user_id)` w `apps.security.services` zwraca jednorazowy sekret oraz identyfikator, wersję i termin poświadczenia. Zachowuje historię, unieważnia poprzednie poświadczenia i zwiększa wersję sesji. Wyniku nie należy zapisywać w sesji, loggerze ani komunikatach Django; interfejs ma pokazać sekret jednorazowo.
- `consume_temporary_credential(credential_id, secret)` atomowo zużywa nadal ważne poświadczenie. Tylko pomyślny wynik z identyfikatorami, wersją i pierwotnym terminem pozwala przy logowaniu utworzyć ograniczony kontekst zmiany hasła. Utrata tego kontekstu wymaga nowego resetu.
- `change_password` przyjmuje identyfikator użytkownika, stary sekret, nowe hasło i potwierdzenie oraz nazwane `reason` (`ChangeReason`), `expected_version` i dla resetu `credential_id`. Wersja i identyfikator poświadczenia muszą pochodzić z zaufanego kontekstu serwera. Powody to `VOLUNTARY`, `INITIAL`, `EXPIRED` i `RESET`. Serwis zapisuje wszystkie zmiany transakcyjnie i zwiększa wersję sesji; widok zamyka sesję HTTP i kieruje do ponownego logowania.

Kosztowne hashowanie odbywa się poza transakcją. Zapis ponownie sprawdza stan konta, poświadczenia, historii i polityki. `SecurityConflict` oznacza zmianę stanu lub błąd blokady bazy: brak przyznania dostępu i brak częściowego zapisu. Wymagane jest ponowienie od początku z aktualnym kontekstem. Nie używamy `select_for_update()` do ochrony SQLite. Pomocnicze funkcje `verify_*` są kontrolami odczytowymi i same nie przyznają sesji ani uprawnień.

Testy współbieżności tworzą tymczasową plikową bazę przez `tmp_path` i używają osobnych połączeń w wątkach. Nie korzystają z lokalnej `db.sqlite3`, nie wymagają upływu godzin ani usług zewnętrznych:

```powershell
uv run --locked pytest tests/security
uv run --locked pytest tests/security/test_concurrency.py
```

## Logowanie i sesje po E3

| Adres | Metody | Dostęp |
|---|---|---|
| `/login/` | GET, POST | Formularz logowania |
| `/` | GET | Pulpit pełnej sesji |
| `/password/change/` | GET, POST | Zwykła zmiana własnego hasła |
| `/password/required/` | GET, POST | Wymuszona zmiana w ograniczonym kontekście |
| `/logout/` | POST | Wylogowanie pełnej lub ograniczonej sesji z CSRF |

Pierwsze hasło ADMIN, ważne hasło tymczasowe i wygasłe hasło stałe dają wyłącznie ograniczony kontekst. Nie jest on uwierzytelnionym użytkownikiem Django i nie otwiera pulpitu. Przy resecie formularz ponownie wymaga hasła tymczasowego. Po poprawnej zmianie trzeba zalogować się nowym hasłem; dotychczasowe sesje tracą dostęp.

`SecurityContextMiddleware` działa po obsłudze sesji i uwierzytelniania. Przy żądaniu odczytuje bieżące konto, wersję oraz ustawienia i sprawdza limit przed odnowieniem aktywności. Sesja na granicy limitu jest już nieważna. Zmiana ważności hasła może od razu przełączyć pełny dostęp na ograniczony. Hasło tymczasowe i jego ograniczony kontekst zachowują oryginalny termin czterech godzin, niezależnie od aktywności. Statyczne pliki nie przedłużają sesji; przyszłe widoki automatycznego odpytywania muszą być oznaczone `apps.security.middleware.passive_view`.

Chronione odpowiedzi i widoki uwierzytelniania mają `Cache-Control: no-store`. Wylogowanie usuwa sesję z bazy; GET jej nie kończy, a stare ciasteczko nie przywraca dostępu. Sesyjne ciasteczka mają `HttpOnly` i `SameSite=Lax`, a w HTTPS także `Secure`. Token CSRF jest obracany również przy ograniczonym logowaniu, przełączeniu do wymuszonej zmiany i wylogowaniu. Filtr raportowania ukrywa sekrety POST oraz ciasteczka również w lokalnym trybie debugowania.

Nie ma publicznej rejestracji ani wbudowanego panelu Django Admin. Konta inicjalizuje operator lub tworzy administrator. Ścieżki uwierzytelniania są także weryfikowane na kontach tworzonych w izolowanych testach:

```powershell
uv run --locked pytest tests/accounts/test_login.py tests/accounts/test_sessions.py tests/security/test_password_views.py tests/security/test_session_limits.py tests/security/test_session_protection.py
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

[Indeks SDD i dalsza kolejność prac](specs/README.md) opisuje zakończony moduł 1 oraz plan modułu 2: ochronę przed botami i wyciekiem danych. Nowe zadania E8–E13 (T036–T055) są opisane w SDD; E8 jest zakończone, a następne zadanie to T039 w E9; limit IP jest zakresem dodatkowym.

- [Specyfikacja](specs/001-identity-access/spec.md)
- [Plan techniczny](specs/001-identity-access/plan.md)
- [Zadania implementacyjne](specs/001-identity-access/tasks.md)

[Wyniki weryfikacji](docs/verification.md) opisują kontrole dotychczas wykonanych zadań.
