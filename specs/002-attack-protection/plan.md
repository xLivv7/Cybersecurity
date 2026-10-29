# Plan techniczny ochrony przed botami i wyciekiem danych

Status: E9 w realizacji; ukończono T041, następne T042
Wersja: 0.2
Data: 2026-10-29
Podstawa: [specyfikacja 0.1](spec.md), [decyzje i źródła](source.md).

## 1. Stan wejściowy i sposób rozbudowy

Moduł 1 ma 35 zakończonych zadań, migracje kont, polityki bezpieczeństwa i dokumentów oraz 265 przechodzących testów. Commit bazowy: `1cf5075`. Pozostawiamy Django 5.2, Python 3.13, SQLite z transakcjami IMMEDIATE, Argon2id, szablony i istniejące reguły sesji. Nie tworzymy drugiej aplikacji ani nowego systemu uwierzytelniania.

W T037 rozdzielono walidację pól `LoginForm` od uwierzytelnienia. Usługa `attempt_login()` wykonuje weryfikację hasła poza blokadą zapisu, po czym atomowo sprawdza blokadę i snapshot poświadczeń oraz tworzy kontekst. Było to potrzebne do poprawnego wdrożenia limitu już w E8; T040 doda do istniejącej kolejności bramki CAPTCHA i honeypot. Usługi `start_session()` oraz zmiany hasła zachowują sprawdzanie aktualnego stanu konta i wersji sesji.

Plan jest realizowany od T036. Usługi zewnętrzne pozostają zakresem późniejszych etapów.

## 2. Odpowiedzialności i pliki docelowe

| Obszar | Miejsce | Odpowiedzialność |
|---|---|---|
| Stan ochrony | `apps/security/models.py`, nowe migracje | Polityka, liczniki, incydenty i kolejka sygnałów |
| Limit konta | `apps/security/login_limits.py` | Normalizacja, atomowe decyzje, czas blokady |
| CAPTCHA | `apps/security/captcha.py` | Jeden adapter Siteverify, walidacja kontraktu, brak obejść |
| Kolejność logowania | `apps/accounts/forms.py`, `views.py`, ewentualnie `login_service.py` | Bramki przed hasłem, zachowanie pełnych/ograniczonych kontekstów |
| Zmiana hasła | `apps/security/forms.py`, `views.py` | CAPTCHA przed wywołaniem usługi zmiany |
| Ustawienia ADMIN | `apps/security/settings_views.py` | Jawnie wybrane pola polityki; nadal kontrola aktora |
| Pułapki | `apps/security/canaries.py`, komenda dostarczania | Incydenty, token HTTP, kolejka i ponowienia |
| Interfejs | szablony logowania/zmiany hasła, małe skrypty w `static/js/` | Widget, odliczanie blokady, dostępność i reset po błędzie |
| Demonstracja | `scripts/simulate_bot.py`, `docs/module-2/` | Ograniczone scenariusze, wyniki, instrukcja i sprawozdanie |
| Kontrole | nowe testy `tests/security/`, `tests/accounts/` | Granice, współbieżność, zewnętrzne adaptery i regresja |

Ścieżki są planowane; nie tworzymy pustych pakietów przed potrzebującym ich zadaniem. Nowa zależność HTTP jest dopuszczalna tylko z uzasadnieniem i zmianą `pyproject.toml`/`uv.lock`; mały adapter może korzystać z biblioteki standardowej z timeoutem.

## 3. Dane i polityka

### Ustawienia

Rozszerzamy istniejący singleton `SecuritySettings` o `login_failure_limit`, domyślnie 5, dodatnia liczba całkowita. Stała `LOGIN_LOCK_SECONDS = 900` nie jest regulowana w panelu. Migracja nie zmienia kont, haseł i dotychczasowych trzech ustawień. Osobny limit IP i flaga jego włączenia powstają dopiero w zakresie dodatkowym T050–T051; domyślnie wyłączone, próg 20.

