# Specyfikacja modułu identyfikacji uwierzytelniania i autoryzacji

Status: zaimplementowano i odebrano lokalnie
Wersja: 0.3
Data aktualizacji statusu: 2026-10-29

Dalsza rozbudowa: [moduł 2 — ochrona przed botami i wyciekiem danych](../002-attack-protection/spec.md). Wyłączenie CAPTCHA z zakresu niniejszego modułu pozostaje historyczną granicą modułu 1; nowe wymagania definiuje osobna specyfikacja. Zmiany komunikatów logowania AUTH-02–03 i UI-04 opisuje moduł 2.

## 1. Cel projektu

Powstanie edukacyjna aplikacja webowa w Pythonie, służąca poznawaniu i weryfikowaniu mechanizmów cyberbezpieczeństwa. Umożliwi zarządzanie kontami, uwierzytelnianie, obsługę cyklu życia haseł oraz kontrolę dostępu zależną od roli. Jej struktura ma umożliwiać późniejszą rozbudowę o kolejne mechanizmy bezpieczeństwa.

SDD oznacza tutaj Spec-Driven Development. Ta specyfikacja określa zachowanie aplikacji i kryteria odbioru. Architektura, dobór zależności i kolejność prac zostaną opisane osobno w `plan.md` i `tasks.md`.

## 2. Założenia projektu

- Aplikacja jest projektem edukacyjnym o cyberbezpieczeństwie, rozwijanym przyrostowo.
- Logika aplikacji powstaje w Pythonie, a użytkownicy korzystają z interfejsu webowego w języku polskim.
- Kod, dokumentacja i testy są utrzymywane w uporządkowanym repozytorium na GitHubie.
- Konta tworzy administrator; aplikacja nie oferuje publicznej rejestracji.
- Uprawnienia są przyznawane zgodnie z zasadą najmniejszych uprawnień i sprawdzane na serwerze.
- Mechanizmy kryptograficzne i sesje korzystają ze sprawdzonych bibliotek.

Wymagania oznaczone identyfikatorami są podstawą testów odbiorczych. Reguły, wartości domyślne i macierz uprawnień określają zakres pierwszej wersji aplikacji. Realizację E1–E7 i wyniki AC-01–AC-31 opisują `tasks.md` oraz `docs/verification.md`; stan modułu obejmuje również korektę SESS-07 z 2026-10-29. Odbiór jest lokalny; nie wykonywano publikacji ani wdrożenia.

## 3. Zakres

### 3.1. W zakresie

- Logowanie i wylogowanie.
- Stałe konto o loginie `ADMIN`.
- Zarządzanie użytkownikami przez administratora.
- Pierwsze logowanie z wymuszoną zmianą hasła.
- Zmiana hasła z weryfikacją starego hasła.
- Hasła tymczasowe nadawane przy tworzeniu konta i resecie.
- Konfigurowalna polityka haseł i historia poprzednich haseł.
- Pięć ról: Administrator, Kierownik, Redaktor, Pracownik i Czytelnik, z kontrolą uprawnień na serwerze.
- Sesje z limitem bezczynności.
- Prosty moduł dokumentów tekstowych do demonstracji uprawnień.
- Sześć kont testowych oraz instrukcja uruchomienia projektu.

### 3.2. Poza bieżącym zakresem

- Uwierzytelnianie dwuskładnikowe TOTP, przewidziane jako możliwe rozszerzenie.
- Publiczna rejestracja, odzyskiwanie hasła przez e-mail i logowanie zewnętrzne.
- CAPTCHA i pozostałe rozszerzenia bezpieczeństwa nieopisane w tej specyfikacji.
- Załączniki, edytor treści HTML i wersjonowanie dokumentów.
- Publiczne wdrożenie aplikacji; publikacja kodu na GitHubie nie oznacza wdrożenia.

## 4. Użytkownicy i role

Aplikacja udostępnia pięć ról: Administrator, Kierownik, Redaktor, Pracownik i Czytelnik.

