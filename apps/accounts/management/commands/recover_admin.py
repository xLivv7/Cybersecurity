"""Recovery requires local operator access and explicit confirmation."""

from django.core.management.base import BaseCommand, CommandError
from django.views.decorators.debug import sensitive_variables

from apps.accounts.models import User
from apps.security.services import issue_temporary_credential


class Command(BaseCommand):
    help = "Odzyskaj ADMIN: unieważnij sesje i wydaj hasło ważne 4 godziny."

    @sensitive_variables()
    def handle(self, *args, **options):
        user = User.objects.filter(login_key="admin").first()
        if user is None:
            raise CommandError("Najpierw wykonaj init_admin.")
        if (
            input("Wpisz ADMIN, aby potwierdzić reset i unieważnienie sesji: ").strip()
            != "ADMIN"
        ):
            raise CommandError("Anulowano odzyskiwanie.")
        issued = issue_temporary_credential(user.pk)
        self.stdout.write(
            f"Hasło tymczasowe ADMIN (4 godziny, pokazane jeden raz): {issued.secret}"
        )
