# Odbiór lokalnej wersji aplikacji

Data: 2026-10-28. Zmiany robocze, bez nowych commitów i bez publikacji.

Uzupełnienie 2026-10-29: dodano licznik i automatyczne opuszczenie wygasłej strony (SESS-07). Aktualny pełny zestaw: **265 testów przeszło w 47,53 s**. Scenariusze skryptu sprawdzono oddzielnie w Node z symulowanym DOM, zegarem i odpowiedziami serwera; nie jest to dodatkowy ręczny odbiór w przeglądarce. Szczegóły w `docs/verification.md`.

## Kontrole automatyczne

Pełny zestaw: **256 testów przeszło w 80,63 s**. Ruff, formatowanie, kontrola Django, brakujących migracji i `git diff --check` przeszły. Workflow obejmuje pełny pytest (w tym współbieżność), Ruff i migracje na Windows i Linux; `actionlint` nie zgłasza błędów. Zdalnego CI nie uruchamiano, ponieważ nie wykonywano publikacji ani pushu.

Testy używają rzeczywistego Argon2id, izolowanych baz i kontrolowanego zegara. Testy wyścigów mają oddzielne połączenia do plikowej bazy i bariery/zdarzenia, bez oczekiwania godzinami. Przekrojowe testy T031 uzupełniają istniejące przypadki o CSRF dokumentów, bezpieczny adres powrotu, pełny reset administracyjny z historią i sesjami, odblokowanie oraz nawigację. T032 potwierdza wcześniejsze testy granic i wyścigów w tym samym pełnym zestawie.

## E4 — konta i ustawienia (T017–T021)

Komendy `init_admin` i `recover_admin` korzystają z lokalnego operatora i nie przyjmują sekretu w argumentach. Inicjalizacja waliduje hasło i potwierdzenie; odzyskanie wymaga wpisania ADMIN. Panel kont ma listę, tworzenie i edycję z jawnymi polami. Blokada, odblokowanie, reset i logiczne usunięcie mają formularze potwierdzenia z nazwą konta i skutkiem. Serwisy sprawdzają aktualną rolę administratora i wersję aktora; nie ma obejścia ochrony ADMIN. Login pozostaje zarezerwowany po usunięciu, a autorstwo dokumentów zachowane.

Hasło tymczasowe pojawia się jeden raz w odpowiedzi z `no-store`; nie trafia do sesji, wiadomości Django ani adresów. Ustawienia obejmują trzy pola i odrzucają niepoprawne zakresy/ułamki. Przygotowanie hashy przed transakcją pozwala zachować atomowość tworzenia konta i resetu bez kosztownego hashowania podczas blokady zapisu.

Dowody: `tests/accounts/test_management.py`, `tests/test_acceptance.py`, wcześniejsze `tests/accounts/test_models.py` i `tests/security/test_session_limits.py`.

## E5 — dokumenty i RBAC (T022–T026)

Migracja `documents.0001_initial` tworzy tytuł, tekst, autora, stan i daty. Autor jest chroniony przez PROTECT; logiczne usunięcie konta nie usuwa dokumentów. Macierz operacji jest jawna i domyślnie odmawia dostępu. Administrator nie ma uprawnień redakcyjnych. Listy są filtrowane na serwerze, a szczegóły zwracają 403 albo 404 bez ujawnienia niedozwolonej treści. Formularze nie przyjmują autora i stanu szkicu; serwisy ponownie sprawdzają użytkownika i stan wewnątrz transakcji. Publikacja/wycofanie są osobnymi POST.

Dowody: `tests/documents/test_access.py::test_matrix_through_http` obejmuje 5 ról × 2 stany × własny/cudzy dokument i sprawdza odczyt, listę, tworzenie, edycję, publikację, wycofanie oraz brak usuwania. Dodatkowo sprawdzono autora, niezmienność stanu po odmowie, HTML, ograniczone sesje i usunięcie autora. `tests/test_acceptance.py` wymusza rzeczywisty CSRF.

## E6 — interfejs i demonstracja (T027–T030)

