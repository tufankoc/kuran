from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser

class UserRegisterForm(UserCreationForm):
    """
    Kullanıcı kayıt formu.
    """
    email = forms.EmailField()
    
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password1', 'password2']
        
    def __init__(self, *args, **kwargs):
        super(UserRegisterForm, self).__init__(*args, **kwargs)
        # Form alanları için Türkçe etiketler
        self.fields['username'].label = 'Kullanıcı Adı'
        self.fields['email'].label = 'E-posta Adresi'
        self.fields['password1'].label = 'Parola'
        self.fields['password2'].label = 'Parola Onayı'

class UserUpdateForm(forms.ModelForm):
    """
    Kullanıcı bilgilerini güncelleme formu.
    """
    email = forms.EmailField()
    
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'first_name', 'last_name', 'daily_goal']
        labels = {
            'username': 'Kullanıcı Adı',
            'email': 'E-posta Adresi',
            'first_name': 'Ad',
            'last_name': 'Soyad',
            'daily_goal': 'Günlük Hedef (Ayet Sayısı)'
        }

class ProfileUpdateForm(forms.ModelForm):
    """
    Kullanıcı profil bilgilerini güncelleme formu.
    """
    class Meta:
        model = CustomUser
        fields = ['profile_picture', 'date_of_birth', 'bio']
        labels = {
            'profile_picture': 'Profil Resmi',
            'date_of_birth': 'Doğum Tarihi',
            'bio': 'Hakkımda'
        }
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'bio': forms.Textarea(attrs={'rows': 4})
        } 