Każde konto ma dokładnie jedną rolę. Uprawnienia przyznajemy jawnie, bez automatycznego dziedziczenia wynikającego z nazwy roli.

Administrator zarządza kontami i bezpieczeństwem. Kierownik odpowiada za publikację treści. Redaktor opracowuje szkice. Pracownik tworzy własne szkice. Czytelnik przegląda opublikowane treści.

### 4.1. Proponowana macierz uprawnień

„Własny” oznacza dokument utworzony przez zalogowane konto. „Szkic” i „Opublikowany” są jedynymi stanami dokumentu.

| Operacja | Administrator | Kierownik | Redaktor | Pracownik | Czytelnik |
|---|---|---|---|---|---|
| Odczyt opublikowanych dokumentów | Tak | Tak | Tak | Tak | Tak |
| Odczyt szkiców | Nie | Wszystkie | Wszystkie | Własne | Nie |
| Tworzenie szkicu | Nie | Tak | Tak | Tak | Nie |
| Edycja szkicu | Nie | Wszystkie | Wszystkie | Własne | Nie |
| Usunięcie szkicu | Nie | Nie | Nie | Nie | Nie |
| Publikacja szkicu | Nie | Tak | Nie | Nie | Nie |
| Wycofanie publikacji do szkicu | Nie | Tak | Nie | Nie | Nie |
| Zarządzanie kontami i rolami | Tak | Nie | Nie | Nie | Nie |
| Reset hasła innego konta | Tak | Nie | Nie | Nie | Nie |
| Zmiana ustawień bezpieczeństwa | Tak | Nie | Nie | Nie | Nie |
| Zmiana własnego hasła i wylogowanie | Tak | Tak | Tak | Tak | Tak |

Administrator nie otrzymuje automatycznie uprawnień redakcyjnych. Opublikowany dokument można edytować dopiero po wycofaniu publikacji przez Kierownika. Funkcja usuwania dokumentów nie jest potrzebna do demonstracji ról i pozostaje poza zakresem.

## 5. Wymagania funkcjonalne

### 5.1. Identyfikacja i logowanie

- **AUTH-01:** formularz zawiera login i maskowane pole hasła.
- **AUTH-02:** niepoprawny login lub hasło powoduje komunikat dokładnie „Login lub hasło niepoprawne”.
- **AUTH-03:** ten sam komunikat obowiązuje dla konta nieistniejącego, zablokowanego oraz nieważnego hasła tymczasowego. Odpowiedź nie ujawnia przyczyny odmowy.
- **AUTH-04:** login jest unikalny bez względu na wielkość liter; otaczające spacje są usuwane. Konto `ADMIN` nie może mieć odpowiednika `admin`. Hasło jest porównywane dokładnie, bez usuwania spacji i zmiany wielkości liter.
- **AUTH-05:** aplikacja rozróżnia dostęp anonimowy, ograniczony dostęp do zmiany hasła oraz pełny dostęp zgodny z rolą.
- **AUTH-06:** po zmianie hasła tymczasowego lub wygasłego użytkownik loguje się ponownie nowym hasłem.

### 5.2. Hasła i ich historia