Wspólne szablony mają polską nawigację zależną od roli, widoczny fokus, przejście do treści, etykiety, tekstowe błędy i komunikaty. Siatki dostosowują się do szerokości, a tabela kont przewija się we własnym kontenerze. Strony 403/404 mają własny wygląd i nie pokazują treści wyjątku ani dokumentu.

`seed_demo` tworzy 1 Kierownika, 1 Redaktora, 2 Pracowników i 2 Czytelników poza ADMIN oraz publikację i szkice dwóch autorów. Ponowne wykonanie nie duplikuje danych i nie zmienia haseł bez `--reset-passwords`. Dane są dozwolone tylko przy lokalnym `ALLOW_DEMO_DATA`. Sprawdzono format, role, powtarzalność, reset i brak modyfikacji ADMIN w `tests/accounts/test_demo.py`.

### Przegląd w prawdziwej przeglądarce

Użyto osobnej bazy `.tools/qa.sqlite3` i serwera QA na `127.0.0.1:8018`; lokalna baza aplikacji nie została zmieniona. Sprawdzono:

- logowanie i pulpit ADMIN, listę kont oraz formularz ustawień;
- Kierownika: listę, utworzenie szkicu, publikację i wycofanie;
- Redaktora: odczyt i edycję szkicu bez przycisku publikacji;
- Pracownika: własny szkic i publikację na liście; bezpośrednie wejście w cudzy szkic daje stronę 403 bez treści;
- Czytelnika: publikację bez tworzenia szkicu;
- pierwsze logowanie hasłem tymczasowym i ograniczony formularz zmiany;
- wylogowanie, fokus klawiatury i przejście do treści;
- dokument z `<script>`: znacznik pozostaje widocznym tekstem, bez wykonania skryptu;
- szeroki ekran i viewport 390 × 844; dokument i formularz nie wychodzą poza szerokość strony.

Podgląd pulpitu zapisano w ignorowanym `.tools/qa-dashboard.png`. Nie zapisano haseł w materiałach weryfikacyjnych. Zmiana hasła i operacje administracyjne są dodatkowo w pełni przetestowane przez HTTP w izolowanych testach.

**T030 ukończono:** użytkowniczka osobiście zmieniła hasło testowego `pracownik1`, następnie potwierdziła udane ponowne logowanie i pokazała pulpit z rolą Pracownik. W bazie QA potwierdzono tryb PERMANENT i datę zmiany hasła. Agent nie otrzymał nowego hasła. Przegląd przeglądarki i scenariusze HTTP zamykają odbiór interfejsu.

## E7 — czysta kopia i dokumentacja (T031–T035)

README opisuje rzeczywiste komendy instalacji, migracji, inicjalizacji, odzyskania i demo, role, formularze oraz kontrole. `docs/decisions/security.md` opisuje ograniczone sesje, wersjonowanie, historię po resecie, brak superużytkownika, transakcje i ochronę sekretów.

Utworzono czystą kopię **bieżących niezacommitowanych źródeł**, nie archiwum starego HEAD, zgodnie z prośbą o brak commitów. Kopia `.tools/acceptance-omuv6z_a` zawiera 106 plików źródłowych, bez `.git`, `.vscode`, środowiska, sekretów, cache i lokalnej bazy. Z `uv.lock` odtworzono osobne `.venv` w trybie offline z cache. W kopii przeszły:

- Ruff i formatowanie (84 pliki Pythona), Django i brakujące migracje;
- migracje na pustej bazie, inicjalizacja ADMIN, dane demo i powtarzalność;
- pierwsza zmiana ADMIN, ponowne logowanie, panel kont i odzyskiwanie odbierające starej sesji dostęp;
- **pełny pytest: 256 testów w 72,99 s**.

Sekrety bootstrapu były generowane tylko w pamięci procesu i nie zostały wypisane ani skopiowane do źródeł. Nie wykonywano commita, pushu ani publicznego wdrożenia. Linux i zdalne CI pozostają do sprawdzenia po publikacji; pierwszy start na nowym komputerze wymaga źródła zależności lub odpowiedniego cache.

