# Zadania modułu ochrony przed botami i wyciekiem danych

Status: E9 ukończone; 7/20 wykonanych, w tym 7/18 obowiązkowych i 0/2 dodatkowych
Wersja: 0.8
Data: 2026-10-29
Podstawa: [specyfikacja 0.2](spec.md), [plan 0.2](plan.md), [źródło wymagań](source.md).

Kontynuujemy numerację po T035. Pole wyboru oznacza wykonanie i weryfikację, nie samo utworzenie planu. Po zadaniu zapisujemy dowód w `docs/verification.md` i logiczny commit. Nie zaznaczamy odbioru zewnętrznego po samym teście mocka. Jeżeli zmienia się zachowanie, najpierw aktualizujemy specyfikację. Ścieżki poniżej są docelowe.

## E8 Limit błędnych logowań

### T036 Modele i ustawienia ochrony logowania

- [x] Rozszerzyć politykę i utworzyć stan limitu oraz bezpiecznych zdarzeń.

**Zakres:** `login_failure_limit=5`, stałe 900 sekund, stan licznika z unikalnym kluczem znormalizowanego loginu i terminem blokady, minimalny `SecurityEvent`. Walidacja dodatnich liczb całkowitych, migracje zachowujące istniejące konta i ustawienia. Nie dodawać jeszcze pól opcjonalnego limitu IP.

**Zależności:** ukończony moduł 1, commit `1cf5075`.
**Wymagania:** M2-LOCK-01–02, M2-LOCK-05–06, M2-CAN-05.
**Gotowe, gdy:** migracje przechodzą na pustej i istniejącej testowej bazie, domyślne wartości i unikalność są sprawdzone, dane modułu 1 pozostają niezmienione.

**Wykonano 2026-10-29:** migracja `0004_login_protection`, próg 5, stałe 900 sekund, unikalny klucz HMAC znormalizowanego loginu, liczniki i zdarzenia bez swobodnego payloadu. Testy migracji z pustego i istniejącego schematu oraz walidacji: PASS. Szczegóły w `docs/verification.md`.

### T037 Atomowy limit prób dla konta

- [x] Zaimplementować licznik i 15-minutową blokadę w przepływie logowania.

**Zakres:** błędne poświadczenia, próg N, brak przedłużania blokady, poprawne hasło podczas blokady, zerowanie po sukcesie/końcu, istniejące i nieistniejące loginy. Odczyt polityki przy finalizacji i kontrola snapshotu poświadczeń; nie omijać ograniczonych kontekstów ani jednorazowości hasła. Zmiana progu działa przy następnej próbie.

**Zależności:** T036.
**Wymagania:** M2-LOCK-02–03, M2-LOCK-05–06.
**Gotowe, gdy:** testy granic 899,999…/900/900,001… sekund i równoległych prób potwierdzają limit bez utraty inkrementacji oraz brak utworzenia sesji po ustanowieniu blokady.

**Wykonano 2026-10-29:** `attempt_login()` rozstrzyga limity i ustanawia kontekst we wspólnej transakcji po weryfikacji hasła poza blokadą zapisu. Przesunięto rozdzielenie walidacji pól od uwierzytelniania z części T040, ponieważ jest potrzebne do atomowego limitu. Zmiana poświadczenia lub równoległa blokada odrzuca wcześniejszy sukces; tymczasowe hasło nadal można zużyć tylko raz. Dowody: `tests/security/test_login_limits.py` i `docs/verification.md`.

### T038 Panel progu i komunikat czasu blokady

- [x] Udostępnić ustawienie ADMIN i czytelny pozostały czas na ekranie logowania.

**Zakres:** jawne nowe pole w panelu, odrzucanie niepoprawnych wartości, odliczanie w interfejsie bez odpytywania przedłużającego blokadę. Bez JS serwer wyświetla aktualny czas po ponowieniu. Informacja nie rozróżnia kont istniejących od nieistniejących; brak automatycznego ponownego wysłania hasła.

**Zależności:** T037.
**Wymagania:** M2-LOCK-01, M2-LOCK-04, M2-LOCK-06; M2-AC-01–04.
**Gotowe, gdy:** test HTTP potwierdza dostęp tylko ADMIN i odmowę z czasem, a test odliczania potwierdza dokładny termin i brak zapisu sekretów w JS/URL.

