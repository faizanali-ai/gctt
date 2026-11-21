from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Upload, read, sign and delete a tiny file to verify media storage."

    def handle(self, *args, **options):
        storage = default_storage
        backend = f"{storage.__class__.__module__}.{storage.__class__.__name__}"
        self.stdout.write(f"Backend: {backend}")
        if not settings.DEBUG and "FileSystemStorage" in backend:
            raise CommandError(
                "Remote media storage is required in production; "
                "FileSystemStorage cannot delete or serve résumés."
            )

        name = "healthcheck/storage-check.txt"
        try:
            saved = storage.save(name, ContentFile(b"gctt storage check"))
            content = storage.open(saved).read()
            url = storage.url(saved)
            storage.delete(saved)
        except Exception as exc:
            raise CommandError(f"Storage check FAILED: {exc}") from exc

        if content != b"gctt storage check":
            raise CommandError("Storage check FAILED: uploaded content did not round-trip")

        self.stdout.write(f"Uploaded: {saved}")
        self.stdout.write(f"Signed URL: {url[:120]}")
        self.stdout.write(self.style.SUCCESS("Storage check passed."))
