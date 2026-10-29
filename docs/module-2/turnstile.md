# Konfiguracja Turnstile

Od E9 formularze logowania i zmiany hasła wymagają CAPTCHA. Aplikacja nie omija jej przy braku konfiguracji. Istniejące sesje zachowują reguły modułu 1.

1. W swoim panelu Cloudflare utwórz widget Turnstile i dodaj host używany do aplikacji, np. `localhost`. Wybierz tryb zarządzany. Nie wpisuj portu ani schematu do listy hostów.
2. Do prywatnego `.env` wpisz wartości `TURNSTILE_SITE_KEY`, `TURNSTILE_SECRET_KEY` i `TURNSTILE_ALLOWED_HOSTNAMES` z `.env.example`. Hosty muszą zgadzać się z adresem w przeglądarce i konfiguracją widgetu. Klucz sekretny pozostaje na serwerze; nie wysyłaj go do repozytorium ani do czatu.
3. Zastosuj migracje (`uv run --locked python manage.py migrate`) i uruchom ponownie serwer, aby wczytał zmienione środowisko. Otwórz aplikację pod skonfigurowanym hostem. Pola hostów nie zastępują `DJANGO_ALLOWED_HOSTS`.
4. Widget musi zakończyć weryfikację przed wysłaniem formularza. Po błędzie hasła formularz ma nowe wyzwanie. Przycisk „Ponów weryfikację CAPTCHA” odświeża wyzwanie; wygaśnięcie i błąd połączenia mają osobny komunikat. Bez JavaScript żądanie pozostanie odrzucone.

Akcje są ustawiane przez aplikację: `login`, `password_change`, `password_required`. Backend sprawdza zgodność hosta, akcji, czasu i jednorazowości. Nie konfiguruj globalnej akcji `test` dla rzeczywistego odbioru. Po awarii dostawcy ponów wyzwanie po przywróceniu połączenia; nie ma przełącznika wyłączającego ochronę.

Oficjalne klucze testowe służą do kontrolowanej próby widgetu i odpowiedzi dostawcy, a nie ochrony kont. Ich stałe tokeny/akcje mogą nie spełniać pełnego kontraktu formularzy i lokalnej ochrony replay. Produkcja ich nie przyjmuje. Automatyczne testy repozytorium zamiast Internetu używają jawnej fixture, która nadaje syntetyczne tokeny i podmienia wyłącznie transport Siteverify, zachowując właściwą walidację adaptera.

Przed pierwszym logowaniem ADMIN skonfiguruj widget, aby możliwa była również wymagana zmiana hasła początkowego. Komendy operatora `init_admin` i `recover_admin` działają lokalnie bez CAPTCHA; wydane poświadczenie nie omija CAPTCHA formularzy. Nie zmieniają one ustawień dostawcy. Dane istniejącego `.env` użytkowniczki pozostają niezmienione podczas implementacji.

Odbiór z rzeczywistymi kluczami, dostępnością widgetu i zrzutami należy do T053. Dotychczasowe wyniki offline nie są takim odbiorem.

Dokumentacja dostawcy: [walidacja serwerowa](https://developers.cloudflare.com/turnstile/get-started/server-side-validation/), [klucze testowe](https://developers.cloudflare.com/turnstile/troubleshooting/testing/).