T035 ukończono po ręcznym potwierdzeniu T030. Wszystkie zadania T001–T035 mają wynik i dowód odbioru. Zmiany T017–T035 pozostają bez commita zgodnie z instrukcją użytkowniczki.

## Kryteria AC-01–AC-31

Wynik PASS oznacza potwierdzenie zachowania testem automatycznym; uwagi o ręcznym odbiorze nie są ukryte przez tę tabelę.

| Kryterium | Wynik | Dowód |
|---|---|---|
| AC-01 | PASS | `tests/accounts/test_login.py::test_refusals_share_one_message` |
| AC-02 | PASS | `tests/accounts/test_sessions.py::test_full_login_rotates_key_and_protects_dashboard`, macierz dokumentów |
| AC-03 | PASS | `test_restricted_context_has_no_full_access`, ograniczony formularz w przeglądarce |
| AC-04 | PASS | `test_minimum_length_boundary`, `test_rejection_shows_errors_and_preserves_account` |
| AC-05 | PASS | `test_minimum_length_boundary` (14 znaków) |
| AC-06 | PASS | `test_confirmation_and_old_secret_must_match_exactly`, testy formularzy |
| AC-07 | PASS | ten sam test oraz HTTP z błędnym starym hasłem |
| AC-08 | PASS | `tests/security/test_levenshtein.py::test_threshold` (3) |
| AC-09 | PASS | `test_threshold` (4), `test_four_edits_pass_and_other_sessions_lose_access` |
| AC-10 | PASS | `test_disabling_rule_only_disables_distance_check`, panel ustawień |
| AC-11 | PASS | `test_five_newest_history_entries_are_checked`, `test_admin_reset_preserves_history_and_revokes_real_sessions` |
| AC-12 | PASS | `test_issue_format_hash_deadline_and_no_logged_secret`, panel kont i demo |
| AC-13 | PASS | `test_expiration_exact_boundary`, `test_consumption_boundary_and_repeat` |
| AC-14 | PASS | `test_two_connections_can_consume_only_once`, dwa klienty przy logowaniu |
| AC-15 | PASS | `test_complete_change_flow`, bootstrap czystej kopii i osobista zmiana hasła oraz ponowne logowanie potwierdzone przez użytkowniczkę |
| AC-16 | PASS | `test_admin_reset_preserves_history_and_revokes_real_sessions`, wyścigi resetu |
| AC-17 | PASS | `tests/documents/test_access.py::test_matrix_through_http` (Czytelnik) |
| AC-18 | PASS | macierz własności Pracownika, 403 potwierdzone również w przeglądarce |
| AC-19 | PASS | macierz Redaktor/Kierownik; publikacja i wycofanie w przeglądarce |
| AC-20 | PASS | macierz Administratora dla szkiców |
| AC-21 | PASS | testy limitów/stanu konta, edycja roli w panelu, `test_unblock_never_restores_invalidated_session` |
| AC-22 | PASS | `tests/accounts/test_models.py`, `test_create_edit_block_delete_and_reset_services` |
| AC-23 | PASS | `test_logout_requires_post_and_csrf_and_invalidates_server_session` |
| AC-24 | PASS | `test_full_idle_boundary`, brak odnowienia na granicy |
| AC-25 | PASS | `test_activity_renews_but_policy_shortening_applies_immediately` |
| AC-26 | PASS | test skrócenia bezczynności i `test_expiry_policy_downgrades_existing_full_context` |
| AC-27 | PASS | `test_password_expiry_boundary_in_existing_session`, ścieżka EXPIRED przez HTTP |
| AC-28 | PASS | modele hashy, `test_credentials_do_not_appear_in_sessions_logs_or_redirects`, raport błędu DEBUG |
| AC-29 | PASS | `test_document_csrf_author_and_state_are_protected`, CSRF panelu i zmiany hasła |
| AC-30 | PASS | `test_text_is_escaped_and_authentication_cannot_be_bypassed`, znacznik skryptu w przeglądarce |
| AC-31 | PASS automatyczny | czysta kopia, nowe środowisko, migracje, ADMIN, demo i 256 testów |
