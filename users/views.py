from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import logout
from .forms import UserRegisterForm, UserUpdateForm, ProfileUpdateForm
import time

def register(request):
    """
    Kullanıcı kayıt görünümü.
    """
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Hesabınız başarıyla oluşturuldu! Şimdi giriş yapabilirsiniz.')
            return redirect('users:login')
    else:
        form = UserRegisterForm()
    
    return render(request, 'users/register.html', {'form': form})

def custom_logout(request):
    """
    Özelleştirilmiş çıkış görünümü.
    """
    try:
        # Oturumu sonlandır
        logout(request)
        messages.success(request, 'Başarıyla çıkış yaptınız.')
    except Exception as e:
        # Hata durumunda log tut ve kullanıcıya bilgi ver
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Çıkış yapılırken hata oluştu: {str(e)}")
        messages.warning(request, 'Çıkış işlemi sırasında bir sorun oluştu, ancak çıkış yapıldı.')
    
    # Ana sayfaya yönlendir
    return redirect('home')

@login_required
def profile(request):
    """
    Kullanıcı profil görünümü.
    """
    # Kullanıcının çalışma istatistiklerini al
    from repetition.algorithm import SpacedRepetitionService
    statistics = SpacedRepetitionService.get_user_statistics(request.user)
    
    return render(request, 'users/profile.html', {
        'user': request.user,
        'statistics': statistics
    })

@login_required
def edit_profile(request):
    """
    Kullanıcı profil düzenleme görünümü.
    """
    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user)
        
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Profiliniz başarıyla güncellendi!')
            return redirect('users:profile')
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileUpdateForm(instance=request.user)
    
    return render(request, 'users/edit_profile.html', {
        'user_form': user_form,
        'profile_form': profile_form
    })
