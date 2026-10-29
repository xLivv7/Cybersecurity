"""Local initialization never accepts a password on the command line."""

from getpass import getpass

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.views.decorators.debug import sensitive_variables

from apps.accounts.models import User


class Command(BaseCommand):
    help = "Utwórz chronione konto ADMIN (hasło podawane w ukrytym polu)."

    @sensitive_variables()
    def handle(self, *args, **options):
        if User.objects.filter(login_key="admin").exists():
            raise CommandError("Konto ADMIN już istnieje. Użyj recover_admin.")
        secret = getpass("Hasło początkowe ADMIN: ")
        confirmation = getpass("Powtórz hasło: ")
        if secret != confirmation:
            raise CommandError("Podane hasła różnią się.")
        try:
            validate_password(secret)
            user = User(
                username="ADMIN",
                role=User.Role.ADMINISTRATOR,
                credential_mode=User.CredentialMode.INITIAL,
            )
            user.set_password(secret)
            with transaction.atomic():
                user.save()
        except ValidationError as error:
            raise CommandError("; ".join(error.messages)) from None
        self.stdout.write("Utworzono ADMIN. Pierwsze logowanie wymaga zmiany hasła.")
