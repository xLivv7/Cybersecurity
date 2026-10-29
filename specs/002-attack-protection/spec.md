# Specyfikacja ochrony przed botami i wyciekiem danych

Status: implementacja E8 w toku; ukończono T036–T037, panel i czas blokady przed odbiorem
Wersja: 0.1
Data: 2026-10-29
Podstawa: [załącznik i decyzje](source.md), aplikacja modułu 1 w commicie `1cf5075`.

## 1. Cel i zakres

Rozszerzamy istniejącą aplikację Django o ochronę logowania przed próbami automatycznymi, CAPTCHA przy logowaniu i zmianie hasła, wykrywanie użycia zasobów-pułapek oraz udokumentowany test na własnej aplikacji. Zachowujemy role, ochronę ADMIN, historię haseł, ograniczone konteksty i wygaszanie sesji z modułu 1.

Zakres podstawowy obejmuje konfigurowalny próg błędnych logowań, czasową blokadę, Turnstile na obu formularzach, honeypot, dwa typy Canarytokens, test bota i sprawozdanie PDF. Limit per IP jest zakresem dodatkowym. Nie dodajemy publicznej rejestracji, TOTP, publicznego wdrożenia ani infrastruktury do testowania cudzych serwisów.

## 2. Wymagania

### Blokada logowania

- **M2-LOCK-01:** tylko ADMIN z pełną sesją może zmienić dodatni całkowity próg błędów. Wartość domyślna to 5. Zmiana nie dotyczy limitu bezczynności sesji.
- **M2-LOCK-02:** kolejne błędne weryfikacje poświadczeń dla znormalizowanego loginu (`strip().casefold()`) zwiększają licznik. Próba osiągająca próg ustawia blokadę na 15 minut. Działa to również dla ADMIN i dla haseł tymczasowych; nie zmienia administracyjnego `is_active`.
- **M2-LOCK-03:** podczas blokady także poprawne hasło nie tworzy pełnego ani ograniczonego kontekstu. Kolejne próby nie przesuwają końca blokady. Przy `teraz >= blocked_until` można spróbować ponownie, a licznik rozpoczyna się od zera. Poprawne logowanie przed osiągnięciem progu również zeruje licznik.
- **M2-LOCK-04:** odmowa na ekranie logowania pokazuje zaokrąglony w górę pozostały czas blokady i odlicza go bez odnawiania blokady lub sesji. Po końcu nie wysyła automatycznie hasła; użytkownik ponawia logowanie z nowym tokenem CAPTCHA. Bez JavaScript serwer pokazuje czas przy kolejnym żądaniu.
- **M2-LOCK-05:** licznik i blokada działają atomowo przy równoległych żądaniach i są wspólne między procesami. Obniżenie progu działa przy kolejnej próbie; istniejący termin blokady nie skraca się ani nie wydłuża. Zmiana progu nie przelicza historii w tle.
- **M2-LOCK-06:** nieistniejący login ma taki sam komunikat i stan licznika jak istniejący. Nie ujawniamy, czy konto istnieje, jest administracyjnie zablokowane lub usunięte. Sam błąd CAPTCHA, honeypot lub CSRF nie zwiększa licznika błędnych poświadczeń. Blokada logowania nie kończy wcześniej utworzonych sesji; nadal podlegają zasadom modułu 1.

### CAPTCHA i pole-pułapka

- **M2-CAP-01:** logowanie wymaga poprawnego tokenu Cloudflare Turnstile. Nie wdrażamy własnego wariantu CAPTCHA; załącznik pozwala pominąć go po wybraniu dostawcy.
- **M2-CAP-02:** serwer weryfikuje token przez Siteverify przed sprawdzeniem hasła. Sam widget, obecność pola lub komunikat JavaScript nie wystarczają. Token jest jednorazowy, ważny najwyżej 300 sekund i przeznaczony dla oczekiwanego hosta i akcji formularza.
- **M2-CAP-03:** brak tokenu, fałszywy token, ponowne użycie, wygaśnięcie, błędny host/akcja i awaria dostawcy oznaczają odmowę operacji. Żadne z tych zdarzeń nie zmienia hasła, historii, wersji sesji ani stanu jednorazowego hasła. Sukces walidacji nie może być użyty do kolejnej operacji.
- **M2-CAP-04:** przy każdym ponowieniu formularza po błędzie użytkownik otrzymuje możliwość nowego wyzwania. Hasło nie wraca do HTML. Widget ma czytelną obsługę oczekiwania, wygaśnięcia i błędu, dostępny komunikat oraz obsługę klawiatury.
- **M2-CAP-05:** klucz sekretny pozostaje na serwerze; testowe klucze i atrapy są oddzielone od rzeczywistej konfiguracji. Brak konfiguracji nie może powodować cichego pominięcia ochrony. Publiczna konfiguracja odrzuca klucze testowe i wyłączoną weryfikację.
- **M2-CAP-06:** wymaganie obejmuje `/password/change/` i `/password/required/`, w tym INITIAL, RESET i EXPIRED. Bez poprawnego tokenu formularz nie uruchamia usługi zmiany hasła. Pierwsza zmiana hasła ADMIN i odzyskiwanie konta mają opisaną ścieżkę konfiguracji; komendy operatora pozostają bez widgetu.
- **M2-HONEY-01:** formularz logowania zawiera pole-pułapkę pomijane przez normalną nawigację i technologie asystujące, z wyłączonym autouzupełnianiem. Nie utrudnia prawidłowego wypełnienia formularza przez człowieka.
- **M2-HONEY-02:** niepusta wartość honeypotu powoduje odrzucenie na serwerze, zapis kategorii zdarzenia i brak weryfikacji hasła. Nie wykonujemy przez to płatnego/zewnętrznego sprawdzania CAPTCHA. Pominięcie pola przez klienta nie zastępuje CAPTCHA.

