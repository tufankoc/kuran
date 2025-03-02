from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.conf import settings
from quran.models import Verse
from django.db import transaction

class StudySession(models.Model):
    """
    Kullanıcının çalışma oturumlarını temsil eden model.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='study_sessions')
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    total_verses_studied = models.PositiveIntegerField(default=0)
    
    class Meta:
        verbose_name = _('Çalışma Oturumu')
        verbose_name_plural = _('Çalışma Oturumları')
        ordering = ['-start_time']
    
    def __str__(self):
        return f"{self.user.username} - {self.start_time.strftime('%d.%m.%Y %H:%M')}"
    
    def end_session(self):
        """
        Oturumu sonlandırır ve toplam çalışılan ayet sayısını günceller.
        """
        self.end_time = timezone.now()
        self.total_verses_studied = self.verse_studies.count()
        self.save()
    
    @property
    def duration(self):
        """
        Oturum süresini dakika cinsinden döndürür.
        """
        if not self.end_time:
            return None
        
        delta = self.end_time - self.start_time
        return delta.total_seconds() // 60

class VerseStudy(models.Model):
    """
    Kullanıcının belirli bir ayet üzerindeki çalışmasını temsil eden model.
    """
    DIFFICULTY_CHOICES = [
        (1, _('Çok Kolay')),
        (2, _('Kolay')),
        (3, _('Orta')),
        (4, _('Zor')),
        (5, _('Çok Zor')),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='verse_studies')
    verse = models.ForeignKey(Verse, on_delete=models.CASCADE, related_name='studies')
    session = models.ForeignKey(StudySession, on_delete=models.CASCADE, related_name='verse_studies', null=True, blank=True)
    first_studied_at = models.DateTimeField(auto_now_add=True)
    last_studied_at = models.DateTimeField(auto_now=True)
    next_review_date = models.DateField()
    easiness_factor = models.FloatField(default=2.5)
    interval = models.PositiveIntegerField(default=1)
    repetitions = models.PositiveIntegerField(default=0)
    difficulty = models.PositiveSmallIntegerField(choices=DIFFICULTY_CHOICES, default=3)
    is_memorized = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = _('Ayet Çalışması')
        verbose_name_plural = _('Ayet Çalışmaları')
        unique_together = ['user', 'verse']
        ordering = ['next_review_date']
    
    def __str__(self):
        return f"{self.user.username} - {self.verse}"
    
    def process_review(self, quality):
        """
        SM-2 algoritmasına göre tekrar zamanlamasını günceller.
        
        quality: 0-5 arası bir değer (0: tamamen unutulmuş, 5: mükemmel hatırlanıyor)
        """
        if quality < 0:
            quality = 0
        if quality > 5:
            quality = 5
        
        # Transaction içinde işlem yap
        with transaction.atomic():
            # Easiness factor güncelleme
            self.easiness_factor = max(1.3, self.easiness_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)))
            
            # Tekrar sayısını artır
            self.repetitions += 1
            
            # Interval hesaplama
            if quality < 3:
                # Eğer hatırlama zayıfsa, tekrar sayısını sıfırla
                self.repetitions = 0
                self.interval = 1
            else:
                # Hatırlama iyiyse, interval'i güncelle
                if self.repetitions == 1:
                    self.interval = 1
                elif self.repetitions == 2:
                    self.interval = 6
                else:
                    self.interval = round(self.interval * self.easiness_factor)
            
            # Bir sonraki tekrar tarihini hesapla
            self.next_review_date = timezone.now().date() + timezone.timedelta(days=self.interval)
            
            # Zorluk derecesini güncelle
            self.difficulty = 6 - quality if quality > 0 else 5
            
            # Ezberlendi mi?
            if quality >= 4 and self.repetitions >= 3:
                self.is_memorized = True
            
            # Tüm alanları belirterek kaydet
            self.save(update_fields=[
                'easiness_factor', 'repetitions', 'interval', 
                'next_review_date', 'difficulty', 'is_memorized',
                'last_studied_at'
            ])
        
        return self.next_review_date

class StudyProgress(models.Model):
    """
    Kullanıcının genel ilerleme durumunu temsil eden model.
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='study_progress')
    total_verses_studied = models.PositiveIntegerField(default=0)
    total_verses_memorized = models.PositiveIntegerField(default=0)
    total_study_time = models.PositiveIntegerField(default=0, help_text=_('Toplam çalışma süresi (dakika)'))
    longest_streak = models.PositiveIntegerField(default=0)
    current_streak = models.PositiveIntegerField(default=0)
    last_study_date = models.DateField(null=True, blank=True)
    
    class Meta:
        verbose_name = _('Çalışma İlerlemesi')
        verbose_name_plural = _('Çalışma İlerlemeleri')
    
    def __str__(self):
        return f"{self.user.username} İlerlemesi"
    
    def update_progress(self):
        """
        Kullanıcının ilerleme durumunu günceller.
        """
        # Toplam çalışılan ayet sayısı
        self.total_verses_studied = self.user.verse_studies.count()
        
        # Toplam ezberlenen ayet sayısı
        self.total_verses_memorized = self.user.verse_studies.filter(is_memorized=True).count()
        
        # Toplam çalışma süresi
        total_minutes = 0
        for session in self.user.study_sessions.filter(end_time__isnull=False):
            if session.duration:
                total_minutes += session.duration
        self.total_study_time = total_minutes
        
        # Streak güncelleme
        today = timezone.now().date()
        if self.last_study_date:
            days_since_last_study = (today - self.last_study_date).days
            
            if days_since_last_study == 0:
                # Bugün zaten çalışılmış, bir şey yapma
                pass
            elif days_since_last_study == 1:
                # Dün çalışılmış, streak'i artır
                self.current_streak += 1
                self.longest_streak = max(self.longest_streak, self.current_streak)
            else:
                # Streak kırıldı
                self.current_streak = 1
        else:
            # İlk çalışma
            self.current_streak = 1
            self.longest_streak = 1
        
        self.last_study_date = today
        self.save()
        
        # Kullanıcının streak'ini de güncelle
        self.user.streak = self.current_streak
        self.user.last_activity_date = today
        self.user.save(update_fields=['streak', 'last_activity_date'])
