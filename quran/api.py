import requests
import logging
from django.conf import settings
from .models import Surah, Verse, Tafsir

logger = logging.getLogger(__name__)

class QuranAPIService:
    """
    Kuran verilerini harici API'den çekmek için servis sınıfı.
    """
    BASE_URL = "https://api.alquran.cloud/v1"
    
    @classmethod
    def fetch_all_surahs(cls):
        """
        Tüm sureleri API'den çeker ve veritabanına kaydeder.
        """
        try:
            # Sureleri çek
            response = requests.get(f"{cls.BASE_URL}/surah")
            if response.status_code != 200:
                logger.error(f"API'den sureler çekilemedi. Durum kodu: {response.status_code}")
                return False
            
            data = response.json()
            if data['code'] != 200:
                logger.error(f"API'den sureler çekilemedi. API kodu: {data['code']}")
                return False
            
            # Sureleri veritabanına kaydet
            for surah_data in data['data']:
                surah, created = Surah.objects.update_or_create(
                    number=surah_data['number'],
                    defaults={
                        'name_arabic': surah_data['name'],
                        'name_english': surah_data['englishName'],
                        'name_turkish': surah_data.get('turkishName', surah_data['englishName']),  # API'de Türkçe isim yoksa İngilizce ismi kullan
                        'revelation_type': surah_data['revelationType'],
                        'verse_count': surah_data['numberOfAyahs']
                    }
                )
                
                if created:
                    logger.info(f"Yeni sure eklendi: {surah}")
                else:
                    logger.info(f"Sure güncellendi: {surah}")
            
            return True
        
        except Exception as e:
            logger.exception(f"Sureler çekilirken hata oluştu: {str(e)}")
            return False
    
    @classmethod
    def fetch_surah_verses(cls, surah_number):
        """
        Belirli bir surenin ayetlerini API'den çeker ve veritabanına kaydeder.
        """
        try:
            # Surenin var olduğunu kontrol et
            try:
                surah = Surah.objects.get(number=surah_number)
            except Surah.DoesNotExist:
                logger.error(f"Sure bulunamadı: {surah_number}")
                return False
            
            # Arapça ayetleri çek
            arabic_response = requests.get(f"{cls.BASE_URL}/surah/{surah_number}")
            if arabic_response.status_code != 200:
                logger.error(f"API'den Arapça ayetler çekilemedi. Durum kodu: {arabic_response.status_code}")
                return False
            
            arabic_data = arabic_response.json()
            if arabic_data['code'] != 200:
                logger.error(f"API'den Arapça ayetler çekilemedi. API kodu: {arabic_data['code']}")
                return False
            
            # Türkçe mealleri çek (Türkçe çeviri için farklı bir endpoint kullanılabilir)
            turkish_response = requests.get(f"{cls.BASE_URL}/surah/{surah_number}/tr.diyanet")
            if turkish_response.status_code != 200:
                logger.error(f"API'den Türkçe ayetler çekilemedi. Durum kodu: {turkish_response.status_code}")
                return False
            
            turkish_data = turkish_response.json()
            if turkish_data['code'] != 200:
                logger.error(f"API'den Türkçe ayetler çekilemedi. API kodu: {turkish_data['code']}")
                return False
            
            # Ayetleri veritabanına kaydet
            arabic_verses = arabic_data['data']['ayahs']
            turkish_verses = turkish_data['data']['ayahs']
            
            for i in range(len(arabic_verses)):
                arabic_verse = arabic_verses[i]
                turkish_verse = turkish_verses[i] if i < len(turkish_verses) else {'text': ''}
                
                verse, created = Verse.objects.update_or_create(
                    surah=surah,
                    verse_number=arabic_verse['numberInSurah'],
                    defaults={
                        'text_arabic': arabic_verse['text'],
                        'text_turkish': turkish_verse['text'],
                        'juz': arabic_verse['juz'],
                        'page': arabic_verse['page']
                    }
                )
                
                if created:
                    logger.info(f"Yeni ayet eklendi: {verse}")
                else:
                    logger.info(f"Ayet güncellendi: {verse}")
            
            return True
        
        except Exception as e:
            logger.exception(f"Ayetler çekilirken hata oluştu: {str(e)}")
            return False
    
    @classmethod
    def fetch_all_verses(cls):
        """
        Tüm surelerin ayetlerini API'den çeker ve veritabanına kaydeder.
        """
        try:
            # Önce tüm sureleri çek
            if not cls.fetch_all_surahs():
                logger.error("Sureler çekilemediği için ayetler çekilemedi.")
                return False
            
            # Her sure için ayetleri çek
            for surah in Surah.objects.all():
                if not cls.fetch_surah_verses(surah.number):
                    logger.error(f"{surah} için ayetler çekilemedi.")
                    continue
            
            return True
        
        except Exception as e:
            logger.exception(f"Tüm ayetler çekilirken hata oluştu: {str(e)}")
            return False 