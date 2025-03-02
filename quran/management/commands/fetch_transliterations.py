import requests
import time
from django.core.management.base import BaseCommand
from quran.models import Verse, Surah
from django.db import transaction
import argparse
import re
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Kuran ayetlerinin Latin harfleriyle okunuşlarını (transliteration) API\'den çeker'

    def add_arguments(self, parser):
        parser.add_argument(
            '--surah',
            type=int,
            help='Sadece belirli bir sureyi işle (sure numarası)'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=10,
            help='Bir seferde işlenecek ayet sayısı (varsayılan: 10)'
        )
        parser.add_argument(
            '--sleep',
            type=float,
            default=0.5,
            help='Her API isteği arasındaki bekleme süresi (saniye, varsayılan: 0.5)'
        )

    def simple_transliterate(self, arabic_text):
        """
        Arapça metni basit bir şekilde Latin harflerine dönüştürür.
        Bu fonksiyon tam bir transliterasyon sağlamaz, sadece örnek amaçlıdır.
        Gerçek bir transliterasyon için daha kapsamlı bir kütüphane kullanılmalıdır.
        """
        # Arapça harflerin Latin karşılıkları (basitleştirilmiş)
        transliteration_map = {
            'ا': 'a', 'أ': 'a', 'إ': 'i', 'آ': 'aa',
            'ب': 'b', 'ت': 't', 'ث': 'th',
            'ج': 'j', 'ح': 'h', 'خ': 'kh',
            'د': 'd', 'ذ': 'dh', 'ر': 'r',
            'ز': 'z', 'س': 's', 'ش': 'sh',
            'ص': 's', 'ض': 'd', 'ط': 't',
            'ظ': 'z', 'ع': '\'', 'غ': 'gh',
            'ف': 'f', 'ق': 'q', 'ك': 'k',
            'ل': 'l', 'م': 'm', 'ن': 'n',
            'ه': 'h', 'و': 'w', 'ي': 'y',
            'ى': 'a', 'ة': 'h', 'ء': '\'',
            'َ': 'a', 'ُ': 'u', 'ِ': 'i',
            'ّ': '', 'ْ': '', 'ٰ': 'a',
            'ٱ': 'a', 'ً': 'an', 'ٌ': 'un',
            'ٍ': 'in', '۟': '', '۝': '',
            '۞': '', '﴾': '', '﴿': '',
            ' ': ' ', '\n': '\n'
        }
        
        # Özel Kuran kelimeleri için transliterasyonlar
        special_words = {
            'الله': 'Allah',
            'بسم': 'Bismillah',
            'الرحمن': 'ar-Rahman',
            'الرحيم': 'ar-Rahim',
            'محمد': 'Muhammad',
            'القرآن': 'al-Quran',
            'المؤمنون': 'al-Mu\'minun',
            'الكافرون': 'al-Kafirun'
        }
        
        # Önce özel kelimeleri kontrol et
        for arabic, latin in special_words.items():
            arabic_text = arabic_text.replace(arabic, latin)
        
        # Karakter karakter transliterasyon yap
        result = []
        for char in arabic_text:
            if char in transliteration_map:
                result.append(transliteration_map[char])
            else:
                result.append(char)  # Bilinmeyen karakterleri olduğu gibi bırak
        
        return ''.join(result)

    def handle(self, *args, **options):
        surah_filter = options.get('surah')
        batch_size = options.get('batch_size', 10)
        sleep_time = options.get('sleep', 0.5)
        
        # Tip dönüşümlerini kontrol et
        if surah_filter is not None:
            try:
                surah_filter = int(surah_filter)
            except (ValueError, TypeError):
                self.stdout.write(self.style.ERROR(f'Geçersiz sure numarası: {surah_filter}'))
                return
                
        if batch_size is not None:
            try:
                batch_size = int(batch_size)
            except (ValueError, TypeError):
                self.stdout.write(self.style.WARNING(f'Geçersiz batch size değeri: {batch_size}, varsayılan değer (10) kullanılıyor.'))
                batch_size = 10
                
        if sleep_time is not None:
            try:
                sleep_time = float(sleep_time)
            except (ValueError, TypeError):
                self.stdout.write(self.style.WARNING(f'Geçersiz sleep time değeri: {sleep_time}, varsayılan değer (0.5) kullanılıyor.'))
                sleep_time = 0.5
        
        if surah_filter:
            self.stdout.write(self.style.SUCCESS(f'Sadece {surah_filter} numaralı sure için okunuşlar çekiliyor...'))
            verses = Verse.objects.filter(surah__number=surah_filter).order_by('verse_number')
        else:
            self.stdout.write(self.style.SUCCESS('Tüm ayetlerin okunuşları (transliteration) çekiliyor...'))
            verses = Verse.objects.all().order_by('surah__number', 'verse_number')
        
        total_verses = verses.count()
        
        if total_verses == 0:
            self.stdout.write(self.style.WARNING('İşlenecek ayet bulunamadı.'))
            return
        
        # İşlem sayacı
        processed = 0
        success_count = 0
        error_count = 0
        
        # Ayetleri batch_size kadar grupla
        verse_batches = [verses[i:i+batch_size] for i in range(0, total_verses, batch_size)]
        total_batches = len(verse_batches)
        
        self.stdout.write(self.style.SUCCESS(f'Toplam {total_verses} ayet, {total_batches} grup halinde işlenecek.'))
        
        for batch_index, batch in enumerate(verse_batches):
            self.stdout.write(self.style.SUCCESS(f'Grup {batch_index+1}/{total_batches} işleniyor...'))
            
            # Her batch için ayrı bir transaction kullan
            with transaction.atomic():
                for verse in batch:
                    # API'den okunuş bilgisini çek
                    try:
                        # Quran.com API'sinden kelime kelime veri çekelim
                        words_url = f"https://api.quran.com/api/v4/verses/by_key/{verse.surah.number}:{verse.verse_number}?words=true&word_fields=text_uthmani,transliteration"
                        
                        self.stdout.write(self.style.SUCCESS(f"Kelime API isteği: {words_url}"))
                        
                        words_response = requests.get(words_url)
                        
                        if words_response.status_code == 200:
                            words_data = words_response.json()
                            
                            # API yanıtını logla
                            self.stdout.write(self.style.SUCCESS(f"Kelime API yanıtı alındı"))
                            
                            if 'verse' in words_data and 'words' in words_data['verse']:
                                # Kelime kelime transliterasyonu birleştir
                                transliteration_parts = []
                                
                                for word in words_data['verse']['words']:
                                    if 'transliteration' in word and word['transliteration'].get('text'):
                                        transliteration_parts.append(word['transliteration']['text'])
                                
                                transliteration_text = ' '.join(transliteration_parts)
                                
                                # Veritabanını güncelle
                                verse.text_transliteration = transliteration_text
                                verse.save(update_fields=['text_transliteration'])
                                
                                self.stdout.write(self.style.SUCCESS(
                                    f'Başarılı: {verse.full_reference} - {transliteration_text[:30]}...'
                                ))
                                
                                success_count += 1
                            else:
                                # Eğer kelime API'si başarısız olursa alternatif bir API deneyelim
                                # Transliterasyon için Quran.com API'sini kullanacağız (ID 40 transliteration için)
                                transliteration_url = f"https://api.quran.com/api/v4/quran/translations/40?verse_key={verse.surah.number}:{verse.verse_number}"
                                
                                self.stdout.write(self.style.SUCCESS(f"Alternatif Transliterasyon API isteği: {transliteration_url}"))
                                
                                transliteration_response = requests.get(transliteration_url)
                                
                                if transliteration_response.status_code == 200:
                                    transliteration_data = transliteration_response.json()
                                    
                                    if 'translations' in transliteration_data and len(transliteration_data['translations']) > 0:
                                        transliteration_text = transliteration_data['translations'][0]['text']
                                        
                                        # HTML etiketlerini temizle
                                        transliteration_text = re.sub(r'<[^>]+>', '', transliteration_text)
                                        
                                        # Veritabanını güncelle
                                        verse.text_transliteration = transliteration_text
                                        verse.save(update_fields=['text_transliteration'])
                                        
                                        self.stdout.write(self.style.SUCCESS(
                                            f'Alternatif API Başarılı: {verse.full_reference} - {transliteration_text[:30]}...'
                                        ))
                                        
                                        success_count += 1
                                    else:
                                        # Son çare olarak manuel transliterasyon yap
                                        arabic_url = f"https://api.alquran.cloud/v1/ayah/{verse.surah.number}:{verse.verse_number}/ar.alafasy"
                                        
                                        self.stdout.write(self.style.SUCCESS(f"Arapça Metin API isteği: {arabic_url}"))
                                        
                                        arabic_response = requests.get(arabic_url)
                                        
                                        if arabic_response.status_code == 200:
                                            arabic_data = arabic_response.json()
                                            
                                            if arabic_data['code'] == 200 and 'data' in arabic_data:
                                                arabic_text = arabic_data['data']['text']
                                                
                                                # Basit transliterasyon yap
                                                transliteration_text = self.simple_transliterate(arabic_text)
                                                
                                                # Veritabanını güncelle
                                                verse.text_transliteration = transliteration_text
                                                verse.save(update_fields=['text_transliteration'])
                                                
                                                self.stdout.write(self.style.SUCCESS(
                                                    f'Manuel Transliterasyon: {verse.full_reference} - {transliteration_text[:30]}...'
                                                ))
                                                
                                                success_count += 1
                                            else:
                                                self.stdout.write(self.style.WARNING(
                                                    f'Arapça Metin API Yanıt Hatası: {verse.full_reference} için veri bulunamadı'
                                                ))
                                        else:
                                            self.stdout.write(self.style.WARNING(
                                                f'Arapça Metin API Hatası: {verse.full_reference} için HTTP {arabic_response.status_code}'
                                            ))
                                else:
                                    self.stdout.write(self.style.WARNING(
                                        f'Alternatif API Hatası: {verse.full_reference} için HTTP {transliteration_response.status_code}'
                                    ))
                        else:
                            self.stdout.write(self.style.WARNING(
                                f'Kelime API Hatası: {verse.full_reference} için HTTP {words_response.status_code}'
                            ))
                        
                        processed += 1
                        
                        # API limitlerini aşmamak için kısa bir bekleme
                        time.sleep(sleep_time)
                    
                    except Exception as e:
                        error_count += 1
                        self.stdout.write(self.style.ERROR(f'Hata: {verse.full_reference} için okunuş çekilemedi - {str(e)}'))
                        logger.exception(f"Transliterasyon verisi çekilirken hata: {str(e)}")
            
            # Her batch sonrası ilerleme bilgisi
            self.stdout.write(self.style.SUCCESS(f'İşlenen ayet: {processed}/{total_verses} (Başarılı: {success_count}, Hata: {error_count})'))
            
            # Batch'ler arasında biraz daha uzun bekle
            time.sleep(1)
        
        self.stdout.write(self.style.SUCCESS(f'Tamamlandı! {success_count} ayet için okunuş bilgisi güncellendi. {error_count} ayet işlenemedi.')) 