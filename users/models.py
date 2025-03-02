from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _

class CustomUser(AbstractUser):
    """
    Özel kullanıcı modeli.
    """
    email = models.EmailField(_('email address'), unique=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/', null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    bio = models.TextField(max_length=500, blank=True)
    
    # Kuran öğrenme ile ilgili özel alanlar
    daily_goal = models.PositiveIntegerField(default=5, help_text=_('Günlük hedeflenen ayet sayısı'))
    streak = models.PositiveIntegerField(default=0, help_text=_('Kesintisiz çalışma günü sayısı'))
    last_activity_date = models.DateField(null=True, blank=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    def __str__(self):
        return self.email
    
    class Meta:
        verbose_name = _('Kullanıcı')
        verbose_name_plural = _('Kullanıcılar')
