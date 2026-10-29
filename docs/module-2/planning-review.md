# Przegląd SDD i przygotowanie modułu 2

Data: 2026-10-29. Zakres: wersjonowanie istniejącej aplikacji i plan dalszych prac, bez implementacji modułu 2.

## Stan wejściowy

W `specs/` istniał wyłącznie katalog `001-identity-access` z trzema dokumentami. Wszystkie 35 zadań T001–T035 były zaznaczone jako wykonane. Kod E4–E7 oraz poprawka automatycznego wygaszania otwartej strony pozostawały w drzewie roboczym po ostatnim commicie T016. Nagłówki wskazywały jeszcze zmiany bez commita i starszą datę statusu.

Zapisano implementację i jej dowody w commicie `1cf5075` (`feat: complete module 1 accounts, documents and session expiry (T017-T035)`). Nagłówki zamkniętego modułu mają wersje spec 0.3, plan 0.2, tasks 0.21 i datę 2026-10-29. Historyczne wpisy z datą 2026-10-28 pozostają opisem ówczesnego stanu, co wyjaśnia sekcja zamknięcia zadań. Nie zmieniano lokalnych haseł, baz danych ani konfiguracji użytkowniczki. Nie wykonywano pushu.

## Wykonane zmiany planu

- Dodano `specs/README.md` jako indeks modułów i kolejności prac.
- Utworzono osobny katalog `002-attack-protection`: `source.md`, `spec.md`, `plan.md`, `tasks.md`.
- Odczytano wszystkie rozdziały i tabelę wariantów załącznika Word; zapisano nazwę, tytuł wewnętrzny i SHA-256 źródła. Rozdzielono obowiązki z załącznika, decyzje projektowe i dodatkowy limit IP.
- Przyjęto Turnstile na obu formularzach, domyślny próg pięciu błędów i dwa typy Canarytokens: konto-pułapkę z tokenem HTTP oraz dokument Word bez makr. To wybory dopuszczone zakresem, nie dodatkowe wymagania prowadzącego.
- Powiązano 29 wymagań z 13 kryteriami odbioru i zadaniami T036–T055 w etapach E8–E13. Dwa zadania IP są dodatkowe; implementacja wszystkich nowych zadań jest oznaczona jako nierozpoczęta.
- Zachowano bazę modułu 1 i opisano jawnie rozszerzenie ogólnego komunikatu logowania o blokadę, różnicę między blokadą logowania a bezczynnością sesji oraz ochronę wszystkich kontekstów zmiany hasła.
- Rozdzielono automatyczne testy adapterów od realnej CAPTCHA i rzeczywiście otrzymanych alertów. Zaplanowano skrypt bota, wymagane zrzuty, cztery odpowiedzi kontrolne i końcowy PDF.

## Weryfikacja

Ostatni pełny wynik aplikacji: **265 testów PASS**, opisany w `docs/verification.md`; po nim nie zmieniano kodu aplikacji. W tej sesji ponownie przeszły: `manage.py check`, `makemigrations --check --dry-run` (brak zmian), Ruff i formatowanie 86 plików.

Kontrola dokumentacji: 35 zamkniętych zadań modułu 1, dokładnie T036–T055 bez duplikatów, 20 pustych pól wyboru, komplet czterech pól opisowych każdego nowego zadania, 29 unikalnych wymagań, 13 kryteriów oraz 62 istniejące lokalne odsyłacze w specyfikacjach i README. `git diff --check` końcowej zmiany dokumentacji nie zgłasza błędów. Nie tworzono PDF, widgetów, aktywnych tokenów ani fałszywych dowodów odbioru.

Najbliższy krok to T036. Przed odbiorami zewnętrznymi potrzebne będą rzeczywiste klucze i dozwolony host Turnstile, oba tokeny Canarytokens, odbiorca alertów i jego potwierdzenie. Dane autora i przedmiotu są potrzebne dopiero do T054. Zależności te są jawne w zadaniach i nie blokują rozpoczęcia implementacji modeli.