- **PASS-01:** hasła są przechowywane wyłącznie jako hashe z losową solą, przy użyciu biblioteki przeznaczonej do haseł. Dotyczy to również haseł tymczasowych i historii.
- **PASS-02:** algorytmem przechowywania będzie Argon2id, obsługiwany przez sprawdzoną bibliotekę.
- **PASS-03:** domyślna minimalna długość nowego hasła wynosi 14 znaków.
- **PASS-04:** nowe hasło użytkownik wpisuje dwukrotnie; wartości muszą być identyczne.
- **PASS-05:** standardowa zmiana hasła wymaga podania poprawnego starego hasła.
- **PASS-06:** administrator może włączać i wyłączać regułę minimalnej odległości Levenshteina. Gdy jest włączona, odległość Levenshteina pomiędzy starym i nowym hasłem musi wynosić co najmniej 4.
- **PASS-07:** odległość oznacza minimalną liczbę wstawień, usunięć i zamian znaków, z kosztem każdej operacji równym 1. Wielkość liter ma znaczenie; nie stosujemy normalizacji hasła.
- **PASS-08:** nie można ponownie ustawić poprzednio używanego hasła.
- **PASS-09:** odrzucamy hasło bieżące i ostatnie 5 haseł stałych. Historia zawiera hashe, a sprawdzenie polega na weryfikacji kandydata względem każdego z nich. Hasła tymczasowe nie wypierają haseł stałych z historii; reset nie usuwa historii.
- **PASS-10:** lista popularnych, zabronionych haseł stanowi dodatkową walidację. Nie wymagamy określonej liczby cyfr, wielkich liter ani znaków specjalnych w haśle stałym.
- **PASS-11:** wyłączenie reguły Levenshteina nie wyłącza minimalnej długości, potwierdzenia, historii ani listy zabronionych haseł.
- **PASS-12:** błędna zmiana hasła nie modyfikuje hasha, historii ani daty ważności. Poprawna zmiana aktualizuje je jako jedną operację.

### 5.3. Hasło tymczasowe i pierwsze logowanie

Hasło tymczasowe jest jednorazowym hasłem początkowym lub resetującym nadawanym przez administratora. Umożliwia ustawienie własnego hasła stałego. Jest to mechanizm odrębny od kodów TOTP.

- **TEMP-01:** przy utworzeniu i resecie konta administrator nadaje hasło tymczasowe złożone z 16 znaków alfanumerycznych, ważne 4 godziny.
- **TEMP-02:** aplikacja generuje je kryptograficznie bezpiecznie z zestawu `A–Z`, `a–z`, `0–9` i pokazuje administratorowi jednokrotnie po operacji. Przekazanie hasła użytkownikowi odbywa się poza aplikacją.
- **TEMP-03:** pierwsze logowanie wymusza ustawienie własnego hasła, podawanego dwukrotnie.
- **TEMP-04:** poprawne użycie hasła tymczasowego zużywa je i tworzy wyłącznie ograniczoną sesję zmiany hasła. Nie zapewnia dostępu do dokumentów, panelu administracyjnego ani ustawień.
- **TEMP-05:** ograniczona sesja wygasa po wcześniejszym z terminów: upływie limitu bezczynności albo pierwotnym terminie ważności hasła tymczasowego. Utrata tej sesji wymaga nowego resetu przez administratora.
- **TEMP-06:** w chwili równej terminowi ważności hasło tymczasowe jest już nieważne. Dwie równoczesne próby nie mogą go skutecznie zużyć dwukrotnie.
- **TEMP-07:** reset natychmiast unieważnia dotychczasowe hasło tymczasowe, hasło logowania i sesje konta. Zachowuje historię haseł stałych.
- **TEMP-08:** przy pierwszej zmianie porównujemy nowe hasło z podanym hasłem tymczasowym także regułą Levenshteina, jeżeli jest włączona. Można wymagać ponownego wpisania hasła tymczasowego w formularzu zmiany; nie przechowujemy jego jawnej wartości w sesji.
- **TEMP-09:** po resecie nie obliczamy odległości od zapomnianego hasła stałego, ponieważ nie znamy jego treści. Nadal sprawdzamy historię hashy. Nie próbujemy odtwarzać hasła z hasha.

### 5.4. Ważność hasła stałego

- **EXP-01:** administrator ustawia ważność hasła w dniach.
- **EXP-02:** wartość `0` wyłącza okresowe wygasanie; jest to ustawienie domyślne. Wartości dodatnie oznaczają pełne okresy 24 godzin od ostatniego ustawienia hasła stałego. Wartości ujemne i niecałkowite są odrzucane.
- **EXP-03:** wygasłe hasło pozwala wyłącznie przejść do ograniczonej sesji zmiany hasła. Zmiana wymaga starego hasła i wszystkich aktywnych walidacji.
- **EXP-04:** ważność hasła stałego i czterogodzinna ważność hasła tymczasowego są niezależne.

