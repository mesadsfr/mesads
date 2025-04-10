import pyotp
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = (
        "Manage 2FA for users.\n\n"
        "Usage:\n"
        "  manage.py manage_2fa -l             List all users with 2FA enabled\n"
        "  manage.py manage_2fa -s EMAIL       Enable 2FA for the user with given email\n"
        "  manage.py manage_2fa -r EMAIL       Remove 2FA for the user with given email"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "-l", "--list", action="store_true", help="List all users with 2FA enabled"
        )
        parser.add_argument(
            "-s",
            "--set",
            metavar="EMAIL",
            help="Enable 2FA for the user with the given email",
        )
        parser.add_argument(
            "-r",
            "--remove",
            metavar="EMAIL",
            help="Remove 2FA for the user with the given email",
        )

    def handle(self, *args, **options):
        User = get_user_model()

        if not (options.get("list") or options.get("set") or options.get("remove")):
            self.stdout.write(self.style.WARNING(self.help))
            return

        if options.get("list"):
            users = User.objects.exclude(otp_secret="")
            self.stdout.write("Users with 2FA enabled:")
            for user in users:
                self.stdout.write(f" - {user.email}")

        if options.get("set"):
            email = options.get("set")
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"User with email '{email}' does not exist.")
                )
                return

            if user.otp_secret:
                self.stdout.write(f"User '{email}' already has 2FA enabled.")
            else:
                secret = pyotp.random_base32()
                user.otp_secret = secret
                user.save()
                self.stdout.write(
                    self.style.SUCCESS(f"2FA enabled for user '{email}'.")
                )

        if options.get("remove"):
            email = options.get("remove")
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"User with email '{email}' does not exist.")
                )
                return

            if not user.otp_secret:
                self.stdout.write(f"User '{email}' does not have 2FA enabled.")
            else:
                user.otp_secret = ""
                user.save()
                self.stdout.write(
                    self.style.SUCCESS(f"2FA removed for user '{email}'.")
                )