**Wykonano 2026-10-29:** panel ADMIN zapisuje dodatni próg, a ekran logowania pokazuje zaokrąglony w górę czas blokady. Skrypt liczy lokalnie i nie wysyła żądań/hasła; bez JS czas podaje serwer. Testy HTTP obejmują role, CSRF, walidację oraz identyczne zasady dla znanych i nieznanych loginów. Zastosowano lokalną migrację po kopii zapasowej i sprawdzono zachowanie danych. Wyniki w `docs/verification.md`; M2-AC-01–04 w `docs/module-2/acceptance.md`.

**Zakończenie E8:** T036–T038 ukończono i zweryfikowano lokalnie. Każde zadanie ma własny commit. CAPTCHA i honeypot należą do następnego etapu.

## E9 CAPTCHA i honeypot

### T039 Adapter Turnstile i konfiguracja środowisk

- [x] Dodać wspólną serwerową walidację tokenu.

**Zakres:** Siteverify z timeoutem, kontrola odpowiedzi, hosta i akcji, odmowa przy błędach sieci i konfiguracji. Klucze z otoczenia, opisane puste wartości w `.env.example`, oddzielenie kluczy testowych. Zakaz testowych kluczy/obejść w publicznej konfiguracji. Rozszerzyć filtr raportowania błędów o nowe sekrety.

**Zależności:** T038.
**Wymagania:** M2-CAP-02–03, M2-CAP-05, M2-CAN-05.
**Gotowe, gdy:** testy adaptera bez Internetu obejmują sukces, fałszywy/zużyty/wygasły token, błędny host/akcję, wadliwy JSON, timeout i HTTP 5xx; żaden sekret nie trafia do raportu błędu.

**Wykonano 2026-10-29:** implementacja i odpowiednie testy zakończone; wyniki i ograniczenia odbioru zapisano w `docs/verification.md`.

### T040 CAPTCHA i pole-pułapka w logowaniu

- [x] Włączyć widget, honeypot i właściwą kolejność bramek przed weryfikacją hasła.

**Zakres:** rozdzielić obecne uwierzytelnianie w `LoginForm.clean()` od walidacji pól. Honeypot przed dostawcą, blokada przed CAPTCHA, CAPTCHA przed hasłem. Odmowa CAPTCHA/honeypotu nie zwiększa licznika poświadczeń. Reset widgetu po błędzie, maskowane puste hasło w ponownym HTML, dostępność klawiaturą i dla czytników ekranu.

**Zależności:** T037, T039.
**Wymagania:** M2-CAP-01–04, M2-HONEY-01–02, M2-LOCK-06; M2-AC-05, M2-AC-07.
**Gotowe, gdy:** bezpośredni POST bez JS/tokenu i niepusty honeypot są odrzucane bez weryfikacji hasła; prawidłowe logowanie zachowuje pełny/ograniczony kontekst modułu 1.

**Wykonano 2026-10-29:** implementacja i odpowiednie testy zakończone; wyniki i ograniczenia odbioru zapisano w `docs/verification.md`.

### T041 CAPTCHA w każdej ścieżce zmiany hasła

- [x] Chronić formularz standardowy i wszystkie warianty wymaganej zmiany.

**Zakres:** akcje widgetu `password_change` i `password_required`, formularze INITIAL/RESET/EXPIRED, nowy token po odmowie. CAPTCHA poprzedza usługę zmiany hasła. Opisać konfigurację przed pierwszym logowaniem ADMIN i zachowanie przy awarii dostawcy; komendy lokalnego operatora nie dostają CAPTCHA.

**Zależności:** T039–T040.
**Wymagania:** M2-CAP-02–06; M2-AC-06.
**Gotowe, gdy:** brak/błąd tokenu w każdym kontekście pozostawia hash, historię, wersję sesji i poświadczenie tymczasowe bez zmian; poprawna operacja nadal wymaga ponownego logowania.

**Wykonano 2026-10-29:** implementacja i odpowiednie testy zakończone; wyniki i ograniczenia odbioru zapisano w `docs/verification.md`.

### T042 Jednorazowość tokenów i regresja formularzy

- [x] Sprawdzić replay, granice, równoległość i dostępność nowych formularzy.

**Zakres:** ponowne użycie tokenu również między formularzami, odmowa po wygaśnięciu, błąd hosta/akcji, równoległe żądania, reset wyzwania i brak liczenia błędów dostawcy jako błędów hasła. Dostosować istniejące testy do jawnej fixture poprawnej walidacji bez dodawania obejścia HTTP.

