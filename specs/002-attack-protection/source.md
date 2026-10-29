# Źródło wymagań i decyzje modułu 2

Data: 2026-10-29. Status: analiza załącznika i przyjęte założenia do implementacji.

Źródłem wymagań jest przekazany przez użytkowniczkę plik **Moduł 2 – Zabezpieczenia przed atakami.docx**. Tytuł wewnętrzny: „Moduł 2 - Zabezpieczenia przed botami, ruchem automatycznym i wyciekiem danych”. Odczytano treść wszystkich sześciu rozdziałów i tabelę dziesięciu wariantów. Dokument nie zawiera obrazów. Plik źródłowy pozostaje w Downloads; dokumentacja projektu jest przenośna i nie wymaga tej lokalizacji.

SHA-256 źródła: `cbe0cf52b5da495c9f2c620a81e0659838a92648010e06ba467de3005980da22`.

## Powiązanie z załącznikiem

| Miejsce w załączniku | Wymaganie | Dokumentacja projektu |
|---|---|---|
| Rozdz. 2, limit błędnych logowań | Próg ustawiany przez administratora, blokada 15 minut, pozostały czas | M2-LOCK-01–06; T036–T038 |
| Rozdz. 2–3, CAPTCHA logowania | Gotowy dostawca lub własny wariant, jednorazowość i termin | M2-CAP-01–05; T039–T040, T042 |
| Rozdz. 2, zmiana hasła | Zewnętrzna CAPTCHA i odrzucenie formularza bez poprawnego tokenu | M2-CAP-06; T041–T042 |
| Rozdz. 2, pułapka na boty | Ukryte pole logowania wykrywa automat | M2-HONEY-01–02; T040 |
| Rozdz. 2, Canarytokens | Dwa różne typy, w tym konto-pułapka i otrzymany alert | M2-CAN-01–05; T043–T046 |
| Rozdz. 2, test | Bot na własnej aplikacji i zestawienie działania zabezpieczeń | M2-TEST-01–04; T047–T049 |
| Rozdz. 2, zadanie dodatkowe | Limit per IP niezależny od loginu | M2-IP-01–03; T050–T051, dodatkowe |
| Rozdz. 4 | Odpowiedzi na cztery pytania kontrolne | M2-REP-02; T054 |
| Rozdz. 5 | Sprawozdanie PDF z kodem, zrzutami, alertami i wnioskami | M2-REP-01–03; T052–T055 |

## Przyjęte decyzje i granice zakresu

1. **Cloudflare Turnstile na obu formularzach.** Załącznik dopuszcza go zamiast reCAPTCHA. Dzięki gotowemu dostawcy wariant indywidualny CAPTCHA nie jest wymagany; w sprawozdaniu wpisujemy „nie dotyczy — gotowe rozwiązanie Turnstile”. To decyzja projektu, a nie nakaz konkretnego dostawcy w załączniku.
2. **Domyślny próg pięciu błędów.** Załącznik nie podaje wartości; administrator może ustawić dodatnią liczbę całkowitą. Blokada ma stałe 15 minut, niezależnie od 15-minutowego limitu bezczynności sesji z modułu 1.
3. **Dwa typy Canarytokens: HTTP powiązany z kontem-pułapką i dokument Word bez makr.** Konto jest odrębnym wpisem pułapki, bez możliwości uzyskania sesji użytkownika. Jego użycie tworzy incydent i uruchamia token HTTP przez serwer. Drugi token jest prawdziwym dokumentem wygenerowanym przez Canarytokens, przechowywanym w izolowanym katalogu demonstracyjnym, poza zwykłą listą dokumentów aplikacji.
4. **IP jako zakres dodatkowy.** Zaplanowany osobno, bez przedstawiania go jako obowiązkowego warunku ukończenia podstawy. Nie obejmuje konfiguracji reverse proxy bez znanej topologii.
5. **Jawne rozdzielenie testów i odbioru zewnętrznego.** Mocki i klucze testowe nie potwierdzają rzeczywistej ochrony przed botami ani dostarczenia alertu. Odbiór wymaga realnego widgetu i dwóch otrzymanych alertów. Potrzebne będą klucze Turnstile, adres odbiorcy Canarytokens i dane do strony tytułowej sprawozdania; nie są potrzebne do rozpoczęcia kodowania.

## Sprawdzone źródła techniczne

Sprawdzono 2026-10-29. To dokumentacja integracji; zakres ocenianych ćwiczeń wynika z załącznika.

- [Turnstile — walidacja na serwerze](https://developers.cloudflare.com/turnstile/get-started/server-side-validation/): Siteverify, jednorazowy token ważny 300 sekund, kontrola `hostname` i `action`.
- [Turnstile — testowanie](https://developers.cloudflare.com/turnstile/troubleshooting/testing/): oddzielne klucze do kontrolowanych testów; nie stanowią rzeczywistej ochrony demonstracji.
- [Canarytokens — token HTTP](https://docs.canarytokens.org/guide/http-token): wywołanie unikatowego adresu uruchamia alert. Integracja konta-pułapki z takim adresem jest rozwiązaniem naszej aplikacji.
- [Canarytokens — dokumenty Office](https://help.canary.tools/hc/en-gb/articles/10905485310109-Canarytoken-Overview-and-Use-Cases): zależność działania od aplikacji i dostępu do DNS/HTTP. Odbiór dokumentu sprawdzamy w obsługiwanym programie, nie w podglądzie HTML.
