from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from core.models import Project


class Command(BaseCommand):
    help = "Create sample owner accounts and reassign selected projects to the matching user."

    DEFAULT_USERS = {
        "trekky": {
            "password": "trekky123",
            "projects": ["Trekky", "Trekky Local"],
            "create_missing_project": None,
        },
        "gikky": {
            "password": "gikky123",
            "projects": ["Gikky"],
            "create_missing_project": {"name": "Gikky", "domain": "gikky.net"},
        },
    }

    def handle(self, *args, **options):
        User = get_user_model()

        for username, spec in self.DEFAULT_USERS.items():
            user, created = User.objects.get_or_create(username=username)
            user.set_password(spec["password"])
            if not user.is_staff:
                user.is_staff = True
            user.save()

            if created:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Created user "{username}" with default password "{spec["password"]}".'
                    )
                )
            else:
                self.stdout.write(
                    f'Updated password for existing user "{username}".'
                )

            create_spec = spec.get("create_missing_project")
            if create_spec:
                Project.objects.get_or_create(
                    name=create_spec["name"],
                    defaults={"owner": user, "domain": create_spec["domain"]},
                )

            if spec["projects"]:
                updated = Project.objects.filter(name__in=spec["projects"]).update(owner=user)
                self.stdout.write(
                    f'Assigned {updated} project(s) to "{username}": {", ".join(spec["projects"])}'
                )

        self.stdout.write("")
        self.stdout.write("Current project ownership:")
        for project in Project.objects.select_related("owner").order_by("name"):
            self.stdout.write(
                f"  - {project.name} (id={project.pk}, domain={project.domain or '-'}) -> {project.owner.username}"
            )