**Zależności:** T040–T041.
**Wymagania:** M2-CAP-01–06, M2-TEST-04; M2-AC-05–07, M2-AC-11.
**Gotowe, gdy:** testy integracyjne sprawdzają skutki w bazie i sesji, ponowiony token nie autoryzuje drugiej operacji, a stare przypadki haseł/sesji zachowują wynik.

**Wykonano 2026-10-29:** implementacja i odpowiednie testy zakończone; wyniki i ograniczenia odbioru zapisano w `docs/verification.md`.

**Zakończenie E9:** T039–T042 ukończono i zweryfikowano offline. Cztery zadania mają oddzielne commity. Wynik końcowy: 374 testy pytest i 8 testów JavaScript PASS. Rzeczywiste klucze, widget w przeglądarce i dowody pozostają zakresem T053.

## E10 Pułapki Canarytokens

### T043 Rejestr pułapek i trwałe dostarczanie sygnałów

- [ ] Dodać rejestr loginu-pułapki, kolejkę i komendę dostarczania.

**Zakres:** oddzielna tożsamość bez praw użytkownika, ochrona przed kolizją/rejestracją zwykłego konta pod tą nazwą, stany pending/sent/error, ograniczone retry. URL pochodzi wyłącznie z konfiguracji operatora, host i schemat są walidowane, wywołanie sieciowe nie trzyma transakcji bazy. Komenda udostępnia stan bez wypisywania tokenu.

**Zależności:** T036, T042.
**Wymagania:** M2-CAN-01–02, M2-CAN-04–05.
**Gotowe, gdy:** testy symulują sukces, timeout i ponowienie bez utraty incydentu; brak konfiguracji nie udaje wysłania, rezerwacja nazwy działa także w panelu/komendach tworzących konta.

### T044 Wykrywanie użycia konta-pułapki

- [ ] Połączyć próbę logowania pułapką z incydentem i tokenem HTTP.

**Zakres:** dowolne hasło przy loginie-pułapce daje odmowę i sygnał przed honeypotem/CAPTCHA/blokadą; wcześniej obowiązuje CSRF i walidacja rozmiaru. Nie tworzyć pełnej lub ograniczonej sesji, nie wyświetlać nazwy pułapki w normalnej nawigacji.

**Zależności:** T040, T043.
**Wymagania:** M2-CAN-01–02, M2-CAN-04–05.
**Gotowe, gdy:** testy wszystkich bramek potwierdzają zapis incydentu i brak dostępu; zewnętrzne wywołania są mockowane. Rzeczywisty alert należy do T046.

### T045 Drugi token w dokumencie Word

- [ ] Przygotować izolowaną demonstrację dokumentu Canarytokens bez makr.

**Zakres:** instrukcja utworzenia i przechowywania autentycznego tokenu innego typu niż HTTP, syntetyczna zawartość, lokalny katalog poza repozytorium i listą dokumentów aplikacji. Zapisać wymagany program i dostęp sieciowy, sposób anonimizacji dowodu i odtworzenia demonstracji.

**Zależności:** T043.
**Wymagania:** M2-CAN-03, M2-CAN-05.
**Gotowe, gdy:** rzeczywisty plik-token jest przygotowany lokalnie i jego typ udokumentowany, a repozytorium zawiera instrukcję bez aktywnego URL/tokenu. Bez przygotowania pliku zadanie pozostaje nieukończone; sam opis nie wystarcza.

### T046 Odbiór dwóch rzeczywistych alertów

- [ ] Potwierdzić alert konta-pułapki i oddzielny alert otwarcia dokumentu.

**Zakres:** skonfigurować właściwego odbiorcę, uruchomić dostarczanie sygnałów, wykonać kontrolowane użycie obu pułapek i zebrać zanonimizowane zrzuty. Ująć ograniczenia: IP serwera dla tokenu HTTP i zależność dokumentu od programu/sieci. Działanie wyzwalające wiadomości wykonać dopiero w ramach jawnie autoryzowanej demonstracji.

**Zależności:** T044–T045; zewnętrzne tokeny, odbiorca i potwierdzenie otrzymania alertów.
**Wymagania:** M2-CAN-01–05, M2-REP-03; M2-AC-08–09.
**Gotowe, gdy:** istnieją dowody dwóch otrzymanych alertów różnych typów i powiązane czasy zdarzeń. Mock, zapis outbox lub HTTP 200 nie wystarcza. Jeśli potrzeba udziału użytkowniczki, pozostawić jawnie oczekujący odbiór i kontynuować niezależne zadania.