### Canarytokens i incydenty

- **M2-CAN-01:** istnieje rejestr konta-pułapki z zarezerwowanym, znormalizowanym loginem innym niż ADMIN i loginy użytkowników. Próba logowania tym loginem przy dowolnym haśle tworzy incydent. Pułapka nigdy nie tworzy sesji, nie ma roli ani dostępu do dokumentów.
- **M2-CAN-02:** incydent uruchamia zarejestrowany token HTTP Canarytokens i skutkuje zewnętrznym alertem do skonfigurowanego odbiorcy. Wykrywanie następuje po CSRF i walidacji rozmiaru danych, przed pozostałymi bramkami logowania, więc honeypot, CAPTCHA lub blokada nie maskują użycia pułapki. Odpowiedź pozostaje zwykłą odmową.
- **M2-CAN-03:** drugi, inny typ to dokument Word bez makr wygenerowany przez Canarytokens. Znajduje się poza zwykłą listą dokumentów aplikacji, w odrębnym katalogu testowym, bez prawdziwych danych. Odbiór wymaga jego otwarcia w obsługiwanej aplikacji i otrzymania osobnego alertu. W repozytorium jest instrukcja i opis dowodu, nie aktywny token lub jego adres.
- **M2-CAN-04:** każde użycie konta-pułapki zapisuje incydent, a dostarczenie sygnału ma stan oczekujący/wysłany/błąd, ograniczone ponowienia i odporność na duplikaty. Błąd sieci nie daje dostępu do konta i nie gubi zapisanego incydentu. Otrzymanie odpowiedzi HTTP z tokenu nie jest równoznaczne z dowodem otrzymania e-maila.
- **M2-CAN-05:** zdarzenia używają kategorii i czasu, bez haseł, tokenów CAPTCHA, URL-i Canarytokens, cookies i kluczy. Loginy/IP w materiale dowodowym są testowe lub zanonimizowane. Alert konta wyzwalany przez backend może wskazywać IP serwera; nie przedstawiamy go jako IP osoby atakującej. Rejestracja dostawców i odbiorcy nie jest wykonywana automatycznie przez aplikację.

### Testy i odbiór

- **M2-TEST-01:** ograniczony skrypt bota wykonuje żądania wyłącznie do własnej instancji demonstracyjnej. Domyślnie dopuszcza tylko loopback, ma maksymalną liczbę prób, timeout, niskie tempo i nie podąża za przekierowaniem do obcego hosta. Nie przełamuje CAPTCHA ani nie korzysta z usług jej rozwiązywania.
- **M2-TEST-02:** scenariusze rozdzielają honeypot, brak tokenu, błędny/zużyty token, próg konta, koniec blokady i konto-pułapkę. Prób zablokowanych wcześniej przez CAPTCHA nie przedstawiamy jako testu limitu haseł. Testy licznika używają kontrolowanej walidacji w izolowanym środowisku, bez furtki HTTP w zwykłej aplikacji.
- **M2-TEST-03:** wynik zestawia scenariusz, oczekiwaną warstwę ochrony, odpowiedź, dowód zdarzenia i rezultat PASS/FAIL/niezweryfikowane. Nie zawiera haseł ani aktywnych tokenów.
- **M2-TEST-04:** testy obejmują dokładne granice czasu, równoległe próby, brak enumeracji kont, dostępność formularzy i regresję modułu 1. Automatyka nie wymaga Internetu; rzeczywistą integrację i alerty sprawdzamy oddzielnie.

### Zakres dodatkowy

- **M2-IP-01:** opcjonalny limit błędnych logowań z jednego IP działa niezależnie od loginu, więc zmiana konta nie zeruje licznika. ADMIN ustawia osobny próg; domyślnie 20 błędów, blokada 15 minut. Porażki CAPTCHA/honeypotu nie są błędami hasła. Poprawne logowanie nie zeruje licznika IP.
- **M2-IP-02:** w bezpośrednim uruchomieniu używamy `REMOTE_ADDR`; nagłówki `X-Forwarded-For` nie są ufane. IPv4/IPv6 są normalizowane; test sprawdza podszywanie się nagłówkiem i współdzielenie adresu przez wielu użytkowników.
- **M2-IP-03:** blokada IP nie przedłuża się przez kolejne próby, nie blokuje istniejącej sesji i nie zastępuje limitu konta. Przy dwóch blokadach pokazujemy późniejszy termin umożliwiający ponowne logowanie. Ustawienie i dokumentacja jasno wskazują dodatkowy charakter funkcji.

