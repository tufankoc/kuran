import logging
from datetime import timedelta
from django.utils import timezone
from django.db.models import Q
from .models import VerseStudy, StudyProgress
from django.db import transaction
from quran.models import Surah, Verse

logger = logging.getLogger(__name__)

class SpacedRepetitionService:
    """
    Aralıklı tekrar algoritmasını uygulayan servis sınıfı.
    """
    
    @staticmethod
    def get_verses_to_review(user):
        """
        Kullanıcının bugün tekrar etmesi gereken ayetleri döndürür.
        """
        today = timezone.now().date()
        
        # Bugün tekrar edilmesi gereken ayetler
        verses_to_review = VerseStudy.objects.filter(
            user=user,
            next_review_date__lte=today
        ).select_related('verse', 'verse__surah').order_by('next_review_date')
        
        return verses_to_review
    
    @staticmethod
    def get_new_verses_to_study(user, limit=5):
        """
        Kullanıcının henüz çalışmadığı yeni ayetleri döndürür.
        """
        # Kullanıcının zaten çalıştığı ayetler
        studied_verse_ids = VerseStudy.objects.filter(user=user).values_list('verse_id', flat=True)
        
        # Henüz çalışılmamış ayetler
        new_verses = Verse.objects.exclude(id__in=studied_verse_ids).select_related('surah').order_by('surah__number', 'verse_number')[:limit]
        
        return new_verses
    
    @staticmethod
    def process_verse_review(user, verse_id, quality):
        """
        Kullanıcının ayet tekrarını işler ve bir sonraki tekrar tarihini belirler.
        
        quality: 0-5 arası bir değer (0: tamamen unutulmuş, 5: mükemmel hatırlanıyor)
        """
        try:
            with transaction.atomic():
                verse_study = VerseStudy.objects.select_for_update().get(user=user, verse_id=verse_id)
                next_review_date = verse_study.process_review(quality)
                
                # Kullanıcının ilerleme durumunu güncelle
                try:
                    progress = StudyProgress.objects.select_for_update().get(user=user)
                except StudyProgress.DoesNotExist:
                    progress = StudyProgress.objects.create(user=user)
                
                progress.update_progress()
            
            return next_review_date
        
        except VerseStudy.DoesNotExist:
            logger.error(f"Kullanıcı {user.username} için {verse_id} ID'li ayet çalışması bulunamadı.")
            return None
        except Exception as e:
            logger.error(f"Ayet tekrarı işlenirken hata oluştu: {str(e)}")
            return None
    
    @staticmethod
    def start_new_verse_study(user, verse_id, session=None):
        """
        Kullanıcı için yeni bir ayet çalışması başlatır.
        """
        from quran.models import Verse
        
        try:
            # Transaction içinde işlem yap
            with transaction.atomic():
                # Ayetin var olduğunu kontrol et
                verse = Verse.objects.get(id=verse_id)
                
                # Zaten çalışılmış mı kontrol et - transaction içinde kontrol et
                if VerseStudy.objects.filter(user=user, verse=verse).exists():
                    logger.warning(f"Kullanıcı {user.username} zaten {verse} ayetini çalışıyor.")
                    return None
                
                # Yeni çalışma oluştur
                verse_study = VerseStudy(
                    user=user,
                    verse=verse,
                    session=session,
                    next_review_date=timezone.now().date(),  # İlk tekrar bugün
                    easiness_factor=2.5,
                    interval=1,
                    repetitions=0,
                    difficulty=3,
                    is_memorized=False
                )
                verse_study.save(force_insert=True)
                
                # Kullanıcının ilerleme durumunu güncelle
                try:
                    progress = StudyProgress.objects.select_for_update().get(user=user)
                except StudyProgress.DoesNotExist:
                    progress = StudyProgress.objects.create(user=user)
                
                progress.update_progress()
                
                return verse_study
        
        except Exception as e:
            logger.error(f"Ayet çalışması başlatılırken hata oluştu: {str(e)}")
            return None
    
    @staticmethod
    def get_daily_study_plan(user):
        """
        Kullanıcı için günlük çalışma planı oluşturur.
        """
        # Bugün tekrar edilmesi gereken ayetler
        verses_to_review = SpacedRepetitionService.get_verses_to_review(user)
        
        # Kullanıcının günlük hedefi
        daily_goal = user.daily_goal
        
        # Eğer tekrar edilecek ayet sayısı günlük hedeften azsa, yeni ayetler ekle
        if verses_to_review.count() < daily_goal:
            new_verses_needed = daily_goal - verses_to_review.count()
            new_verses = SpacedRepetitionService.get_new_verses_to_study(user, limit=new_verses_needed)
        else:
            new_verses = []
        
        return {
            'verses_to_review': verses_to_review,
            'new_verses': new_verses,
            'total_verses': verses_to_review.count() + len(new_verses)
        }
    
    @staticmethod
    def get_user_statistics(user):
        """
        Kullanıcının çalışma istatistiklerini döndürür.
        """
        try:
            progress = StudyProgress.objects.get(user=user)
        except StudyProgress.DoesNotExist:
            progress = StudyProgress.objects.create(user=user)
        
        # Bugün tekrar edilmesi gereken ayetler
        today = timezone.now().date()
        verses_due_today = VerseStudy.objects.filter(user=user, next_review_date__lte=today).count()
        
        # Yarın tekrar edilecek ayetler
        tomorrow = today + timedelta(days=1)
        verses_due_tomorrow = VerseStudy.objects.filter(user=user, next_review_date=tomorrow).count()
        
        # Haftalık tekrar edilecek ayetler
        next_week = today + timedelta(days=7)
        verses_due_next_week = VerseStudy.objects.filter(
            user=user, 
            next_review_date__gt=today,
            next_review_date__lte=next_week
        ).count()
        
        # Zorluk seviyelerine göre ayetler
        difficulty_distribution = {
            'very_easy': VerseStudy.objects.filter(user=user, difficulty=1).count(),
            'easy': VerseStudy.objects.filter(user=user, difficulty=2).count(),
            'medium': VerseStudy.objects.filter(user=user, difficulty=3).count(),
            'hard': VerseStudy.objects.filter(user=user, difficulty=4).count(),
            'very_hard': VerseStudy.objects.filter(user=user, difficulty=5).count(),
        }
        
        # Ezberlenmiş ayetler
        memorized_verses_count = VerseStudy.objects.filter(user=user, is_memorized=True).count()
        
        # Çalışılan sureler
        studied_surahs = VerseStudy.objects.filter(user=user).values_list('verse__surah', flat=True).distinct()
        studied_surahs_count = len(studied_surahs)
        
        # Bugün tekrar edilecek ayetler
        due_today_count = verses_due_today
        
        return {
            'total_verses_studied': progress.total_verses_studied,
            'total_verses_memorized': progress.total_verses_memorized,
            'total_study_time': progress.total_study_time,
            'current_streak': progress.current_streak,
            'longest_streak': progress.longest_streak,
            'last_study_date': progress.last_study_date,
            'verses_due_today': verses_due_today,
            'verses_due_tomorrow': verses_due_tomorrow,
            'verses_due_next_week': verses_due_next_week,
            'difficulty_distribution': difficulty_distribution,
            'memorized_verses_count': memorized_verses_count,
            'studied_surahs_count': studied_surahs_count,
            'due_today_count': due_today_count,
        }
        
    @staticmethod
    def add_entire_surah_to_study(user, surah_id, session=None):
        """
        Bir surenin tüm ayetlerini kullanıcının çalışma listesine ekler.
        """
        try:
            # Sureyi al (transaction dışında)
            surah = Surah.objects.get(id=surah_id)
            
            # Surenin tüm ayetlerini al (transaction dışında)
            verses = list(Verse.objects.filter(surah=surah).order_by('verse_number'))
            
            # Kullanıcının zaten çalıştığı ayetleri al (transaction dışında)
            existing_studies = set(VerseStudy.objects.filter(
                user=user,
                verse__surah=surah
            ).values_list('verse_id', flat=True))
            
            # Transaction içinde işlem yap
            added_count = 0
            existing_count = 0
            
            # Bugünün tarihini al
            today = timezone.now().date()
            
            # Toplu ekleme için liste oluştur
            verse_studies_to_create = []
            
            # Önce listeyi hazırla (transaction dışında)
            for verse in verses:
                if verse.id in existing_studies:
                    existing_count += 1
                    continue
                
                # Yeni çalışma nesnesi oluştur
                verse_study = VerseStudy(
                    user=user,
                    verse=verse,
                    session=session,
                    next_review_date=today,
                    easiness_factor=2.5,
                    interval=1,
                    repetitions=0,
                    difficulty=3,
                    is_memorized=False
                )
                
                verse_studies_to_create.append(verse_study)
                added_count += 1
            
            # Eğer eklenecek ayet yoksa, transaction'a gerek yok
            if not verse_studies_to_create:
                return {
                    'added_count': 0,
                    'existing_count': existing_count,
                    'total_count': len(verses)
                }
            
            # Küçük parçalar halinde ekle
            batch_size = 20
            for i in range(0, len(verse_studies_to_create), batch_size):
                batch = verse_studies_to_create[i:i+batch_size]
                
                # Her batch için ayrı transaction kullan
                with transaction.atomic():
                    VerseStudy.objects.bulk_create(batch)
            
            # İlerleme durumunu güncelle (ayrı transaction)
            if added_count > 0:
                with transaction.atomic():
                    try:
                        progress = StudyProgress.objects.select_for_update().get(user=user)
                    except StudyProgress.DoesNotExist:
                        progress = StudyProgress.objects.create(user=user)
                    
                    progress.update_progress()
            
            return {
                'added_count': added_count,
                'existing_count': existing_count,
                'total_count': len(verses)
            }
        
        except Exception as e:
            logger.error(f"Sure çalışmaya eklenirken hata oluştu: {str(e)}")
            return None 