## E11 Bot i testy zabezpieczeń

### T047 Ograniczony skrypt symulujący bota

- [ ] Napisać narzędzie demonstracyjne dla własnej lokalnej instancji.

**Zakres:** pętla żądań z CSRF/cookies, twarda lista loopback, limit liczby prób i tempa, timeout oraz zakaz przekierowania do obcego hosta. Scenariusze z honeypotem, brakiem/niepoprawnym tokenem i loginem-pułapką; scenariusz limitu konta uruchamiany osobno w izolowanym profilu testowym z kontrolowanym adapterem. Brak łamania CAPTCHA, cudzych haseł i dowolnych celów sieciowych.

**Zależności:** T042, T044. Faktyczne otrzymanie alertu T046 nie blokuje napisania skryptu.
**Wymagania:** M2-TEST-01–02.
**Gotowe, gdy:** skrypt działa na odrębnej bazie/kontach testowych, odmawia obcego celu i nadmiarowych prób, nie wypisuje sekretów i nie wprowadza furtki do zwykłej aplikacji.

### T048 Wyniki testu bota i macierz zabezpieczeń

- [ ] Uruchomić scenariusze i zapisać faktyczne wyniki.

**Zakres:** oczekiwana/uruchomiona warstwa, status i bezpieczna odpowiedź, zdarzenie, PASS/FAIL/niezweryfikowane. Oddzielić wyniki z atrapą, testowymi kluczami i rzeczywistym dostawcą. Nie twierdzić, że licznik zadziałał, gdy żądanie odrzucono już na CAPTCHA.

**Zależności:** T047; dowody T046 dla wierszy otrzymanych alertów.
**Wymagania:** M2-TEST-02–03, M2-REP-03; M2-AC-10.
**Gotowe, gdy:** zapisane polecenia i syntetyczne dane pozwalają powtórzyć test, a raport zawiera rzeczywiste wyniki i jawne braki zewnętrznego odbioru.

### T049 Pełne testy integracyjne i regresja

- [ ] Zweryfikować nowe reguły razem z całą aplikacją modułu 1.

**Zakres:** kontrolowany czas, granice, równoległość, znane/nieznane loginy, ADMIN, hasła tymczasowe, polityka, CSRF, brak sekretów, błędy dostawców, sesje i role dokumentów. Ruff, formatowanie, kontrola Django i zgodności migracji; testy bez Internetu i danych lokalnych użytkowniczki.

**Zależności:** T038, T042, T044, T047.
**Wymagania:** M2-LOCK-01–06, M2-CAP-01–06, M2-HONEY-01–02, M2-CAN-01–05, M2-TEST-04; M2-AC-11.
**Gotowe, gdy:** pełny zestaw przechodzi, workflow obejmuje nowe testy i istnieje macierz automatycznych dowodów. Wynik automatyczny nie zastępuje T046.

## E12 Dodatkowy limit według IP

Ten etap jest opcjonalny zgodnie z załącznikiem. Jego pominięcie nie blokuje odbioru podstawowego; zadania zachowują puste pola z adnotacją „pominięto zakres dodatkowy”.

### T050 Stan i polityka niezależnego limitu IP

- [ ] Dodatkowe: dodać osobny licznik i próg IP w panelu ADMIN.

**Zakres:** niezależność od loginu, próg domyślny 20, blokada 900 sekund, flaga włączenia domyślnie wyłączona, normalizacja IPv4/IPv6 z `REMOTE_ADDR`. Nie ufać `X-Forwarded-For`; sukces logowania nie zeruje licznika IP.

**Zależności:** T049.
**Wymagania:** M2-IP-01–02.
**Gotowe, gdy:** migracje, walidacja, prawa ADMIN i testy kanonizacji/spoofingu nagłówków przechodzą, a limit konta działa niezależnie.

### T051 Integracja limitu IP i test spraying

- [ ] Dodatkowe: egzekwować limit dla prób na wielu loginach i udokumentować wynik.

**Zakres:** bramka IP przed CAPTCHA, atomowa aktualizacja po błędnych poświadczeniach, brak przesuwania blokady, późniejszy termin przy dwóch blokadach, scenariusz wielu kont spod jednego adresu. Uzupełnić skrypt, macierz, opis ryzyka wspólnego IP i testy regresyjne.

**Zależności:** T050.
**Wymagania:** M2-IP-01–03, M2-TEST-02–04; M2-AC-13.
**Gotowe, gdy:** zmiana loginu ani nagłówka nie omija limitu, dokładna granica działa, istniejące sesje pozostają zgodne z modułem 1 i pełny zestaw testów przechodzi.

