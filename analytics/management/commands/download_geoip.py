"""Download the free DB-IP "IP to Country Lite" database (CC BY 4.0) used to tell a visit's country.

Run at deploy time. If the download fails the deploy still goes ahead: visits are counted without
a country until the next successful download.
"""
import gzip
import shutil
import tempfile
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

URL = "https://download.db-ip.com/free/dbip-country-lite-{month}.mmdb.gz"


def _months_to_try(today: date) -> list[str]:
    previous = date(today.year - (today.month == 1), (today.month - 2) % 12 + 1, 1)
    return [today.strftime("%Y-%m"), previous.strftime("%Y-%m")]


class Command(BaseCommand):
    help = "Download the DB-IP country database used by the visit statistics."

    def handle(self, *args, **options):
        target = Path(settings.ANALYTICS_GEOIP_PATH)
        target.parent.mkdir(parents=True, exist_ok=True)
        for month in _months_to_try(date.today()):
            url = URL.format(month=month)
            try:
                request = urllib.request.Request(url, headers={"User-Agent": "portfolio-analytics"})
                with urllib.request.urlopen(request, timeout=60) as response, tempfile.NamedTemporaryFile(
                    dir=target.parent, delete=False
                ) as compressed:
                    shutil.copyfileobj(response, compressed)
                with gzip.open(compressed.name, "rb") as source, tempfile.NamedTemporaryFile(
                    dir=target.parent, delete=False
                ) as unpacked:
                    shutil.copyfileobj(source, unpacked)
                Path(unpacked.name).replace(target)
                target.chmod(0o644)
                Path(compressed.name).unlink(missing_ok=True)
                self.stdout.write(self.style.SUCCESS(f"Country database {month} saved to {target}"))
                return
            except (urllib.error.URLError, OSError, EOFError) as exc:
                self.stdout.write(self.style.WARNING(f"Could not download {url}: {exc}"))
        self.stdout.write(self.style.WARNING("No country database downloaded; visits will have no country."))