### 5.5. Administracja kontami

- **ADMIN-01:** administrator może wyświetlać listę, tworzyć, edytować, blokować i usuwać użytkowników oraz resetować ich hasła.
- **ADMIN-02:** lista pokazuje login, imię, nazwisko, rolę i stan konta; nie udostępnia hashy ani haseł.
- **ADMIN-03:** edycja umożliwia zmianę imienia, nazwiska i roli. Login po utworzeniu pozostaje niezmienny.
- **ADMIN-04:** blokada natychmiast odbiera możliwość logowania; kolejne żądanie w istniejącej sesji również jest odrzucane. Odblokowanie nie przywraca unieważnionych sesji.
- **ADMIN-05:** zmiana roli unieważnia istniejące sesje konta. Nowe uprawnienia obowiązują po ponownym logowaniu.
- **ADMIN-06:** usuwanie wymaga potwierdzenia i oznacza logiczne usunięcie konta: konto traci dostęp i znika z aktywnej listy, ale pozostaje identyfikator autora dokumentów. Usunięty login pozostaje zarezerwowany.
- **ADMIN-07:** konto `ADMIN` nie może być usunięte, zablokowane, przemianowane ani pozbawione roli Administrator. W tej wersji jest jedynym kontem administratora; pozostałym kontom można przypisać jedną z czterech ról biznesowych.
- **ADMIN-08:** konto `ADMIN` powstaje w lokalnej procedurze inicjalizacji z hasłem podanym przez operatora. Hasło nie jest zapisane w kodzie ani repozytorium. Pierwsze logowanie także wymusza jego zmianę.
- **ADMIN-09:** lokalna procedura odzyskania dostępu do `ADMIN` może wydać nowe hasło tymczasowe i unieważnić jego sesje. Nie udostępniamy tej operacji anonimowo przez WWW.

### 5.6. Ustawienia bezpieczeństwa

- **CONF-01:** administrator może zmieniać stan reguły minimalnej odległości Levenshteina, ważność hasła stałego i limit bezczynności sesji.
- **CONF-02:** reguła minimalnej odległości Levenshteina jest domyślnie włączona. Limit bezczynności wynosi domyślnie 15 minut i musi być dodatnią całkowitą liczbą minut.
- **CONF-03:** minimalna długość wynosi w tej wersji stale 14 znaków; liczba przechowywanych haseł historycznych wynosi stale 5. Interfejs administratora nie musi ich konfigurować.
- **CONF-04:** nowe ustawienia obowiązują od następnego żądania. Zmiana ważności hasła może oznaczać jego natychmiastowe wygaśnięcie, a skrócenie limitu sesji jej zakończenie przy następnym żądaniu.
- **CONF-05:** włączenie reguły Levenshteina wpływa na przyszłe zmiany haseł; nie powoduje sprawdzania odległości dla już zapisanych hashy.

### 5.7. Sesje

- **SESS-01:** użytkownik może ręcznie się wylogować; sesja zostaje unieważniona po stronie serwera.
- **SESS-02:** sesja wygasa automatycznie po skonfigurowanym czasie bezczynności.
- **SESS-03:** aktywność oznacza uwierzytelnione żądanie do widoku aplikacji. Pobranie zasobu statycznego, automatyczne odpytywanie i ruch myszy nie przedłużają sesji. Upływ limitu jest sprawdzany przed aktualizacją czasu aktywności.
- **SESS-04:** na granicy limitu sesja jest już wygasła. Odświeżenie strony lub użycie starego ciasteczka jej nie przywraca.
- **SESS-05:** każda poprawna zmiana hasła unieważnia wszystkie sesje konta, w tym sesję wykonującą zmianę. Użytkownik wraca do logowania.
- **SESS-06:** sesje obsługuje sprawdzony mechanizm frameworka. Identyfikator sesji jest zmieniany przy logowaniu, a hasła nie trafiają do danych sesyjnych.
- **SESS-07:** interfejs pokazuje pozostały czas sesji i po potwierdzeniu jej wygaśnięcia automatycznie przenosi do logowania, również bez kliknięcia użytkownika. Bierna kontrola stanu nie przedłuża aktywności. Aktywność w innej karcie tego samego kontekstu jest uwzględniana przed przekierowaniem. Serwer pozostaje źródłem prawdy i odrzuca wygasłą sesję także bez JavaScript. Przy utracie sieci po upływie znanego terminu interfejs ukrywa chronioną treść do potwierdzenia stanu. Widoki chronione mają zakaz cache.