### Liczniki

`LoginAttemptState` identyfikuje klucz loginu po tej samej normalizacji co model użytkownika. Klucz jest zapisany jako HMAC-SHA256 z osobnym przeznaczeniem, aby nie przechowywać surowych nieistniejących loginów. Korzysta z klucza Django; jego rotacja resetuje korelację liczników i musi być uwzględniona w procedurze operatora. Unikalność klucza musi być wymuszona w bazie; nie polegamy na pamięci procesu. Pola: licznik błędów, `blocked_until`, ostatnia aktualizacja, wersja stanu. Stan obejmuje również nieistniejący login i nie jest flagą administracyjnej blokady konta.

Próba po końcu blokady najpierw zeruje licznik i termin. Próba w czasie blokady niczego nie przedłuża. Poprawne logowanie zeruje licznik konta; odrzucona CAPTCHA nie zapisuje błędu poświadczeń. Skrócenie progu obowiązuje przy następnym rozstrzygnięciu próby. W dodatkowym limicie IP kluczem jest niezależny, kanoniczny adres, a sukces nie kasuje jego licznika.

### Incydenty i kolejka

`SecurityEvent` zapisuje kategorię (`credential_failure`, `account_locked`, `captcha_rejected`, `honeypot`, `canary_used` i ewentualnie `ip_locked`), czas, niejawny klucz korelacji oraz bezpieczny wynik. Wartości wprowadzone w honeypot, hasła, sesje i tokeny nie trafiają do eventu. Okres retencji i komenda czyszczenia mają być jawne w instrukcji; domyślnie zdarzenia testowe przechowujemy 7 dni.

`CanaryIdentity` jest oddzielnym rejestrem zarezerwowanej nazwy, bez FK nadającego prawa użytkownika. Walidacja uniemożliwia kolizję z ADMIN i istniejącymi kontami, a tworzenie zwykłego użytkownika respektuje rezerwację. Pułapki są konfigurowane przez lokalnego operatora; nie rozbudowujemy panelu o ogólny edytor URL-i.

`CanarySignal` wiąże incydent ze statusem dostarczenia, liczbą prób i terminem ponowienia. Aktywny adres tokenu pochodzi z konfiguracji serwera, nie z danych logowania. Unikalne powiązanie z incydentem zapobiega duplikatom z ponownego zapisu. Dostarczanie zewnętrzne może być co najmniej jednokrotne; po timeoutach możliwy jest powtórny alert, co dokumentujemy zamiast deklarować gwarancję exactly-once.

## 4. Przepływ logowania i transakcje

1. CSRF i walidacja ograniczeń wejścia; normalizacja loginu bez zmiany hasła.
2. Rozpoznanie loginu-pułapki: atomowo incydent i sygnał, następnie zwykła odmowa bez kontekstu logowania. Dostarczenie odbywa się poza żądaniem.
3. Honeypot: odmowa bez hashowania i bez zapytania do dostawcy CAPTCHA.
4. Odczyt aktywnej blokady konta i ewentualnie IP: odmowa z pozostałymi sekundami. Odczyt nie odnawia terminu.
5. Siteverify poza transakcją bazy. Po każdej odmowie nowy widget/token; bez ponownego wykorzystania sukcesu.
6. Weryfikacja poświadczeń przez istniejący backend. Finalizacja w transakcji ponownie sprawdza politykę, blokadę i snapshot konta/poświadczenia. Sukces nie może ominąć blokady ustanowionej przez równoległe żądanie.
7. Atomowy zapis wyniku próby i decyzji o utworzeniu kontekstu. Używamy istniejącego `start_session()` i konsumpcji hasła tymczasowego we wspólnej granicy transakcji. Zmiana hasha, wersji konta albo poświadczenia po weryfikacji oznacza odmowę lub kontrolowane ponowienie, nigdy użycie starego wyniku.