### Sprawozdanie

- **M2-REP-01:** końcowym materiałem jest PDF: strona tytułowa (imię, nazwisko, grupa, indeks, moduł, przedmiot), teoria własnymi słowami, opis ćwiczeń, sposób walidacji Turnstile, oba tokeny, kluczowe fragmenty kodu, zrzuty, wyniki bota, wnioski i link do repozytorium lub archiwum kodu.
- **M2-REP-02:** odpowiedzi obejmują cztery pytania z załącznika: gotowe rozwiązania ochrony i ryzyka dostawcy, credential stuffing a spraying, blokada konta jako narzędzie odmowy usługi, mała liczba fałszywych alarmów honeytokenów i możliwe wyjątki (np. skaner).
- **M2-REP-03:** dowody pokazują blokadę z czasem, CAPTCHA logowania, CAPTCHA zmiany hasła, odmowę bez tokenu, dwa otrzymane alerty i wynik bota. Brakujące dane lub nieotrzymany alert pozostają jawną zależnością; nie deklarujemy pełnego odbioru na podstawie atrap.

## 3. Kolejność bramek i zgodność z modułem 1

POST logowania: CSRF → limity rozmiaru i normalizacja → wykrycie konta-pułapki → honeypot → aktywne blokady → CAPTCHA → atomowa weryfikacja/licznik → istniejące utworzenie pełnej lub ograniczonej sesji. Rejestr pułapek nie daje skrótu do udanego logowania. Dostawcy nie są wywoływani wewnątrz transakcji bazy.

W module 1 `AUTH-03` przewiduje jednolitą odmowę logowania; moduł 2 rozszerza ją wyłącznie o ogólną informację o czasowej blokadzie, także dla nieistniejących loginów. `SESS-07` nadal dotyczy bezczynności istniejącej sesji. Blokada prób logowania jest odrębnym mechanizmem i nie zmienia historii haseł ani administracyjnej blokady konta. CAPTCHA jest wyłączeniem z zakresu tylko dokumentu modułu 1; jej implementację określa niniejsza specyfikacja.

## 4. Kryteria odbioru

| ID | Sprawdzalne zachowanie | Wymagania |
|---|---|---|
| M2-AC-01 | Tylko ADMIN zapisuje poprawny próg, niepoprawny nie zmienia polityki | LOCK-01 |
| M2-AC-02 | N-ta błędna próba blokuje na 900 sekund; poprawne hasło podczas blokady nie loguje | LOCK-02–03 |
| M2-AC-03 | Kolejne próby nie wydłużają blokady; granica 900 sekund umożliwia ponowienie; sukces zeruje licznik | LOCK-03–04 |
| M2-AC-04 | Równoległe próby i zmiana progu nie omijają limitu; identyczne zachowanie dla nieistniejącego loginu | LOCK-05–06 |
| M2-AC-05 | Brak, błąd, replay, wygaśnięcie, zły host/akcja i awaria CAPTCHA odrzucają operację | CAP-01–05 |
| M2-AC-06 | Wszystkie cztery konteksty zmiany hasła wymagają tokenu; odmowa nie zmienia danych | CAP-06 |
| M2-AC-07 | Honeypot odrzuca przed hasłem/dostawcą; normalne użycie klawiaturą pozostaje możliwe | HONEY-01–02 |
| M2-AC-08 | Użycie konta-pułapki nie loguje i daje zapis incydentu oraz otrzymany alert HTTP | CAN-01–02, CAN-04–05 |
| M2-AC-09 | Otwarty dokument-token innego typu daje drugi otrzymany alert; opisano warunki działania | CAN-03 |
| M2-AC-10 | Bot ma ograniczony cel i tempo; raport rozdziela faktyczne wyniki warstw | TEST-01–03 |
| M2-AC-11 | Regresja modułu 1 oraz testy nowych granic i współbieżności przechodzą | TEST-04 |
| M2-AC-12 | PDF zawiera komplet materiałów i cztery odpowiedzi, bez sekretów i fikcyjnych dowodów | REP-01–03 |
| M2-AC-13, dodatkowe | Wiele loginów współdzieli limit IP, zmiana nagłówka go nie omija, granice działają | IP-01–03 |

W kolumnie wymagań pominięto wspólny prefiks `M2-`. Podstawowy odbiór wymaga M2-AC-01–12; M2-AC-13 dotyczy rozszerzenia. Aktualnie wszystkie kryteria są **niezweryfikowane**. Plan lub sam test jednostkowy integracji nie oznacza zakończenia modułu.
