# Decyzje bezpieczeństwa

## Pełny i ograniczony dostęp

Pełna sesja używa logowania Django. Hasła INITIAL, TEMPORARY i wygasłe PERMANENT dają osobny kontekst zawierający identyfikatory, wersję, powód i czasy. Nie jest to uwierzytelniony użytkownik Django. Middleware dopuszcza mu tylko wymuszoną zmianę hasła i wylogowanie. Po zużyciu hasła tymczasowego utrata kontekstu wymaga nowego resetu.

## Wersjonowanie konta

Zmiana lub reset hasła, zmiana roli, blokada, odblokowanie i logiczne usunięcie zwiększają `session_version`. Chroniony widok odczytuje aktualną wersję z bazy. Stare ciasteczko nie odzyskuje uprawnień po odblokowaniu. Logowanie i przełączenie zakresu obracają identyfikator sesji oraz token CSRF.

## Historia po resecie

Ostatni hash hasła stałego pozostaje w `User.password`; poświadczenia tymczasowe mają osobną tabelę. Reset blokuje użycie hasła stałego przez zmianę trybu, zachowując możliwość sprawdzenia kandydata względem bieżącego i pięciu poprzednich haseł. Hasła początkowe operatora i tymczasowe nie zajmują miejsc w historii. Odległość liczymy od ponownie podanego hasła tymczasowego, nigdy od zapomnianego hasła ani hasha.

## Kontrola ról

Jedynym źródłem uprawnień jest jawna rola konta. ADMIN nie jest superużytkownikiem Django i nie dziedziczy dostępu do szkiców. Każdy serwis zapisu ponownie sprawdza aktora i stan obiektu. Formularze mają jawne listy pól; autor dokumentu pochodzi z kontekstu serwera. Nieznane operacje, role i stany są odrzucane.

## Transakcje i SQLite

Krótkie transakcje `IMMEDIATE`, warunkowe zapisy i liczba zmienionych rekordów chronią przed dwukrotnym zużyciem i nadpisaniem resetu starszą operacją. `select_for_update()` nie jest używane do ochrony SQLite. Kosztowne hashowanie odbywa się przed transakcją; wewnętrzny obiekt przygotowanego poświadczenia pozwala również panelowi i komendzie demo zachować tę zasadę w większej operacji atomowej. Konflikt/blokada nie daje dostępu ani częściowego zapisu. Testy używają niezależnych połączeń do plikowej bazy.

## Odpowiedzi i sekrety

Operacje zmiany stanu wymagają POST i CSRF. Chronione odpowiedzi i jednorazowe hasła mają `no-store`. Sekret jest przechowywany wyłącznie jako Argon2id z solą; jawna wartość istnieje tylko w pamięci i zamierzonej jednorazowej odpowiedzi/wyjściu komendy. Filtr błędów maskuje pola sekretów i ciasteczka także w lokalnym DEBUG. PUBLICZNE wdrożenie wymaga odrębnej konfiguracji HTTPS i proxy; nie jest częścią odbioru lokalnej wersji.
