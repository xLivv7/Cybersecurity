"""Idempotent local demo accounts, with opt-in credential reset."""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.views.decorators.debug import sensitive_variables

from apps.accounts.models import User
from apps.accounts.services import account_action, create_account
from apps.documents.models import Document
from apps.security.services import prepare_temporary_credential

DEMO_ACCOUNTS = [
    ("kierownik", User.Role.MANAGER, "Karolina", "Kierownik"),
    ("redaktor", User.Role.EDITOR, "Robert", "Redaktor"),
    ("pracownik1", User.Role.EMPLOYEE, "Anna", "Pracownik"),
    ("pracownik2", User.Role.EMPLOYEE, "Piotr", "Pracownik"),
    ("czytelnik1", User.Role.READER, "Maria", "Czytelnik"),
    ("czytelnik2", User.Role.READER, "Jan", "Czytelnik"),
]


class Command(BaseCommand):
    help = "Utwórz lokalną demonstrację. Nowe hasła pokazuje tylko raz."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset-passwords",
            action="store_true",
            help="Jawnie zresetuj istniejące konta demo (bez ADMIN).",
        )

    @sensitive_variables()
    def handle(self, *args, **options):
        if not getattr(settings, "ALLOW_DEMO_DATA", False):
            raise CommandError(
                "Dane demo są dozwolone wyłącznie w konfiguracji lokalnej."
            )
        admin = User.objects.filter(login_key="admin").first()
        if admin is None:
            raise CommandError("Najpierw wykonaj init_admin.")
        for login, role, first, last in DEMO_ACCOUNTS:
            existing = User.objects.filter(login_key=login).first()
            if existing and (
                existing.deleted_at is not None
                or existing.role != role
                or not existing.is_active
            ):
                raise CommandError(
                    f"Konto {login} ma inny stan lub rolę. Nie zmieniono demonstracji."
                )
        prepared = {
            login: prepare_temporary_credential()
            for login, role, first, last in DEMO_ACCOUNTS
            if options["reset_passwords"]
            or not User.objects.filter(login_key=login).exists()
        }
        credentials, users = [], {}
        with transaction.atomic():
            for login, role, first, last in DEMO_ACCOUNTS:
                user = User.objects.filter(login_key=login).first()
                if user is None:
                    user, issued = create_account(
                        admin,
                        username=login,
                        first_name=first,
                        last_name=last,
                        role=role,
                        _prepared=prepared[login],
                    )
                    credentials.append((login, issued.secret))
                elif options["reset_passwords"]:
                    issued = account_action(
                        admin, user.pk, "reset", _prepared=prepared[login]
                    )
                    credentials.append((login, issued.secret))
                users[login] = user
            for login, title, body, status in [
                (
                    "kierownik",
                    "Witaj w laboratorium bezpieczeństwa",
                    "To opublikowany dokument dostępny dla każdej roli. Sprawdź pozostałe funkcje na własnym koncie.",
                    "PUBLISHED",
                ),
                (
                    "pracownik1",
                    "Plan prac Anny",
                    "Szkic pierwszego pracownika. Kierownik i Redaktor mogą go przeczytać i edytować.",
                    "DRAFT",
                ),
                (
                    "pracownik2",
                    "Notatki Piotra",
                    "Szkic drugiego pracownika. Inny Pracownik nie ma do niego dostępu.",
                    "DRAFT",
                ),
            ]:
                Document.objects.get_or_create(
                    author=users[login],
                    title=title,
                    defaults={"body": body, "status": status},
                )
        for login, secret in credentials:
            self.stdout.write(f"{login}: {secret}")
        self.stdout.write(
            "Demonstracja gotowa: 6 kont, dokument opublikowany i szkice. Nowe hasła są ważne 4 godziny i pokazane tylko raz. ADMIN bez zmian."
        )
