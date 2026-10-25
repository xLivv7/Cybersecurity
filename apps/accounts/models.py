"""Project accounts with immutable logins and one protected administrator."""

from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import UserManager as DjangoUserManager
from django.core.exceptions import ValidationError
from django.db import models, router
from django.db.models import Q
from django.db.models.deletion import ProtectedError


class Role(models.TextChoices):
    ADMINISTRATOR = "ADMIN", "Administrator"
    MANAGER = "MANAGER", "Kierownik"
    EDITOR = "EDITOR", "Redaktor"
    EMPLOYEE = "EMPLOYEE", "Pracownik"
    READER = "READER", "Czytelnik"


class CredentialMode(models.TextChoices):
    INITIAL = "INITIAL", "Hasło początkowe"
    TEMPORARY = "TEMPORARY", "Hasło tymczasowe"
    PERMANENT = "PERMANENT", "Hasło stałe"


class UserQuerySet(models.QuerySet):
    def update(self, **kwargs):
        if {"username", "login_key"}.intersection(kwargs):
            raise ValidationError("Login po utworzeniu konta jest niezmienny.")
        return super().update(**kwargs)

    def bulk_update(self, objs, fields, batch_size=None):
        if {"username", "login_key"}.intersection(fields):
            raise ValidationError("Login po utworzeniu konta jest niezmienny.")
        return super().bulk_update(objs, fields, batch_size=batch_size)

    def bulk_create(
        self,
        objs,
        batch_size=None,
        ignore_conflicts=False,
        update_conflicts=False,
        update_fields=None,
        unique_fields=None,
    ):
        if {"username", "login_key"}.intersection(update_fields or ()):
            raise ValidationError("Login po utworzeniu konta jest niezmienny.")
        objs = list(objs)
        for obj in objs:
            obj._prepare_identity()
            obj.full_clean(validate_unique=False, validate_constraints=False)
        return super().bulk_create(
            objs,
            batch_size=batch_size,
            ignore_conflicts=ignore_conflicts,
            update_conflicts=update_conflicts,
            update_fields=update_fields,
            unique_fields=unique_fields,
        )

    def delete(self):
        protected = list(self.filter(login_key="admin"))
        if protected:
            raise ProtectedError("Konto ADMIN nie może zostać usunięte.", protected)
        return super().delete()


class UserManager(DjangoUserManager.from_queryset(UserQuerySet)):
    def get_by_natural_key(self, username):
        return self.get(login_key=self.model.normalize_username(username).casefold())

    async def aget_by_natural_key(self, username):
        return await self.aget(
            login_key=self.model.normalize_username(username).casefold()
        )

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        raise ValueError(
            "Projekt używa roli Administrator, bez superużytkowników Django."
        )

    async def acreate_superuser(
        self, username, email=None, password=None, **extra_fields
    ):
        raise ValueError(
            "Projekt używa roli Administrator, bez superużytkowników Django."
        )


class User(AbstractUser):
    Role = Role
    CredentialMode = CredentialMode

    login_key = models.CharField(
        "klucz loginu", max_length=450, unique=True, editable=False
    )
    role = models.CharField(
        "rola", max_length=10, choices=Role.choices, default=Role.READER
    )
    deleted_at = models.DateTimeField("usunięto", null=True, blank=True)
    password_changed_at = models.DateTimeField(
        "ostatnia zmiana hasła", null=True, blank=True
    )
    credential_mode = models.CharField(
        "tryb poświadczeń",
        max_length=10,
        choices=CredentialMode.choices,
        default=CredentialMode.TEMPORARY,
    )
    session_version = models.PositiveBigIntegerField("wersja sesji", default=1)

    objects = UserManager()

    class Meta(AbstractUser.Meta):
        abstract = False
        base_manager_name = "objects"
        default_manager_name = "objects"
        verbose_name = "użytkownik"
        verbose_name_plural = "użytkownicy"
        constraints = [
            models.CheckConstraint(
                condition=Q(role__in=Role.values), name="account_valid_role"
            ),
            models.CheckConstraint(
                condition=Q(credential_mode__in=CredentialMode.values),
                name="account_valid_credential_mode",
            ),
            models.CheckConstraint(
                condition=Q(is_staff=False, is_superuser=False),
                name="account_no_framework_privileges",
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        username="ADMIN",
                        login_key="admin",
                        role=Role.ADMINISTRATOR,
                        is_active=True,
                        deleted_at__isnull=True,
                    )
                    | (
                        ~Q(login_key="admin")
                        & ~Q(username__iexact="admin")
                        & ~Q(role=Role.ADMINISTRATOR)
                    )
                ),
                name="account_protected_admin",
            ),
            models.CheckConstraint(
                condition=Q(deleted_at__isnull=True) | Q(is_active=False),
                name="account_deleted_is_inactive",
            ),
            models.CheckConstraint(
                condition=~Q(credential_mode=CredentialMode.INITIAL)
                | Q(login_key="admin"),
                name="account_initial_only_admin",
            ),
            models.CheckConstraint(
                condition=Q(session_version__gte=1),
                name="account_positive_session_version",
            ),
            models.CheckConstraint(
                condition=~Q(username="") & ~Q(login_key=""),
                name="account_nonempty_identity",
            ),
        ]

    @classmethod
    def normalize_username(cls, username):
        # Login normalization is strip + casefold for lookup, never for passwords.
        return username.strip() if isinstance(username, str) else username

    def _prepare_identity(self):
        self.username = self.normalize_username(self.username)
        if not self.username or not isinstance(self.username, str):
            raise ValidationError({"username": "Login jest wymagany."})
        self.login_key = self.username.casefold()
        if self.login_key == "admin":
            self.username = "ADMIN"
        if self._state.adding and not self.password:
            self.set_unusable_password()

    def clean(self):
        self._prepare_identity()
        super().clean()
        errors = {}
        if self.pk is not None:
            previous = (
                type(self)
                .objects.using(self._state.db or router.db_for_read(type(self)))
                .filter(pk=self.pk)
                .values("username", "login_key")
                .first()
            )
            if previous and (
                previous["username"] != self.username
                or previous["login_key"] != self.login_key
            ):
                errors["username"] = "Login po utworzeniu konta jest niezmienny."
        if self.is_staff or self.is_superuser:
            errors["is_superuser"] = "Konta nie mają uprawnień frameworka Django."
        if self.login_key == "admin":
            if self.role != Role.ADMINISTRATOR:
                errors["role"] = "Konto ADMIN musi mieć rolę Administrator."
            if not self.is_active or self.deleted_at is not None:
                errors["is_active"] = (
                    "Konto ADMIN nie może być zablokowane ani usunięte."
                )
        elif self.role == Role.ADMINISTRATOR:
            errors["role"] = "Rola Administrator jest zarezerwowana dla konta ADMIN."
        if self.deleted_at is not None and self.is_active:
            errors["is_active"] = "Usunięte konto musi być nieaktywne."
        if self.credential_mode == CredentialMode.INITIAL and self.login_key != "admin":
            errors["credential_mode"] = "Hasło początkowe jest zarezerwowane dla ADMIN."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self._prepare_identity()
        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, using=None, keep_parents=False):
        using = using or self._state.db or router.db_for_write(type(self))
        protected = (
            type(self).objects.using(using).filter(pk=self.pk, login_key="admin")
        )
        if protected.exists():
            raise ProtectedError("Konto ADMIN nie może zostać usunięte.", [self])
        return super().delete(using=using, keep_parents=keep_parents)
