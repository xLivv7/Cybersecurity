# Odbiór modułu 2

Stan: 2026-10-29. E8–E9 ukończone lokalnie; pozostałe etapy oczekują na realizację. PASS automatyczny potwierdza opisane testy, a nie pełny odbiór modułu lub rzeczywistych usług zewnętrznych.

| Kryterium | Stan | Dowody |
|---|---|---|
| M2-AC-01 | PASS automatyczny | `tests/security/test_login_limit_ui.py`: zapis przez ADMIN, odmowa pozostałym rolom i CSRF, niepoprawne wartości bez zmiany polityki |
| M2-AC-02 | PASS automatyczny | `tests/security/test_login_limits.py`: N-ta próba i odmowa także poprawnego stałego, początkowego i tymczasowego hasła; pułap czasowy 900 sekund |
| M2-AC-03 | PASS automatyczny | testy dokładnej granicy, zerowania i braku przedłużania; testy HTTP licznika oraz `tests/js/login-lock.test.cjs` |
| M2-AC-04 | PASS automatyczny | rzeczywiste oddzielne połączenia SQLite: inkrementacje i blokada wobec trwającego logowania; zmiana progu po weryfikacji, takie same reguły dla nieistniejącego loginu |
| M2-AC-05 | PASS automatyczny, realny odbiór w T053 | `test_captcha.py`, `test_login_captcha.py`, `test_captcha_flows.py`: token, host/akcja, granica czasu, sieć, replay i współbieżność |
| M2-AC-06 | PASS automatyczny, realny odbiór w T053 | `test_password_captcha.py`: 16 przypadków standardowej zmiany oraz INITIAL/RESET/EXPIRED, brak mutacji przy odmowie |
| M2-AC-07 | PASS automatyczny, odbiór klawiaturą w T053 | pole HiddenInput poza nawigacją; kolejność bramek w HTTP; test rzeczywistego skryptu widgetu w symulowanym DOM |
| M2-AC-08 | Niezweryfikowane | E10: konto-pułapka i otrzymany alert |
| M2-AC-09 | Niezweryfikowane | E10: dokument-token i drugi otrzymany alert |
| M2-AC-10 | Niezweryfikowane | E11: skrypt bota i rzeczywiste wyniki |
| M2-AC-11 | Częściowo | Regresja po E9: 374 pytest i 8 JavaScript PASS; pełna regresja modułu 2 w T049 i T055 |
| M2-AC-12 | Niezweryfikowane | E13: sprawozdanie PDF i dowody |
| M2-AC-13 | Nierozpoczęte, dodatkowe | E12: limit IP |

Wyniki E8–E9 i migracji opisano w [dzienniku weryfikacji](../verification.md). Lokalną migrację poprzedzono kopią w ignorowanym `.tools/backups/`; porównano wszystkie dotychczasowe kolumny i wiersze. Dopuszczono dodane przez Django wpisy typów treści i uprawnień nowych modeli. Konta, poświadczenia, dokumenty i istniejące ustawienia pozostały niezmienione.

Nie wykonywano testów na cudzych usługach, konfiguracji Turnstile ani wysyłania alertów. Testy JavaScript wykonują rzeczywisty plik skryptu w symulowanym DOM/zegarze; odbiór interfejsu w przeglądarce i zebranie zrzutów pozostają zadaniem T053.

Po E9 nie ma jeszcze rzeczywistych kluczy Turnstile w lokalnym .env. Formularze bez nich odrzucają operacje; instrukcja: [konfiguracja](turnstile.md). Nie uznajemy mocków ani kluczy testowych za dowód działania usługi z rzeczywistą konfiguracją. Lokalna migracja 0005 została zastosowana po kopii zapasowej i porównaniu dotychczasowych danych.