## E13 Dokumentacja i odbiór

### T052 Instrukcja konfiguracji i odtworzenie środowiska

- [ ] Opisać instalację modułu 2 i sprawdzić ją na pustej bazie.

**Zakres:** README, `.env.example`, prawdziwe/testowe klucze i hosty, inicjalizacja ADMIN, ustawienie progu, pułapki i komenda dostarczania, skrypt bota, retencja zdarzeń, awaria CAPTCHA i procedura lokalnego operatora. Odtworzyć zależności i migracje w izolowanej kopii. Nie wkładać aktywnych tokenów do repozytorium.

**Zależności:** T043–T045, T047, T049; T051 tylko gdy wybrano zakres dodatkowy.
**Wymagania:** M2-CAP-05–06, M2-CAN-03–05, M2-TEST-01, M2-REP-01.
**Gotowe, gdy:** nowy operator może odtworzyć aplikację z instrukcji, a kroki zewnętrzne i potrzebne dane są jawne; konta użytkowniczki pozostają nietknięte.

### T053 Odbiór interfejsu i komplet dowodów

- [ ] Sprawdzić formularze w przeglądarce i zebrać zrzuty do sprawozdania.

**Zakres:** pulpit/telefon, klawiatura, odliczanie blokady, logowanie z prawdziwym widgetem, wszystkie konteksty zmiany hasła, odmowa bez tokenu, dwa zanonimizowane alerty i wynik skryptu. Odróżnić rzeczywiste klucze od testowych; aktywne URL-e i adres odbiorcy ukryć.

**Zależności:** T046, T048–T049, T052; rzeczywista konfiguracja Turnstile.
**Wymagania:** M2-CAP-04–06, M2-HONEY-01, M2-REP-03.
**Gotowe, gdy:** wymagane scenariusze przeglądarkowe są sprawdzone i pliki dowodów mają datę/opis. Bez realnego widgetu lub alertów nie oznaczać pełnego odbioru.

### T054 Sprawozdanie PDF

- [ ] Przygotować i wizualnie zweryfikować końcowe sprawozdanie.

**Zakres:** strona tytułowa, teoria własnymi słowami, gotowy Turnstile zamiast wariantu, logika limitów i weryfikacji tokenu, oba typy pułapek, fragmenty kodu, zrzuty, macierz bota, cztery odpowiedzi kontrolne, wnioski i link do kodu lub archiwum. Zaznaczyć, czy wykonano zakres IP.

**Zależności:** T048, T052–T053; imię, nazwisko, grupa, indeks, przedmiot i link/archiwum kodu od użytkowniczki lub dostępne w projekcie.
**Wymagania:** M2-REP-01–03; M2-AC-12.
**Gotowe, gdy:** PDF zawiera komplet prawdziwych dowodów i danych, wszystkie strony są wyrenderowane i sprawdzone, a plik nie zawiera sekretów ani fikcyjnych danych autora. Brakujących danych nie uzupełniać domysłami.

### T055 Odbiór modułu 2 i zamknięcie dokumentacji

- [ ] Potwierdzić kryteria i zamknąć podstawowy zakres modułu.

**Zakres:** macierz M2-AC-01–12 w `docs/module-2/acceptance.md`, pełne kontrole na końcowym stanie, zgodność spec/plan/tasks z implementacją i dowodami. M2-AC-13 osobno jako PASS lub „nie wykonano zakresu dodatkowego”. Aktualizacja `specs/README.md`, lokalny commit; push lub wdrożenie wymagają osobnego zadania.

**Zależności:** T036–T049, T052–T054; T050–T051 tylko dla odbioru rozszerzenia.
**Wymagania:** M2-AC-01–12; opcjonalnie M2-AC-13.
**Gotowe, gdy:** wszystkie wymagane kryteria mają rzeczywisty dowód, 18 obowiązkowych zadań jest zakończonych, PDF i instrukcje są dostępne, a niezamknięte zależności nie są przedstawiane jako sukces.

## Najbliższy krok

Następne zadanie to **T043** w E10. Klucze dostawców, zewnętrzne tokeny, potwierdzenia poczty i dane autora będą potrzebne przed odpowiednimi odbiorami; nie blokują przygotowania modeli i testów. Ten dokument jest planem dalszej pracy, a nie poleceniem natychmiastowej implementacji wszystkich zadań.
