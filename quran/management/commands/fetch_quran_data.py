from django.core.management.base import BaseCommand, CommandError
from quran.api import QuranAPIService
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'API\'den Kuran verilerini çeker ve veritabanına kaydeder'

    def add_arguments(self, parser):
        parser.add_argument(
            '--surah',
            type=int,
            help='Belirli bir surenin ayetlerini çekmek için sure numarası'
        )

    def handle(self, *args, **options):
        surah_number = options.get('surah')
        
        if surah_number:
            self.stdout.write(self.style.NOTICE(f"{surah_number} numaralı surenin ayetleri çekiliyor..."))
            success = QuranAPIService.fetch_surah_verses(surah_number)
            if success:
                self.stdout.write(self.style.SUCCESS(f"{surah_number} numaralı surenin ayetleri başarıyla çekildi."))
            else:
                raise CommandError(f"{surah_number} numaralı surenin ayetleri çekilemedi.")
        else:
            self.stdout.write(self.style.NOTICE("Tüm Kuran verileri çekiliyor..."))
            
            self.stdout.write(self.style.NOTICE("Sureler çekiliyor..."))
            success = QuranAPIService.fetch_all_surahs()
            if not success:
                raise CommandError("Sureler çekilemedi.")
            self.stdout.write(self.style.SUCCESS("Sureler başarıyla çekildi."))
            
            self.stdout.write(self.style.NOTICE("Ayetler çekiliyor..."))
            success = QuranAPIService.fetch_all_verses()
            if not success:
                raise CommandError("Ayetler çekilemedi.")
            self.stdout.write(self.style.SUCCESS("Ayetler başarıyla çekildi."))
            
            self.stdout.write(self.style.SUCCESS("Tüm Kuran verileri başarıyla çekildi.")) 