Kosztowna weryfikacja hasha ma być poza blokadą zapisu, a jej wynik powiązany ze snapshotem. Test równoległy potwierdza brak utraty inkrementacji i brak sesji zatwierdzonej po ustanowieniu blokady. Nie wykonujemy Siteverify, pobierania tokenów ani wysyłki sieciowej podczas blokady SQLite. Nie kopiujemy reguł haseł do nowej warstwy.

## 5. Kontrakt Turnstile i konfiguracja

Jeden adapter otrzymuje token i oczekiwaną akcję. Ogranicza wielkość wejścia, wywołuje HTTPS Siteverify z kluczem serwera i krótkim timeoutem (planowane 5 sekund), sprawdza `success`, dozwolony `hostname`, właściwe `action` i strukturę odpowiedzi. Akcje: `login`, `password_change`, `password_required`. Nie przyjmuje adresu dostawcy z HTTP ani nie zapisuje pełnej odpowiedzi/tokenów do logów.

Dostawca egzekwuje termin 300 sekund i jednorazowość. Dodatkowo `CaptchaRedemption` zapisuje wyłącznie SHA-256 zaakceptowanego tokenu i jego termin, z unikalnością wymuszoną przez bazę. Atomowy zapis dopuszcza tylko jedną operację nawet przy równoległych odpowiedziach sukcesu. Wygasłe wpisy są czyszczone przy kolejnej udanej walidacji; surowych tokenów ani odpowiedzi sukcesu nie buforujemy do ponownego użycia. Adapter sprawdza też serwerowy `challenge_ts` i dokładną granicę 300 sekund. Równoległe ponowienie tego samego tokenu nie może dać dwóch autoryzacji. Timeout oznacza odmowę i nowy token; nie wykonujemy bezwarunkowego retry zużytego tokenu. Testy kontraktu obejmują brak/powtórzenie tokenu, niepoprawne typy JSON, HTTP 5xx i utratę sieci.

Planowane zmienne środowiskowe: `TURNSTILE_SITE_KEY`, `TURNSTILE_SECRET_KEY`, `TURNSTILE_ALLOWED_HOSTNAMES`, `CANARY_LOGIN_NAME`, `CANARY_HTTP_TOKEN_URL`, `CANARY_ALLOWED_HOSTS`. W `.env.example` umieszczamy puste wartości i opis. URL tokenu traktujemy jak sekret; walidujemy schemat i jawnie dozwolony host operatora, bez przekierowań do innych hostów. Odbiorcę e-mail konfiguruje operator po stronie Canarytokens; aplikacja nie wysyła własnej poczty.

Trzy tryby weryfikacji:

- Testy automatyczne: adapter zastąpiony fixture, żadnego Internetu i żadnego przełącznika w żądaniu użytkownika.
- Lokalny test widgetu: oficjalne klucze testowe, wyraźnie opisane jako testowe; nie wystarczają do odbioru ochrony.
- Odbiór rzeczywisty: prawdziwe klucze, host i akcje; osobno dowody rzeczywistych alertów Canarytokens.

Konfiguracja produkcyjna odrzuca znane klucze testowe i brak wymaganych sekretów. Lokalna błędna konfiguracja pokazuje czytelną odmowę zamiast pominięcia CAPTCHA. README opisze konfigurację widgetu przed pierwszą zmianą hasła ADMIN oraz sytuację awarii dostawcy. Komendy `init_admin` i `recover_admin` nadal pozostają ścieżką lokalnego operatora.

## 6. Pułapki i dowody alertów

Lokalna komenda dostarczania pobiera oczekujące sygnały i wywołuje token HTTP z timeoutem. Zapisuje status, ogranicza ponowienia i udostępnia bezpieczny wynik operatorowi. Instrukcja demonstracji wymaga jej uruchomienia; bez działającego dostarczania nie deklarujemy aktywnego alertowania. Odpowiedź tokenu nie świadczy o dostarczeniu poczty; odbiorca musi potwierdzić rzeczywisty alert.

