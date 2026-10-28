# Zadania implementacyjne modułu identyfikacji uwierzytelniania i autoryzacji

Status: w realizacji  
Wersja: 0.13

Data: 2026-10-28

Podstawa: [spec.md](spec.md), wersja 0.2, oraz [plan.md](plan.md), wersja 0.1

## 1. Jak korzystać z listy

Zadania realizujemy w etapach E1–E7 zgodnie z planem. Identyfikatory `T001`–`T035` służą do powiązania prac, testów i zmian w repozytorium. Pole wyboru oznacza ukończenie i weryfikację zadania; puste pole oznacza zadanie jeszcze nieukończone.

Każde zadanie zawiera zakres, zależności, wymagania ze specyfikacji oraz warunek ukończenia. Brak bezpośredniego kryterium AC przy zadaniu infrastrukturalnym nie oznacza braku weryfikacji — obowiązuje wskazany warunek ukończenia.

Zadanie oznaczamy jako wykonane po implementacji i weryfikacji, z odnotowaniem wyniku odpowiednich kontroli w opisie zmiany. Nie odkładamy testów bezpieczeństwa do końca projektu. Przed zmianą zachowania aktualizujemy specyfikację, a następnie plan i zadania.

Ścieżki wskazane poniżej są docelowymi lokalizacjami w repozytorium. Tworzymy tylko pliki potrzebne do danego zadania. Publikacja kodu i publiczne wdrożenie nie są zadaniami tego dokumentu.

## 2. E1 Podstawa projektu

### T001 Środowisko i zależności

- [x] Przygotować środowisko Python 3.13 i deklarację zależności.

**Zakres:** utworzyć `pyproject.toml`, `.python-version`, `uv.lock` i `.gitignore`. Zadeklarować Django 5.2 z obsługą Argon2, bibliotekę konfiguracji środowiska oraz grupę narzędzi deweloperskich: pytest, pytest-django i Ruff. Przypiąć rozstrzygnięte wersje w pliku blokady. Wykluczyć środowisko wirtualne, sekrety, lokalne bazy i pliki tymczasowe testów.

**Zależności:** brak.  
**Wymagania:** TECH-01, TECH-06.  
**Gotowe, gdy:** środowisko można odtworzyć z `uv.lock`, narzędzia uruchamiają się w zadeklarowanej wersji Pythona, a lokalne artefakty pozostają poza zakresem wersjonowania.