### 5.8. Autoryzacja i dokumenty

- **RBAC-01:** operacje są dozwolone wyłącznie zgodnie z przypisanymi uprawnieniami; domyślnie dostęp jest zabroniony.
- **RBAC-02:** kontrola dostępu odbywa się na serwerze także dla bezpośrednich adresów, wysłanych formularzy i zmienionych identyfikatorów obiektów.
- **RBAC-03:** niezalogowana osoba jest kierowana do logowania; zalogowana osoba bez uprawnienia otrzymuje HTTP 403. Nieistniejący obiekt zwraca HTTP 404.
- **RBAC-04:** listy i szczegóły nie ujawniają treści szkiców poza zakresem roli lub własności. Identyfikator autora jest ustalany na serwerze, nie na podstawie przesłanego formularza.
- **DOC-01:** dokument ma tytuł, treść tekstową, autora, stan oraz daty utworzenia i modyfikacji. Nowy dokument jest szkicem.
- **DOC-02:** interfejs pokazuje tylko dostępne operacje, a każda operacja jest niezależnie weryfikowana przez serwer.

## 6. Interfejs

- **UI-01:** aplikacja ma spójny, dopracowany interfejs w języku polskim, użyteczny na komputerze i telefonie.
- **UI-02:** widoki obejmują logowanie, wymuszoną zmianę hasła, pulpit, listę i szczegóły dokumentów, edycję szkicu, zmianę własnego hasła, zarządzanie kontami, ustawienia oraz strony błędów.
- **UI-03:** formularze mają etykiety, widoczny fokus klawiatury i czytelne błędy tekstowe. Informacji nie przekazujemy wyłącznie kolorem.
- **UI-04:** formularz nowego hasła opisuje aktywne zasady; odmowa podaje niespełnione kryterium. Błąd logowania pozostaje ogólny zgodnie z AUTH-02.
- **UI-05:** reset, blokada i usunięcie konta wymagają potwierdzenia wskazującego konkretne konto i skutek operacji.

## 7. Wymagania techniczne i repozytorium

- **TECH-01:** logika aplikacji jest napisana w Pythonie. Proponowany framework to Django; szczegóły zostaną zapisane w planie technicznym.
- **TECH-02:** repozytorium rozdziela konfigurację, konta, reguły bezpieczeństwa, dokumenty, szablony, zasoby statyczne, testy i specyfikacje.
- **TECH-03:** korzystamy z gotowych mechanizmów hashowania, losowości, sesji i ochrony CSRF. Żądania zmieniające stan wymagają odpowiedniej metody HTTP i ochrony CSRF; GET nie zmienia danych.
- **TECH-04:** szablony bezpiecznie wyświetlają tekst dokumentów i danych użytkownika; wpisany kod HTML lub skrypt nie jest wykonywany.
- **TECH-05:** hasła, hasła tymczasowe, identyfikatory sesji i sekrety nie trafiają do logów ani komunikatów diagnostycznych. Jedyną celową prezentacją wygenerowanego hasła tymczasowego jest TEMP-02.
- **TECH-06:** repozytorium zawiera README, deklarację zależności, migracje, `.gitignore` i `.env.example` bez sekretów. Lokalna baza, plik `.env` i środowisko wirtualne pozostają poza Git.
- **TECH-07:** instrukcja umożliwia uruchomienie z czystego klonu, inicjalizację `ADMIN`, utworzenie danych demonstracyjnych oraz uruchomienie testów. Automatyczne kontrole w GitHub Actions obejmują testy i analizę stylu kodu.
- **TECH-08:** czas jest zapisywany i porównywany z uwzględnieniem strefy czasowej; prezentacja używa `Europe/Warsaw`. Testy granic czasowych korzystają z kontrolowanego zegara, bez rzeczywistego oczekiwania godzinami.
- **TECH-09:** konfiguracja lokalna i konfiguracja publicznego wdrożenia są rozdzielone. Przyszłe wdrożenie wymaga HTTPS, bezpiecznych ciasteczek sesyjnych i wyłączonego trybu debugowania.