Operator tworzy także token typu Word bez makr. Plik przechowuje lokalnie poza repozytorium, np. w ignorowanym `.tools/module-2-canaries/`. To wyjątek demonstracyjny, nie nowa funkcja załączników w module dokumentów. Należy sprawdzić obsługę w natywnym Wordzie i dostęp do sieci; sam podgląd lub pobranie nie jest dowodem wyzwolenia.

Zdjęcia alertów po anonimizacji mogą trafić do `docs/module-2/evidence/`; aktywne URL-e, identyfikatory zarządzania i adres odbiorcy pozostają poza publicznym materiałem. Zewnętrzny odbiór ma osobny status oczekujący do faktycznego potwierdzenia. W tej fazie nie generujemy tokenów ani nie wysyłamy żadnej wiadomości.

## 7. Etapy i zależności

| Etap | Zadania | Efekt |
|---|---|---|
| E8 — limit konta | T036–T038 | Dane i polityka, atomowy limit, panel i czas blokady |
| E9 — CAPTCHA i honeypot | T039–T042 | Turnstile na obu formularzach, kolejność bramek, testy |
| E10 — pułapki Canarytokens | T043–T046 | Konto-pułapka, dokument, dostarczanie i dwa potwierdzone alerty |
| E11 — bot i regresja | T047–T049 | Ograniczony skrypt, macierz rzeczywistych wyników, pełne testy |
| E12 — dodatkowy limit IP | T050–T051 | Niezależny limit dla wielu loginów; etap opcjonalny |
| E13 — materiały i odbiór | T052–T055 | Instrukcje, zrzuty, PDF i odbiór podstawy/rozszerzenia |

E8 poprzedza E9, E9 poprzedza E10. E11 korzysta z gotowych mechanizmów; brak jeszcze alertu nie blokuje pisania testów, ale blokuje oznaczenie odpowiedniego odbioru jako ukończonego. E12 można pominąć dla podstawowego zakresu. E13 wymaga rzeczywistych dowodów E10 i danych strony tytułowej.

## 8. Strategia kontroli i warunek zakończenia

Nowe testy korzystają z kontrolowanego zegara i rzeczywistego Argon2. Współbieżność sprawdzamy przez oddzielne połączenia do plikowej SQLite, jak w module 1. Zewnętrzny adapter jest mockowany w CI. Nie czekamy faktycznych 15 minut w testach jednostkowych; granice sprawdzamy przed, w i po terminie.

Sprawdzamy także bezpośredni POST bez JS, CSRF, brak tokenu w każdym kontekście, błędy sieci, poprawność odliczania, odnowienie widgetu oraz niezmienione hashe/historię/wersje po odmowie. Regresja obejmuje ADMIN, reset i jednorazowość poświadczeń, role dokumentów oraz licznik bezczynności modułu 1. Istniejące testy formularzy dostaną kontrolowaną fixture CAPTCHA, a nowe testy odmowy pozostaną bez niej.

Przy zakończeniu zadania zapisujemy właściwe testy i wynik w `docs/verification.md`; M2-AC-01–13 otrzymają macierz dowodów w `docs/module-2/acceptance.md`. Po przejściu kontroli zapisujemy logiczny commit. Przed końcowym odbiorem wykonujemy pełne CI lokalnie i start na pustej bazie, bez naruszania lokalnych kont użytkowniczki.

PDF powstaje po zebraniu dowodów i danych autora; wymaga renderowania i wizualnej kontroli. Podstawowy odbiór wymaga 18 obowiązkowych zadań i M2-AC-01–12. Zadania T050–T051 oraz M2-AC-13 mogą pozostać jawnie pominięte; nie oznaczamy ich jako wykonanych. Brak rzeczywistych kluczy lub alertów oznacza niepełny odbiór integracji, nawet gdy wszystkie testy lokalne przechodzą.