**Wykonano 2026-10-22:** utworzono wymagane pliki i lokalne środowisko Python 3.13.17. Zależności aplikacji i grupa `dev` są zablokowane w `uv.lock`. Sprawdzono odtworzenie drugiego środowiska offline, zgodność wersji, uruchomienie narzędzi, działanie Argon2id oraz reguły `.gitignore`. Instrukcja znajduje się w [README](../../README.md), a szczegóły w [wynikach weryfikacji](../../docs/verification.md#t001-środowisko-i-zależności).

### T002 Szkielet Django i konfiguracja środowisk

- [x] Utworzyć projekt oraz moduły `accounts`, `security` i `documents`.

**Zakres:** przygotować `manage.py`, `config/`, konfiguracje `base`, `local`, `test` i `production`, pakiety modułów, adresy główne oraz katalogi szablonów i zasobów. Włączyć CSRF i sesje bazodanowe. Skonfigurować SQLite z krótkimi transakcjami `IMMEDIATE`, UTC w zapisie i `Europe/Warsaw` w prezentacji. Utworzyć `.env.example` bez prawdziwych sekretów. Nie uruchamiać pierwszej migracji przed T003.

**Zależności:** T001.  
**Wymagania:** TECH-01, TECH-02, TECH-03, TECH-08, TECH-09.  
**Gotowe, gdy:** struktura odpowiada planowi, ustawienia testowe są izolowane od lokalnych, a konfiguracja publicznego środowiska wymaga sekretu i jawnych hostów oraz wyłącza debugowanie.

**Wykonano 2026-10-25:** utworzono szkielet Django, pakiety trzech modułów, ustawienia środowisk, punkty wejścia WSGI/ASGI, adresy, szablony i podstawowy CSS. Dodano `.env.example` i ignorowaną konfigurację lokalną z wygenerowanym sekretem. Kontrole Django dla trzech środowisk, 17 testów ustawień i szkieletu oraz izolowane kontrole Ruff zakończyły się sukcesem. Nie uruchamiano migracji i nie powstała lokalna baza. Szczegóły: [wyniki weryfikacji](../../docs/verification.md#t002-szkielet-django-i-konfiguracja-środowisk).

### T003 Własny użytkownik i pierwsza migracja

- [x] Zaimplementować `User`, role i ograniczenia danych przed utworzeniem tabel uwierzytelniania.

**Zakres:** zbudować model na `AbstractUser` z polami opisanymi w planie, ustawić `AUTH_USER_MODEL`, dodać unikalny `login_key` wyliczany przez `strip().casefold()`, stany poświadczeń i wersję sesji. Zabezpieczyć relację loginu `ADMIN` do roli Administrator. Nie przyznawać tej roli innym kontom ani ustawiać `is_superuser=True`. W adresach aplikacji nie udostępniać Django Admin.

**Zależności:** T002.  
**Wymagania:** AUTH-04, ADMIN-03, ADMIN-07, TECH-02.  
**Gotowe, gdy:** migracje działają na pustej bazie; testy potwierdzają unikalność loginu także dla różnych wielkości liter, niezmienność zarezerwowanej tożsamości i brak uprzywilejowania frameworkowego konta `ADMIN`.

**Wykonano 2026-10-25:** dodano `accounts.User`, pięć ról, klucz loginu, tryby poświadczeń, wersję sesji i pola cyklu życia konta. Ustawiono `AUTH_USER_MODEL` przed zastosowaniem pierwszej migracji. Model, manager i ograniczenia bazy chronią konto `ADMIN` oraz odrzucają uprawnienia frameworka. Login pozostaje niezmienny także przy operacjach zbiorczych ORM. Migrację `accounts.0001_initial` zastosowano do pustej lokalnej bazy; powstała tabela `accounts_user`, bez `auth_user` i bez kont demonstracyjnych. Pełny zestaw 53 testów, kontrole Ruff, Django i zgodności migracji zakończyły się sukcesem. Szczegóły: [wyniki weryfikacji](../../docs/verification.md#t003-własny-użytkownik-i-pierwsza-migracja).

### T004 Podstawa testów i automatycznych kontroli

- [x] Przygotować konfigurację pytest, Ruff i początkowy workflow CI.

**Zakres:** dodać `tests/conftest.py`, fabryki kont testowych, kontrolowany zegar i konfigurację testów Django. Uruchamiać rzeczywisty Argon2id. Skonfigurować CI do odtworzenia zależności, kontroli stylu, sprawdzenia Django, brakujących migracji i istniejących testów.

**Zależności:** T003.  
**Wymagania:** PASS-02, TECH-07, TECH-08.  
**Gotowe, gdy:** lokalne kontrole i workflow mają te same polecenia, podstawowe testy modelu przechodzą, a testy nie korzystają z lokalnej bazy ani rzeczywistych sekretów.

**Wykonano 2026-10-25:** dodano konfigurację pytest i Ruff w `pyproject.toml`, fabryki kont, fixture administratora i kontrolowany zegar w `tests/conftest.py`. Istniejące testy modelu korzystają ze wspólnych fixtures. Dodano politykę końców linii oraz workflow GitHub Actions dla Windows i Linux, z przypiętym Pythonem, uv i akcjami. Wszystkie 53 testy i lokalne odpowiedniki kontroli CI przeszły; lokalna baza pozostała niezmieniona. Workflow zweryfikowano przez actionlint. Pierwsze wykonanie na GitHubie nastąpi po osobnym pushu. Szczegóły: [wyniki weryfikacji](../../docs/verification.md#t004-podstawa-testów-i-automatycznych-kontroli).

**Zakończenie E1:** ukończono 2026-10-25. Aplikacja ma poprawną konfigurację, własnego użytkownika, powtarzalne środowisko i działające lokalnie podstawowe kontrole; workflow CI jest przygotowany do wykonania na GitHubie.

## 3. E2 Dane i reguły bezpieczeństwa

### T005 Ustawienia bezpieczeństwa i stałe polityki

- [x] Dodać `SecuritySettings`, stałe oraz migrację danych początkowych.

**Zakres:** domyślnie włączyć regułę Levenshteina, ustawić ważność hasła stałego na `0` i limit bezczynności na 15 minut. Zdefiniować stałe: długość hasła 14, odległość 4, historia 5, długość hasła tymczasowego 16 i ważność 4 godziny. Walidować całkowite, nieujemne dni i dodatnie minuty. Odczyt nie może korzystać z trwałego cache opóźniającego zastosowanie zmiany.

**Zależności:** T004.  
**Wymagania:** EXP-01, EXP-02, EXP-04, CONF-01, CONF-02, CONF-03, CONF-04, CONF-05.  
**Gotowe, gdy:** migracja tworzy jeden rekord ustawień, wartości błędne są odrzucane, a zmiana ustawień jest widoczna przy kolejnym odczycie.

**Wykonano 2026-10-26:** dodano model `SecuritySettings` ze stałym identyfikatorem `1`, ustawieniami domyślnymi i datą modyfikacji, nazwane stałe polityki oraz selektor odczytujący aktualne ustawienia bez cache. Migracje `security.0001_initial` i `security.0002_initial_settings` tworzą tabelę i pojedynczy rekord początkowy. Walidacja i ograniczenia bazy odrzucają niepoprawne zakresy oraz wartości ułamkowe, a ograniczenie identyfikatora uniemożliwia dodanie drugiego rekordu. Dodano 30 testów; pełny zestaw 83 testów i kontrole Ruff, Django oraz zgodności migracji przeszły. Migracje zastosowano również w lokalnej bazie. Szczegóły: [wyniki weryfikacji](../../docs/verification.md#t005-ustawienia-bezpieczeństwa-i-stałe-polityki).

### T006 Historia i poświadczenia tymczasowe

- [x] Zaimplementować modele `PasswordHistory` i `TemporaryCredential`.

**Zakres:** dodać pola, relacje i ograniczenia opisane w planie. Rozdzielić hash hasła stałego od poświadczenia tymczasowego. Uwzględnić terminy wydania, wygaśnięcia, zużycia i unieważnienia oraz wersję poświadczenia.

**Zależności:** T005.  
**Wymagania:** PASS-01, PASS-09, TEMP-01, TEMP-06, TEMP-07.  
**Gotowe, gdy:** migracje działają od pustej bazy, poświadczenia zawierają wyłącznie hashe, a model pozwala zachować historię podczas wielokrotnych resetów.

**Wykonano 2026-10-26:** dodano `PasswordHistory` z hashem wycofanego hasła stałego i czasem zastąpienia oraz `TemporaryCredential` z osobnym hashem, terminami wydania, wygaśnięcia, zużycia i unieważnienia oraz wersją poświadczenia. Pole hasha odrzuca jawne hasła i niepoprawne kodowanie Argon2id także przy zwykłych zapisach zbiorczych ORM. Relacje chronią rekordy przed kaskadowym usunięciem konta; ograniczenia zapewniają dodatnią wersję, unikalność wersji dla konta oraz spójne terminy. Migrację `security.0003_passwordhistory_temporarycredential` zweryfikowano w testach i zastosowano lokalnie. Dodano 25 testów; pełny zestaw 108 testów, Ruff, kontrola Django i zgodności migracji przeszły. Serwisy resetu i przycinania historii pozostają w T009–T011. Szczegóły: [wyniki weryfikacji](../../docs/verification.md#t006-historia-i-poświadczenia-tymczasowe).

### T007 Walidacja haseł i konfiguracja Argon2id

- [x] Przygotować wspólne sprawdzanie hasła stałego i historii.

**Zakres:** skonfigurować hasher, minimalną długość, zgodność dwóch pól, poprawność starego sekretu, listę popularnych haseł oraz weryfikację kandydata względem hasha bieżącego i pięciu poprzednich haseł stałych. Hasła porównywać bez usuwania spacji i normalizacji; nie narzucać klas znaków.

**Zależności:** T006.  
**Wymagania:** AUTH-04, PASS-01, PASS-02, PASS-03, PASS-04, PASS-05, PASS-08, PASS-09, PASS-10.  
**Kryteria:** AC-04, AC-05, AC-06, AC-07, AC-11, AC-28.  
**Gotowe, gdy:** testy sprawdzają granicę 13/14 znaków, niezgodne potwierdzenie, błędne stare hasło, popularne hasło i historię; rzeczywisty zapis używa Argon2id z solą.

**Wykonano 2026-10-26:** wspólny walidator i 8 przypadków testowych; pełny zestaw 116 testów oraz Ruff, Django i kontrola migracji przeszły. Szczegóły: [weryfikacja T007](../../docs/verification.md#t007-walidacja-haseł-i-konfiguracja-argon2id).

### T008 Reguła odległości Levenshteina

- [x] Dodać czystą funkcję obliczającą odległość i włączyć ją do walidacji.

**Zakres:** przyjąć koszt 1 dla wstawienia, usunięcia i zamiany. Sprawdzać próg 4 tylko przy włączonej regule. Uwzględnić spacje, polskie znaki, wielkość liter i puste ciągi w testach funkcji. Nie porównywać nowych haseł z samymi hashami.

**Zależności:** T007.  
**Wymagania:** PASS-06, PASS-07, PASS-11, CONF-05.  
**Kryteria:** AC-08, AC-09, AC-10.  
**Gotowe, gdy:** odległość 3 odrzuca zmianę, odległość 4 przechodzi tę regułę, a wyłączenie kontroli nie wyłącza pozostałych walidatorów.

**Wykonano 2026-10-26:** funkcja Levenshteina i integracja z aktualnymi ustawieniami; 13 nowych przypadków testowych, w tym granice 3/4, Unicode, spacje i przełączanie reguły. Pełny zestaw 129 testów oraz Ruff, Django i kontrola migracji przeszły. Szczegóły: [weryfikacja T008](../../docs/verification.md#t008-reguła-odległości-levenshteina).

### T009 Generowanie i resetowanie hasła tymczasowego

- [x] Zaimplementować serwis wydawania poświadczenia tymczasowego.

**Zakres:** generować 16 znaków alfanumerycznych przez `secrets`, zapisywać hash z ważnością 4 godzin, atomowo unieważniać starsze poświadczenia i zwiększać `session_version`. Reset przełącza konto w tryb `TEMPORARY`, zachowuje hash ostatniego hasła stałego i historię, ale blokuje logowanie tym hasłem. Jawny sekret zwracać tylko wywołującemu w celu jednorazowej prezentacji.

**Zależności:** T008.  
**Wymagania:** TEMP-01, TEMP-02, TEMP-06, TEMP-07, TEMP-09, TECH-03, TECH-05.  
**Kryteria:** AC-11, AC-12, AC-13, AC-16, AC-28.  
**Gotowe, gdy:** testy potwierdzają format, terminy i zachowanie historii, a stare hasło i wcześniejsze poświadczenie nie zapewniają dostępu po resecie.

**Wykonano 2026-10-26:** serwis `issue_temporary_credential`, kontrole aktualnych poświadczeń i testy resetu, granicy czasu oraz rollbacku. Jawny sekret istnieje tylko w wyniku operacji, bez zapisu i prezentacji w repr/logach. Pełny zestaw 134 testów oraz Ruff, Django i kontrola migracji przeszły. Szczegóły: [weryfikacja T009](../../docs/verification.md#t009-generowanie-i-resetowanie-hasła-tymczasowego).

### T010 Transakcyjna zmiana hasła

- [x] Zaimplementować wspólny serwis ustawiania nowego hasła stałego.

**Zakres:** obsłużyć zmianę dobrowolną, pierwsze logowanie, hasło wygasłe i reset. W jednej transakcji aktualizować hash, historię, czas, tryb poświadczeń i wersję sesji oraz unieważniać poświadczenia tymczasowe. Przy resecie porównywać odległość z podanym hasłem tymczasowym; hasła stałe sprawdzać przez historię. Nie zapisywać starego sekretu w sesji.

**Zależności:** T009.  
**Wymagania:** PASS-04, PASS-05, PASS-09, PASS-12, TEMP-03, TEMP-08, TEMP-09, EXP-03, SESS-05.  
**Kryteria:** AC-04, AC-06, AC-07, AC-11, AC-15, AC-28.  
**Gotowe, gdy:** sukces aktualizuje wszystkie dane spójnie; odrzucenie i wymuszony błąd zapisu nie pozostawiają częściowych zmian; historia mieści pięć poprzednich haseł stałych.

**Wykonano 2026-10-26:** wspólny serwis `change_password` dla czterech kontekstów, transakcyjny zapis i historia pięciu poprzednich haseł. 12 nowych testów, pełny zestaw 146 testów oraz kontrole Ruff, Django i migracji przeszły. Szczegóły: [weryfikacja T010](../../docs/verification.md#t010-transakcyjna-zmiana-hasła).

### T011 Jednorazowe zużycie i kontrola współbieżności

- [x] Zaimplementować atomowe zużycie poświadczenia i ochronę przed nadpisaniem nowszego stanu.

**Zakres:** warunkowo oznaczać hasło jako zużyte tylko przy właściwej wersji konta i czasie przed terminem. Sprawdzać liczbę zmienionych rekordów. W zapisach opartych na wcześniejszej walidacji ponownie potwierdzać wersję konta i dane źródłowe. Obsługiwać konflikt lub blokadę bazy bez przyznawania dostępu i bez częściowego zapisu. Nie polegać na `select_for_update()` w SQLite.

**Zależności:** T010.  
**Wymagania:** PASS-12, TEMP-04, TEMP-06, TEMP-07.  
**Kryteria:** AC-13, AC-14, AC-16.  
**Gotowe, gdy:** test na osobnych połączeniach plikowej bazy pozwala najwyżej jednej próbie zużyć hasło, a reset kolidujący ze zmianą lub użyciem poświadczenia nie zostaje nadpisany starszym stanem.

**Wykonano 2026-10-26:** atomowe zużycie poświadczenia, kontrola liczby zapisów, ponowne sprawdzanie danych źródłowych i obsługa konfliktów/blokad przez `SecurityConflict`. Dodano 14 przypadków testowych, w tym rzeczywiste wyścigi na osobnych połączeniach plikowej bazy oraz test odzyskania ADMIN przed pierwszym hasłem stałym. Szczegóły i wyniki kontroli: [weryfikacja T011](../../docs/verification.md#t011-jednorazowe-zużycie-i-kontrola-współbieżności).

**Zakończenie E2:** reguły i operacje bezpieczeństwa są dostępne jako wspólne serwisy i przechodzą testy przed podłączeniem ich do interfejsu.

**E2 ukończono 2026-10-26:** T005–T011 są zaimplementowane i zweryfikowane. Końcowy pełny zestaw: 160 testów, poprawne kontrole Ruff, Django i zgodności migracji. Następny etap to E3, rozpoczynający się od T012.

## 4. E3 Logowanie i sesje

### T012 Logowanie i rozpoznanie trybu poświadczeń

- [x] Zaimplementować formularz logowania i backend uwierzytelniania.

**Zakres:** używać `login_key`, maskować hasło i zwracać dokładnie „Login lub hasło niepoprawne” dla wszystkich przyczyn odmowy opisanych w specyfikacji. Rozróżniać poświadczenia `INITIAL`, `TEMPORARY` i `PERMANENT`. Nie pozostawiać domyślnego backendu pozwalającego ominąć reguły projektu. Nieistniejący login także wywołuje kosztowną weryfikację zastępczą.

**Zależności:** T011.  
**Wymagania:** AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-05.  
**Kryteria:** AC-01, AC-02.  
**Gotowe, gdy:** testy rozróżniają sukces i porażkę bez ujawniania przyczyny odmowy, a konto zablokowane, usunięte lub w niewłaściwym trybie nie otrzymuje dostępu.

**Wykonano 2026-10-28:** formularz `/login/`, klasyfikacja poświadczeń i własny backend bez domyślnej ścieżki awaryjnej. 11 nowych testów, pełna weryfikacja i szczegóły w [wynikach T012](../../docs/verification.md#t012-logowanie-i-rozpoznanie-trybu-poświadczeń). Podłączenie kontekstów sesji następuje w T013.

### T013 Pełna i ograniczona sesja

- [ ] Podłączyć wynik logowania do właściwego kontekstu sesji.

**Zakres:** pełne logowanie wykonywać mechanizmem Django. Dla pierwszego logowania, resetu i wygaśnięcia tworzyć ograniczony kontekst bez zwykłego `login()` i bez uwierzytelnionego użytkownika Django. Zapisywać tylko niezbędne identyfikatory, wersję, powód i czasy. Obracać klucz sesji i udostępniać ograniczonemu kontekstowi wyłącznie zmianę hasła oraz wylogowanie.

**Zależności:** T012.  
**Wymagania:** AUTH-05, TEMP-03, TEMP-04, TEMP-05, EXP-03, SESS-06.  
**Kryteria:** AC-02, AC-03, AC-14, AC-28.  
**Gotowe, gdy:** testy bezpośrednich adresów nie pozwalają ograniczonej sesji wejść na pulpit ani do panelu kont; jedynie udane zużycie poświadczenia tymczasowego może nadać właściwy ograniczony kontekst.

### T014 Formularze zmiany hasła

- [ ] Zbudować zwykłą i wymuszoną zmianę hasła na wspólnym serwisie.

**Zakres:** formularze pokazują aktywne zasady i konkretne błędy walidacji. W ograniczonej sesji po resecie ponownie wymagają podania hasła tymczasowego. Po sukcesie zamykają bieżącą sesję i kierują do logowania; pozostałe sesje tracą dostęp przez zmianę wersji konta.

**Zależności:** T013.  
**Wymagania:** AUTH-06, PASS-04, PASS-05, TEMP-03, TEMP-08, EXP-03, SESS-05, UI-04.  
**Kryteria:** AC-04, AC-05, AC-06, AC-07, AC-08, AC-09, AC-10, AC-11, AC-15.  
**Gotowe, gdy:** każda ścieżka zmiany działa przez HTTP, odrzucenie zachowuje stan, a po sukcesie nowy sekret działa dopiero w ponownym logowaniu.

### T015 Middleware bezpieczeństwa i terminy

- [ ] Sprawdzać aktualny stan konta, wersję sesji, bezczynność i ważność haseł.

**Zakres:** middleware umieścić po obsłudze sesji i uwierzytelniania Django. Pobierać aktualne ustawienia; kontrolować termin przed odnowieniem aktywności. Obsłużyć granicę `teraz >= termin`, wartość `0` ważności hasła i wcześniejszy z terminów ograniczonej sesji. Pełną sesję z wygasłym hasłem przełączać na ograniczony dostęp. Nie przedłużać sesji żądaniami zasobów statycznych lub automatycznym odpytywaniem.

**Zależności:** T014.  
**Wymagania:** TEMP-05, EXP-01, EXP-02, EXP-03, EXP-04, CONF-04, SESS-02, SESS-03, SESS-04, TECH-08.  
**Kryteria:** AC-13, AC-21, AC-24, AC-25, AC-26, AC-27.  
**Gotowe, gdy:** kontrolowany zegar potwierdza zachowanie przed granicą, na granicy i po niej; skrócenie ustawień obowiązuje w już istniejącej sesji przy kolejnym żądaniu.

### T016 Wylogowanie i zabezpieczenia sesji

- [ ] Dodać wylogowanie, nagłówki oraz ochronę wrażliwych danych.

**Zakres:** wylogowanie przez POST z CSRF działa dla obu kontekstów i usuwa sesję po stronie serwera. Ustawić `HttpOnly`, `SameSite=Lax`, `Secure` w konfiguracji HTTPS oraz `no-store` na widokach chronionych i prezentujących sekret. Oznaczyć dane wrażliwe w raportowaniu błędów; nie zapisywać ich w loggerze, komunikatach sesyjnych ani adresach URL.

**Zależności:** T015.  
**Wymagania:** SESS-01, SESS-05, SESS-06, SESS-07, TECH-03, TECH-05, TECH-09.  
**Kryteria:** AC-23, AC-28, AC-29.  
**Gotowe, gdy:** stare ciasteczko nie przywraca wylogowanej sesji, GET nie wylogowuje, brak CSRF blokuje operację, a testy nagłówków i logów nie wykazują zapisu sekretów.

**Zakończenie E3:** da się przejść pierwsze logowanie, zmianę, reset, wygaśnięcie i wylogowanie; żaden ograniczony kontekst nie zapewnia pełnego dostępu.

## 5. E4 Konta i panel bezpieczeństwa

### T017 Inicjalizacja i odzyskiwanie konta ADMIN

- [ ] Dodać komendy `init_admin` i `recover_admin`.

**Zakres:** inicjalizacja pobiera hasło dwukrotnie przez ukryty prompt, waliduje je, zapisuje hash w trybie `INITIAL` i wymusza zmianę. Nie nadpisuje istniejącego konta. Odzyskiwanie wymaga lokalnego potwierdzenia, korzysta z serwisu resetu i pokazuje nowy sekret raz w terminalu. Nie przyjmuje hasła jako argumentu polecenia.

**Zależności:** T016.  
**Wymagania:** ADMIN-07, ADMIN-08, ADMIN-09, TECH-05, TECH-07.  
**Kryteria:** AC-03, AC-15, AC-16, AC-22.  
**Gotowe, gdy:** testy komend sprawdzają inicjalizację, ponowne wykonanie i odzyskiwanie, a pierwsze logowanie `ADMIN` nie omija wymuszonej zmiany hasła.

### T018 Serwisy zarządzania kontami

- [ ] Dodać tworzenie, edycję, blokadę, odblokowanie i logiczne usunięcie konta.

**Zakres:** tworzenie wydaje hasło tymczasowe; zmiana roli, blokada i usunięcie zwiększają wersję sesji. Zachować login po utworzeniu i po usunięciu. Wykluczyć usunięte konta z aktywnej listy. Chronić `ADMIN` także przy bezpośrednim wywołaniu serwisu. Odblokowanie nie reaktywuje starych sesji.

**Zależności:** T017.  
**Wymagania:** ADMIN-01, ADMIN-03, ADMIN-04, ADMIN-05, ADMIN-06, ADMIN-07.  
**Kryteria:** AC-12, AC-21, AC-22.  
**Gotowe, gdy:** testy serwisów oraz kilku sesji potwierdzają skutki zmian, zachowanie zarezerwowanego loginu i ochronę konta `ADMIN`.

### T019 Lista kont i formularze administracyjne

- [ ] Zbudować panel listy, tworzenia i edycji kont.

**Zakres:** widoki dopuszczają wyłącznie Administratora. Lista pokazuje login, imię, nazwisko, rolę i stan, bez hashy. Formularze mają jawne listy pól; nie przyjmują klientowskich wartości wersji sesji, hashy, uprawnień frameworka ani niedozwolonej roli.

**Zależności:** T018.  
**Wymagania:** ADMIN-01, ADMIN-02, ADMIN-03, ADMIN-07, RBAC-01, RBAC-02, RBAC-03, UI-02.  
**Kryteria:** AC-12, AC-21, AC-22, AC-28.  
**Gotowe, gdy:** operacje działają przez formularze, pozostałe role otrzymują 403, a podmienione lub dodatkowe pola nie zmieniają chronionych danych.

### T020 Potwierdzanie operacji i jednorazowa prezentacja hasła

- [ ] Podłączyć akcje blokady, odblokowania, usunięcia i resetu.

**Zakres:** stosować POST z CSRF i czytelne potwierdzenie dotyczące konkretnego konta. Po utworzeniu lub resecie pokazać wygenerowane hasło jednorazowo w odpowiedzi bez cache; nie używać przechowywania sekretu w sesji ani systemie komunikatów. Wyjaśnić wymóg pierwszej zmiany i ważność 4 godzin.

**Zależności:** T019.  
**Wymagania:** TEMP-02, TEMP-07, ADMIN-01, ADMIN-04, ADMIN-06, UI-05, TECH-03, TECH-05.  
**Kryteria:** AC-12, AC-16, AC-21, AC-22, AC-28, AC-29.  
**Gotowe, gdy:** odświeżenie listy nie pozwala odczytać wydanego hasła, akcje GET nie zmieniają danych, a brak uprawnień lub CSRF pozostawia konto bez zmian.

### T021 Panel ustawień bezpieczeństwa

- [ ] Udostępnić Administratorowi edycję trzech ustawień bezpieczeństwa.

**Zakres:** obsłużyć przełącznik Levenshteina, ważność hasła w dniach i bezczynność w minutach. Wyświetlić stałe zasady polityki bez możliwości ich edycji. Pokazać błędy walidacji i zapisać zmiany przez wspólny serwis. Nie modyfikować historycznych dat użytkowników.

**Zależności:** T020.  
**Wymagania:** EXP-01, EXP-02, CONF-01, CONF-02, CONF-03, CONF-04, CONF-05, UI-02.  
**Kryteria:** AC-10, AC-26, AC-27, AC-29.  
**Gotowe, gdy:** uprawnione zmiany działają od następnego żądania, niepoprawne wartości i inne role są odrzucane, a włączenie odległości nie próbuje analizować istniejących hashy.

**Zakończenie E4:** konto `ADMIN` można zainicjalizować i odzyskać lokalnie; panel realizuje cały cykl zarządzania kontami i ustawieniami.

## 6. E5 Dokumenty i kontrola dostępu

### T022 Model dokumentu

- [ ] Dodać model `Document` i jego migrację.

**Zakres:** tytuł, treść tekstowa, autor, stan `DRAFT` lub `PUBLISHED` oraz daty. Nowe dokumenty są szkicami. Chronić relację autora przed fizycznym usunięciem i nie dodawać operacji usuwania dokumentów.

**Zależności:** T021.  
**Wymagania:** DOC-01, ADMIN-06, TECH-02.  
**Gotowe, gdy:** model i migracja działają, stan nowego dokumentu jest poprawny, a logiczne usunięcie autora zachowuje dokument i relację autorstwa.

### T023 Jawne polityki operacji

- [ ] Zaimplementować macierz pięciu ról w `documents/policies.py`.

**Zakres:** sprawdzać rolę, stan dokumentu i własność; domyślnie odmawiać. Nie nadawać Administratorowi dostępu do szkiców. Pracownik operuje na własnych szkicach, Redaktor na wszystkich szkicach, Kierownik także publikuje i wycofuje. Nie używać grup lub flag superużytkownika jako alternatywnego źródła uprawnień.

**Zależności:** T022.  
**Wymagania:** RBAC-01, RBAC-02, RBAC-04, DOC-02; macierz specyfikacji 4.1.  
**Kryteria:** AC-17, AC-18, AC-19, AC-20.  
**Gotowe, gdy:** parametryzowane testy polityk obejmują każdą rolę, stan, własność i dostępną operację, w tym przypadki odmowy.

### T024 Listy, szczegóły i odpowiedzi błędów

- [ ] Dodać selektory i widoki odczytu dokumentów.

**Zakres:** filtrować listy po stronie serwera; szczegóły istniejącego niedostępnego dokumentu zwracają 403, a nieistniejącego 404. Anonimowy dostęp kierować do logowania z bezpiecznym lokalnym adresem powrotu. Nie ujawniać tytułu ani treści niedozwolonego szkicu w liście lub odpowiedzi błędu.

**Zależności:** T023.  
**Wymagania:** RBAC-02, RBAC-03, RBAC-04, DOC-02, UI-02.  
**Kryteria:** AC-18, AC-20.  
**Gotowe, gdy:** testy list i bezpośrednich adresów potwierdzają widoczność treści, różnicę 403/404 oraz brak dostępu przez sesję ograniczoną.

### T025 Tworzenie, edycja i publikacja

- [ ] Zaimplementować formularze i serwisy zapisu dokumentów.

**Zakres:** autora ustalać z sesji; nie przyjmować jego identyfikatora ani stanu z formularza szkicu. Weryfikować uprawnienie i aktualny stan także w serwisie. Opublikowanego dokumentu nie można edytować przed wycofaniem. Publikacja i wycofanie są osobnymi operacjami POST dostępnymi Kierownikowi.

**Zależności:** T024.  
**Wymagania:** RBAC-01, RBAC-02, RBAC-04, DOC-01, DOC-02, TECH-03, TECH-04.  
**Kryteria:** AC-17, AC-18, AC-19, AC-20, AC-29, AC-30.  
**Gotowe, gdy:** dozwolony zapis działa, a podmiana identyfikatora, autora, stanu, metody żądania lub roli nie pozwala zmienić niedostępnych danych.

### T026 Integracyjna weryfikacja macierzy ról

- [ ] Przełożyć macierz polityk na parametryzowane żądania HTTP.

**Zakres:** sprawdzić listy, szczegóły, tworzenie, edycję, publikację i wycofanie dla wszystkich ról. Dodać przypadki kont zablokowanych i ograniczonych sesji. Potwierdzić, że usunięcie przycisku nie jest jedyną kontrolą operacji, oraz że odpowiedź 403 nie zmienia danych.

**Zależności:** T025.  
**Wymagania:** RBAC-01, RBAC-02, RBAC-03, RBAC-04, DOC-02.  
**Kryteria:** AC-17, AC-18, AC-19, AC-20, AC-21.  
**Gotowe, gdy:** testy rzeczywistych adresów i metod HTTP pokrywają całą macierz i przechodzą bez omijania middleware lub serwisów.

**Zakończenie E5:** moduł dokumentów demonstruje wszystkie role i sprawdza dostęp po stronie serwera, również przy bezpośrednich żądaniach.

## 7. E6 Interfejs i demonstracja

### T027 Wspólny układ i styl interfejsu

- [ ] Ujednolicić szablony, nawigację i zasoby CSS.

**Zakres:** przygotować wspólny układ, typografię, odstępy, kolory, przyciski, pola i tabele. Pulpit oraz nawigacja pokazują funkcje dostępne danej roli. Obsłużyć szeroki i wąski ekran oraz stany pustych list. W interfejsie używać nazw operacji i konkretnych reguł bezpieczeństwa aplikacji.

**Zależności:** T026.  
**Wymagania:** UI-01, UI-02, DOC-02.  
**Gotowe, gdy:** wszystkie widoki korzystają ze spójnych komponentów, tabele i formularze są czytelne na telefonie, a nawigacja zgadza się z uprawnieniami.

### T028 Dostępność, błędy i potwierdzenia

- [ ] Dopracować formularze i strony 403/404.

**Zakres:** dodać jednoznaczne etykiety, widoczny fokus, obsługę klawiaturą, tekstowe błędy przy polach i opis aktywnej polityki. Komunikaty nie polegają wyłącznie na kolorze. Potwierdzenia wskazują konto i skutek operacji. Zachować ogólny błąd logowania i maskowanie sekretów.

**Zależności:** T027.  
**Wymagania:** AUTH-01, AUTH-02, UI-01, UI-02, UI-03, UI-04, UI-05.  
**Gotowe, gdy:** formularze można obsłużyć klawiaturą, błędy są zrozumiałe i przypisane do pól, a odmowa dostępu nie ujawnia chronionej treści.

### T029 Dane demonstracyjne

- [ ] Dodać `seed_demo` i jawną opcję `--reset-passwords`.

**Zakres:** lokalnie tworzyć 1 Kierownika, 1 Redaktora, 2 Pracowników i 2 Czytelników poza `ADMIN`, a także opublikowany dokument i szkice różnych autorów. Wykorzystywać serwisy kont i haseł, generować poświadczenia przy wykonaniu i pokazywać nowe sekrety raz w terminalu. Ponowne wykonanie nie duplikuje danych i nie zmienia istniejących haseł bez jawnej opcji. Nie modyfikować `ADMIN`.

**Zależności:** T028.  
**Wymagania:** TEMP-01, TEMP-02, TECH-05, TECH-07; dane demonstracyjne specyfikacji 8.  
**Kryteria:** AC-12, AC-28, AC-31.  
**Gotowe, gdy:** testy komendy potwierdzają liczbę i role kont, autorstwo szkiców, powtarzalność wykonania oraz reset wyłącznie przy jawnej opcji.

### T030 Przegląd w przeglądarce

- [ ] Sprawdzić kompletne ścieżki na komputerze i wąskim ekranie.

**Zakres:** jako `ADMIN` utworzyć i zresetować konto; jako użytkownik przejść pierwsze logowanie, odrzucenie niepoprawnego hasła i jego poprawną zmianę. Sprawdzić pracę każdej roli, publikację i odmowę dostępu, wylogowanie oraz timeout. Wprowadzić tekst zawierający znacznik skryptu i sprawdzić, że pozostaje tekstem. Zweryfikować klawiaturę i wygląd stron błędów.

**Zależności:** T029.  
**Wymagania:** UI-01, UI-02, UI-03, UI-04, UI-05, TECH-04.  
**Kryteria:** AC-03, AC-15, AC-17, AC-19, AC-23, AC-24, AC-30.  
**Gotowe, gdy:** wyniki ręcznej weryfikacji i wykryte poprawki są zapisane w `docs/verification.md`; poprawki zostały ponownie sprawdzone, a materiały weryfikacyjne nie zawierają sekretów.

**Zakończenie E6:** funkcje mają spójny, dostępny interfejs i mogą zostać zademonstrowane na przygotowanych kontach.

## 8. E7 Odbiór i dokumentacja

### T031 Przekrojowa weryfikacja bezpieczeństwa

- [ ] Uzupełnić brakujące testy integracyjne bez powielania istniejących przypadków.

**Zakres:** przejrzeć dotychczasowe pokrycie; uzupełnić scenariusze kilku klientów, ochronę CSRF z wymuszoną kontrolą w kliencie testowym, nagłówki cache, escapowanie i brak jawnych sekretów w sesjach oraz logach. Sprawdzić, że reset nie usuwa historii, wyłączenie reguły odległości nie wyłącza innych zasad, a zmiana ustawień dotyczy już zalogowanych kont.

**Zależności:** T030.  
**Wymagania:** PASS-09, PASS-11, TEMP-07, CONF-04, SESS-01, SESS-05, TECH-03, TECH-04, TECH-05.  
**Kryteria:** AC-10, AC-11, AC-16, AC-21, AC-23, AC-26, AC-28, AC-29, AC-30.  
**Gotowe, gdy:** komplet testów odpowiada kryteriom bez pominięcia kontroli dostępu i konfiguracji rzeczywistego hashera; testy nie wymagają ręcznego przygotowania lokalnej bazy.

### T032 Odbiór granic czasu i współbieżności

- [ ] Zweryfikować istniejące testy równoczesnych operacji i terminów w pełnym przepływie.

**Zakres:** potwierdzić jednorazowość przez osobne połączenia plikowej bazy oraz brak dostępu po resecie kolidującym z logowaniem lub zmianą hasła. Przejrzeć testy granic ważności i bezczynności, utraty ograniczonej sesji oraz skutków błędu blokady. Uzupełnić wyłącznie brakujące przypadki.

**Zależności:** T031.  
**Wymagania:** PASS-12, TEMP-05, TEMP-06, TEMP-07, EXP-03, SESS-02, SESS-03, SESS-04.  
**Kryteria:** AC-13, AC-14, AC-16, AC-24, AC-25, AC-26, AC-27.  
**Gotowe, gdy:** testy używają kontrolowanego czasu i rzeczywiście odrębnych połączeń, kończą się bez oczekiwania na upływ godzin i wykazują brak częściowych zapisów lub drugiej skutecznej próby użycia sekretu.

### T033 Końcowa konfiguracja CI

- [ ] Doprowadzić workflow do uruchamiania wszystkich wymaganych kontroli.

**Zakres:** synchronizować zależności z pliku blokady; uruchamiać Ruff, kontrolę Django, brakujących migracji oraz pełny pytest, w tym testy współbieżności. Utrzymać tę samą serię Pythona i ustawienia hashera lokalnie i w CI. Wyniki nie mogą zawierać prawdziwych sekretów.

**Zależności:** T032.  
**Wymagania:** TECH-05, TECH-06, TECH-07.  
**Kryteria:** AC-28, AC-31.  
**Gotowe, gdy:** te same kontrole przechodzą lokalnie, workflow nie pomija żadnej wymaganej grupy testów i jest gotowy do wykonania po publikacji repozytorium. Wynik zdalny sprawdzimy dopiero po osobno zleconej publikacji.

### T034 README i decyzje techniczne

- [ ] Opisać uruchomienie, testy i najważniejsze rozwiązania bezpieczeństwa.

**Zakres:** README zawiera cel, stos, konfigurację środowiska, migracje, inicjalizację i odzyskiwanie `ADMIN`, dane demonstracyjne, role, testy oraz odnośniki do dokumentów SDD. W `docs/decisions/` opisać ograniczone sesje, unieważnianie przez wersję konta, historię po resecie i brak dziedziczenia uprawnień superużytkownika. Zaznaczyć, że dane demonstracyjne są lokalne, a utrata ograniczonej sesji po użyciu hasła tymczasowego wymaga resetu.

**Zależności:** T033.  
**Wymagania:** TECH-02, TECH-06, TECH-07, TECH-09.  
**Kryteria:** AC-31.  
**Gotowe, gdy:** instrukcja opisuje rzeczywiste, sprawdzone polecenia i nie wymaga wartości zaszytych w kodzie; specyfikacja, plan i zadania opisują aktualny stan projektu.

### T035 Odtworzenie środowiska i zamknięcie odbioru

- [ ] Wykonać odbiór pierwszej wersji z czystej kopii projektu.

**Zakres:** zgodnie z README odtworzyć środowisko, utworzyć pustą bazę, zastosować migracje, zainicjalizować `ADMIN`, przygotować demonstrację i uruchomić kontrole. Przejrzeć pliki przeznaczone do wersjonowania pod kątem sekretów, baz i artefaktów. W `docs/verification.md` zapisać wynik każdego AC-01–AC-31, odwołanie do testu lub procedury ręcznej oraz końcowe ograniczenia. Przy braku wyniku pozostawić dane kryterium nieodebrane.

**Zależności:** T034.  
**Wymagania:** TECH-06, TECH-07; definicja ukończenia specyfikacji 11.  
**Kryteria:** AC-01, AC-02, AC-03, AC-04, AC-05, AC-06, AC-07, AC-08, AC-09, AC-10, AC-11, AC-12, AC-13, AC-14, AC-15, AC-16, AC-17, AC-18, AC-19, AC-20, AC-21, AC-22, AC-23, AC-24, AC-25, AC-26, AC-27, AC-28, AC-29, AC-30, AC-31.  
**Gotowe, gdy:** aplikacja i testy działają z czystej kopii, wszystkie kryteria mają potwierdzony wynik, a w plikach do publikacji nie ma sekretów ani danych środowiska lokalnego. Sama publikacja pozostaje osobną czynnością.

**Zakończenie E7:** pierwsza wersja spełnia specyfikację, ma sprawdzoną instrukcję, komplet wyników odbioru i repozytorium przygotowane do publikacji.

## 9. Mapa kryteriów odbioru

Poniższa mapa wskazuje zadania odpowiedzialne za implementację i weryfikację kryteriów. T035 potwierdza kompletność odbioru, ale nie zastępuje testów poszczególnych funkcji.

| Kryterium | Główne zadania |
|---|---|
| AC-01 | T012 |
| AC-02 | T012, T013 |
| AC-03 | T013, T017, T030 |
| AC-04 | T007, T010, T014 |
| AC-05 | T007, T014 |
| AC-06 | T007, T010, T014 |
| AC-07 | T007, T010, T014 |
| AC-08 | T008, T014 |
| AC-09 | T008, T014 |
| AC-10 | T008, T014, T021, T031 |
| AC-11 | T007, T009, T010, T014, T031 |
| AC-12 | T009, T018, T019, T020, T029 |
| AC-13 | T009, T011, T015, T032 |
| AC-14 | T011, T013, T032 |
| AC-15 | T010, T014, T017, T030 |
| AC-16 | T009, T011, T017, T020, T031, T032 |
| AC-17 | T023, T025, T026, T030 |
| AC-18 | T023, T024, T025, T026 |
| AC-19 | T023, T025, T026, T030 |
| AC-20 | T023, T024, T025, T026 |
| AC-21 | T015, T018, T019, T020, T026, T031 |
| AC-22 | T017, T018, T019, T020 |
| AC-23 | T016, T030, T031 |
| AC-24 | T015, T030, T032 |
| AC-25 | T015, T032 |
| AC-26 | T015, T021, T031, T032 |
| AC-27 | T015, T021, T032 |
| AC-28 | T007, T009, T010, T013, T016, T019, T020, T029, T031, T033 |
| AC-29 | T016, T020, T021, T025, T031 |
| AC-30 | T025, T030, T031 |
| AC-31 | T029, T033, T034, T035 |

## 10. Kolejny krok

E1 i E2 są ukończone. Kolejnym zadaniem jest T012 w etapie E3: formularz logowania i backend uwierzytelniania korzystający z reguł i serwisów E2. Kolejne etapy zaczynamy po spełnieniu warunku zakończenia poprzedniego etapu.