## 8. Dane demonstracyjne

Środowisko demonstracyjne zawiera 6 kont testowych poza osobnym `ADMIN`: 1 Kierownika, 1 Redaktora, 2 Pracowników i 2 Czytelników. Dwa konta Pracowników umożliwiają sprawdzenie dostępu do cudzych szkiców.

Komenda przygotowująca dane jest przeznaczona do środowiska lokalnego. Nie zmienia istniejących haseł przy ponownym wykonaniu bez wyraźnej opcji resetu. Hasła są generowane przy uruchomieniu, a nie umieszczane w repozytorium. Dane treści obejmują dokument opublikowany i szkice różnych autorów.

## 9. Kryteria odbioru

| ID | Scenariusz | Oczekiwany rezultat |
|---|---|---|
| AC-01 | Błędne hasło, nieistniejący login lub zablokowane konto | Ten sam komunikat „Login lub hasło niepoprawne”; brak uwierzytelnionej sesji |
| AC-02 | Poprawne hasło aktywnego konta bez ograniczeń | Dostęp zgodny z rolą |
| AC-03 | Pierwsze użycie ważnego hasła tymczasowego | Tylko formularz zmiany hasła; bez dostępu do pozostałych funkcji |
| AC-04 | Nowe hasło ma 13 znaków | Odrzucenie; dotychczasowe dane uwierzytelniania pozostają bez zmian |
| AC-05 | Nowe hasło ma 14 znaków i spełnia pozostałe zasady | Akceptacja |
| AC-06 | Potwierdzenie różni się od nowego hasła | Odrzucenie bez modyfikacji hasła |
| AC-07 | Stare hasło w standardowej zmianie jest błędne | Odrzucenie zmiany |
| AC-08 | Reguła minimalnej odległości Levenshteina jest włączona, odległość wynosi 3 | Odrzucenie zmiany |
| AC-09 | Reguła minimalnej odległości Levenshteina jest włączona, odległość wynosi 4 | Reguła przechodzi; akceptacja, jeśli pozostałe zasady są spełnione |
| AC-10 | Reguła minimalnej odległości Levenshteina jest wyłączona | Brak kontroli odległości; pozostałe walidacje nadal działają |
| AC-11 | Kandydat jest hasłem bieżącym albo jednym z 5 ostatnich haseł stałych | Odrzucenie także po administracyjnym resecie |
| AC-12 | Utworzenie lub reset konta | Nowe losowe hasło ma 16 znaków z dozwolonego alfabetu i ważność 4 godzin |
| AC-13 | Użycie hasła tymczasowego tuż przed upływem 4 godzin i dokładnie w terminie | Przed terminem możliwe; w terminie odrzucone |
| AC-14 | Ponowne lub równoczesne użycie zużytego hasła tymczasowego | Najwyżej jedna próba tworzy ograniczoną sesję |
| AC-15 | Poprawne zakończenie wymuszonej zmiany hasła | Ograniczona sesja wygasa; można zalogować się nowym hasłem; tymczasowe nie działa |
| AC-16 | Reset hasła konta posiadającego aktywne sesje | Stare dane uwierzytelniania i sesje nie zapewniają dostępu |
| AC-17 | Czytelnik wysyła bezpośrednie żądanie publikacji dokumentu | HTTP 403; stan dokumentu pozostaje bez zmian |
| AC-18 | Pracownik podmienia identyfikator własnego szkicu na cudzy | HTTP 403; brak ujawnienia treści i brak modyfikacji |
| AC-19 | Redaktor próbuje publikacji, Kierownik publikuje | Redaktor otrzymuje 403; Kierownik może opublikować szkic |
| AC-20 | Administrator próbuje odczytać szkic lub go edytować | HTTP 403 zgodnie z proponowaną macierzą |
| AC-21 | Konto zostaje zablokowane, usunięte lub zmienia rolę | Kolejne żądanie starej sesji nie daje dostępu |
| AC-22 | Próba usunięcia, blokady lub degradacji `ADMIN` | Odmowa po stronie serwera; konto pozostaje dostępne |
| AC-23 | Ręczne wylogowanie i ponowne użycie starego ciasteczka | Brak dostępu do chronionych widoków |
| AC-24 | Bezczynność osiąga limit; następnie przychodzi żądanie | Sesja wygasła; żądanie nie odświeża jej wstecz |
| AC-25 | Uprawnione żądanie przed limitem bezczynności | Czas aktywności zostaje odnowiony |
| AC-26 | Zmiana ustawień na bardziej restrykcyjne | Przy następnym żądaniu obowiązuje nowa ważność hasła i limit sesji |
| AC-27 | Hasło stałe wygasa | Możliwa wyłącznie zmiana hasła po potwierdzeniu starego |
| AC-28 | Inspekcja bazy i danych sesyjnych po przejściu scenariuszy | Hasła występują wyłącznie jako hashe; brak jawnych haseł w sesjach |
| AC-29 | Żądanie zmieniające stan bez poprawnej ochrony CSRF | Odrzucenie i brak zmiany danych |
| AC-30 | Treść dokumentu zawiera znacznik skryptu | Treść jest wyświetlana jako tekst; skrypt nie wykonuje się |
| AC-31 | Uruchomienie według README z czystego klonu | Działają migracje, inicjalizacja i testy bez sekretów zapisanych w repozytorium |

