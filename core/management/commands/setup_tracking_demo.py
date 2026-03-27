from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from core.models import Project


class Command(BaseCommand):
    help = "Create a demo project so you can test /user/track-test/ and the ingestion API."

    def add_arguments(self, parser):
        parser.add_argument(
            "--username",
            default="admin",
            help="User who will own the demo project (default: admin).",
        )

    def handle(self, *args, **options):
        User = get_user_model()
        username = options["username"]
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stderr.write(
                self.style.ERROR(
                    f'User "{username}" does not exist. Create one first, e.g.:\n'
                    "  python manage.py createsuperuser"
                )
            )
            return

        project, created = Project.objects.get_or_create(
            owner=user,
            name="Demo tracking",
            defaults={"domain": "localhost"},
        )
        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Created project "{project.name}" (id={project.pk}, tracking_id={project.tracking_id})'
                )
            )
        else:
            self.stdout.write(
                f'Using existing project "{project.name}" (id={project.pk}, tracking_id={project.tracking_id})'
            )

        port = getattr(settings, "DEV_SERVER_PORT", 8777)
        base = f"http://127.0.0.1:{port}"
        self.stdout.write("")
        self.stdout.write("Next steps:")
        self.stdout.write("  1. .\\run_dev.ps1   (or: .\\venv\\Scripts\\python manage.py runserver 127.0.0.1:%s)" % port)
        self.stdout.write(f"  2. Log in at {base}/user/login/")
        self.stdout.write(
            f"  3. Open {base}/user/track-test/{project.pk}/ and click the links"
        )
        self.stdout.write(
            f"  4. Check stats at {base}/user/projects/{project.pk}/"
        )
