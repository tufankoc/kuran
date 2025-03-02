from django.db import models
from django.utils.translation import gettext_lazy as _

class Surah(models.Model):
    """
    Kuran'daki sureleri temsil eden model.
    """
    number = models.PositiveIntegerField(unique=True, help_text=_('Sure numarası'))
    name_arabic = models.CharField(max_length=255, help_text=_('Surenin Arapça adı'))
    name_turkish = models.CharField(max_length=255, help_text=_('Surenin Türkçe adı'))
    name_english = models.CharField(max_length=255, help_text=_('Surenin İngilizce adı'))
    revelation_type = models.CharField(max_length=20, choices=[('Meccan', 'Mekki'), ('Medinan', 'Medeni')], help_text=_('Vahiy tipi'))
    verse_count = models.PositiveIntegerField(help_text=_('Ayet sayısı'))
    
    class Meta:
        verbose_name = _('Sure')
        verbose_name_plural = _('Sureler')
        ordering = ['number']
    
    def __str__(self):
        return f"{self.number}. {self.name_turkish}"

class Verse(models.Model):
    """
    Kuran'daki ayetleri temsil eden model.
    """
    surah = models.ForeignKey(Surah, on_delete=models.CASCADE, related_name='verses', help_text=_('Ait olduğu sure'))
    verse_number = models.PositiveIntegerField(help_text=_('Ayet numarası'))
    text_arabic = models.TextField(help_text=_('Ayetin Arapça metni'))
    text_turkish = models.TextField(help_text=_('Ayetin Türkçe meali'))
    text_transliteration = models.TextField(blank=True, null=True, help_text=_('Ayetin Latin harfleriyle okunuşu'))
    juz = models.PositiveIntegerField(help_text=_('Cüz numarası'))
    page = models.PositiveIntegerField(help_text=_('Sayfa numarası'))
    
    class Meta:
        verbose_name = _('Ayet')
        verbose_name_plural = _('Ayetler')
        ordering = ['surah__number', 'verse_number']
        unique_together = ['surah', 'verse_number']
    
    def __str__(self):
        return f"{self.surah.name_turkish} {self.verse_number}"
    
    @property
    def full_reference(self):
        """
        Ayetin tam referansını döndürür (örn. "2:255" - Bakara Suresi 255. Ayet)
        """
        return f"{self.surah.number}:{self.verse_number}"

class Tafsir(models.Model):
    """
    Ayetlerin tefsirlerini temsil eden model.
    """
    verse = models.ForeignKey(Verse, on_delete=models.CASCADE, related_name='tafsirs', help_text=_('Tefsir edilen ayet'))
    author = models.CharField(max_length=255, help_text=_('Tefsir yazarı'))
    text = models.TextField(help_text=_('Tefsir metni'))
    source = models.CharField(max_length=255, blank=True, null=True, help_text=_('Tefsir kaynağı'))
    
    class Meta:
        verbose_name = _('Tefsir')
        verbose_name_plural = _('Tefsirler')
        unique_together = ['verse', 'author']
    
    def __str__(self):
        return f"{self.verse} - {self.author} Tefsiri"