## 10. Najważniejsze założenia pierwszej wersji

Poniższe założenia podsumowują proponowany zakres pierwszej wersji. Ich zmiany wymagają aktualizacji odpowiednich wymagań i kryteriów odbioru.

1. Sześć kont testowych oprócz konta `ADMIN`.
2. Jedna rola na konto i jedno chronione konto administratora.
3. Moduł dokumentów i macierz uprawnień z punktu 4.1.
4. Historia pięciu poprzednich haseł stałych; reset nie zeruje historii.
5. Domyślnie włączona reguła Levenshteina, 15 minut bezczynności i wyłączone okresowe wygasanie hasła stałego.
6. Logiczne usuwanie kont zamiast fizycznego usuwania rekordów.
7. Jednorazowe zużycie hasła tymczasowego przy wejściu do ograniczonej sesji; utrata tej sesji wymaga resetu.
8. Porównanie Levenshteina z hasłem tymczasowym po resecie, bez porównania z nieznanym poprzednim hasłem stałym.

## 11. Definicja ukończenia modułu

- Wymagania zakresu podstawowego są zaimplementowane, a przyjęte decyzje opisane w specyfikacji.
- Kryteria odbioru są zweryfikowane; kluczowe reguły bezpieczeństwa mają testy automatyczne, a interfejs został sprawdzony w przeglądarce.
- Uprawnienia sprawdzono dla każdej roli, również przez bezpośrednie żądania z pominięciem interfejsu.
- Instrukcja uruchomienia i dane demonstracyjne działają z czystego klonu.
- Repozytorium nie zawiera sekretów, lokalnej bazy ani jawnych haseł.
- Specyfikacja, plan, zadania i końcowe zachowanie aplikacji są zgodne.
- Odbiór obejmuje zakres pierwszej wersji opisany w tej specyfikacji.
