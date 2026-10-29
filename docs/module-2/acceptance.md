# Odbiór modułu 2

Stan: 2026-10-29. E8 ukończone; pozostałe etapy oczekują na realizację. PASS automatyczny potwierdza opisane testy, a nie pełny odbiór modułu lub rzeczywistych usług zewnętrznych.

| Kryterium | Stan | Dowody |
|---|---|---|
| M2-AC-01 | PASS automatyczny | `tests/security/test_login_limit_ui.py`: zapis przez ADMIN, odmowa pozostałym rolom i CSRF, niepoprawne wartości bez zmiany polityki |
| M2-AC-02 | PASS automatyczny | `tests/security/test_login_limits.py`: N-ta próba i odmowa także poprawnego stałego, początkowego i tymczasowego hasła; pułap czasowy 900 sekund |
| M2-AC-03 | PASS automatyczny | testy dokładnej granicy, zerowania i braku przedłużania; testy HTTP licznika oraz `tests/js/login-lock.test.cjs` |
| M2-AC-04 | PASS automatyczny | rzeczywiste oddzielne połączenia SQLite: inkrementacje i blokada wobec trwającego logowania; zmiana progu po weryfikacji, takie same reguły dla nieistniejącego loginu |
| M2-AC-05 | Niezweryfikowane | E9: Turnstile |
| M2-AC-06 | Niezweryfikowane | E9: token w każdym kontekście zmiany hasła |
| M2-AC-07 | Niezweryfikowane | E9: honeypot i dostępność formularzy |
| M2-AC-08 | Niezweryfikowane | E10: konto-pułapka i otrzymany alert |
| M2-AC-09 | Niezweryfikowane | E10: dokument-token i drugi otrzymany alert |
| M2-AC-10 | Niezweryfikowane | E11: skrypt bota i rzeczywiste wyniki |
| M2-AC-11 | Częściowo | Regresja po E8 przechodzi; pełna regresja modułu 2 w T049 i T055 |
| M2-AC-12 | Niezweryfikowane | E13: sprawozdanie PDF i dowody |
| M2-AC-13 | Nierozpoczęte, dodatkowe | E12: limit IP |

Wyniki E8 i migracji opisano w [dzienniku weryfikacji](../verification.md). Lokalną migrację poprzedzono kopią w ignorowanym `.tools/backups/`; porównano wszystkie dotychczasowe kolumny i wiersze. Dopuszczono dodane przez Django wpisy typów treści i uprawnień nowych modeli. Konta, poświadczenia, dokumenty i istniejące ustawienia pozostały niezmienione.

Nie wykonywano testów na cudzych usługach, konfiguracji Turnstile ani wysyłania alertów. Testy JavaScript wykonują rzeczywisty plik skryptu w symulowanym DOM/zegarze; odbiór interfejsu w przeglądarce i zebranie zrzutów pozostają zadaniem T053.
