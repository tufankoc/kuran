from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.contrib import messages
from django.views.decorators.http import require_POST
from .models import StudySession, VerseStudy, StudyProgress
from quran.models import Verse, Surah
from .algorithm import SpacedRepetitionService
from django.db import transaction
import logging
import threading

logger = logging.getLogger(__name__)

@login_required
def dashboard(request):
    """
    Kullanıcı dashboard görünümü.
    """
    # Kullanıcının çalışma istatistiklerini al
    statistics = SpacedRepetitionService.get_user_statistics(request.user)
    
    # Bugün çalışılacak ayetleri al
    due_today = SpacedRepetitionService.get_verses_to_review(request.user)
    due_today_count = due_today.count()
    
    # Ezberlenmiş ayetleri say
    memorized_count = VerseStudy.objects.filter(user=request.user, is_memorized=True).count()
    
    # Toplam çalışılan ayet sayısı
    total_verses_count = VerseStudy.objects.filter(user=request.user).count()
    
    # Son eklenen ayetleri al
    recently_added = VerseStudy.objects.filter(user=request.user).order_by('-first_studied_at')[:5]
    
    # Aktif çalışma oturumu var mı kontrol et
    active_session = StudySession.objects.filter(user=request.user, end_time__isnull=True).first()
    
    return render(request, 'repetition/dashboard.html', {
        'statistics': statistics,
        'due_today': due_today,
        'due_today_count': due_today_count,
        'memorized_count': memorized_count,
        'total_verses_count': total_verses_count,
        'recently_added': recently_added,
        'active_session': active_session
    })

@login_required
def start_session(request):
    """
    Yeni bir çalışma oturumu başlatır.
    """
    # Aktif oturum var mı kontrol et
    active_session = StudySession.objects.filter(user=request.user, end_time__isnull=True).first()
    
    if active_session:
        messages.warning(request, 'Zaten aktif bir çalışma oturumunuz var.')
        return redirect('repetition:dashboard')
    
    # Yeni oturum oluştur
    session = StudySession.objects.create(user=request.user)
    messages.success(request, 'Çalışma oturumu başlatıldı.')
    
    return redirect('repetition:daily_plan')

@login_required
def end_session(request):
    """
    Çalışma oturumunu sonlandırır.
    """
    # Aktif oturumu bul
    session = StudySession.objects.filter(user=request.user, end_time__isnull=True).first()
    
    if not session:
        messages.warning(request, 'Aktif bir çalışma oturumunuz bulunmamaktadır.')
    elif session.end_time:
        messages.warning(request, 'Bu oturum zaten sonlandırılmış.')
    else:
        session.end_session()
        
        # Kullanıcının ilerleme durumunu güncelle
        try:
            progress = StudyProgress.objects.get(user=request.user)
        except StudyProgress.DoesNotExist:
            progress = StudyProgress.objects.create(user=request.user)
        
        progress.update_progress()
        
        messages.success(request, f'Çalışma oturumu sonlandırıldı. Bu oturumda {session.total_verses_studied} ayet çalıştınız.')
    
    return redirect('repetition:dashboard')

@login_required
def daily_plan(request):
    """
    Kullanıcının günlük çalışma planını gösterir.
    """
    # Günlük çalışma planını al
    daily_plan = SpacedRepetitionService.get_daily_study_plan(request.user)
    
    # Aktif çalışma oturumu var mı kontrol et
    active_session = StudySession.objects.filter(user=request.user, end_time__isnull=True).first()
    
    # Bugün tekrar edilecek ayetler
    verses_to_review = daily_plan['verses_to_review']
    
    # Yeni çalışılacak ayetler
    new_verses = daily_plan['new_verses']
    
    # Toplam çalışılacak ayet sayısı
    total_verses = daily_plan['total_verses']
    
    # Eğer çalışılacak ayet yoksa bilgi ver
    if total_verses == 0:
        messages.info(request, 'Bugün için çalışılacak ayet bulunmamaktadır.')
        return redirect('repetition:dashboard')
    
    return render(request, 'repetition/daily_plan.html', {
        'verses_to_review': verses_to_review,
        'new_verses': new_verses,
        'total_verses': total_verses,
        'active_session': active_session,
        'now': timezone.now()
    })

@login_required
def review_verse(request, verse_id):
    """
    Ayet tekrar görünümü.
    """
    try:
        verse = get_object_or_404(Verse, id=verse_id)
        
        # Kullanıcının bu ayet için çalışması var mı kontrol et
        try:
            verse_study = VerseStudy.objects.get(user=request.user, verse=verse)
        except VerseStudy.DoesNotExist:
            messages.error(request, 'Bu ayet için çalışma kaydınız bulunmamaktadır.')
            return redirect('repetition:dashboard')
        
        # Aktif çalışma oturumu var mı kontrol et
        active_session = StudySession.objects.filter(user=request.user, end_time__isnull=True).first()
        
        # Aynı suredeki diğer ayetleri al
        surah_verses = list(VerseStudy.objects.filter(
            user=request.user, 
            verse__surah=verse.surah
        ).select_related('verse').order_by('verse__verse_number'))
        
        # Önceki ve sonraki ayetleri bul
        prev_verse_study = None
        next_verse_study = None
        
        for i, vs in enumerate(surah_verses):
            if vs.verse.id == verse.id:
                if i > 0:
                    prev_verse_study = surah_verses[i-1]
                if i < len(surah_verses) - 1:
                    next_verse_study = surah_verses[i+1]
                break
        
        # POST isteği işleme
        if request.method == 'POST':
            quality = int(request.POST.get('quality', 3))
            
            try:
                # Tekrarı işle
                next_review_date = SpacedRepetitionService.process_verse_review(request.user, verse.id, quality)
                
                # Çalışma oturumuna ekle - ayrı bir transaction içinde
                if active_session and next_review_date:
                    try:
                        # Oturum güncellemesini ayrı bir transaction içinde yap
                        with transaction.atomic():
                            # Güncel verse_study nesnesini tekrar al
                            updated_verse_study = VerseStudy.objects.select_for_update().get(id=verse_study.id)
                            updated_verse_study.session = active_session
                            updated_verse_study.save(update_fields=['session'])
                    except Exception as e:
                        logger.error(f"Oturum güncellenirken hata: {str(e)}")
                
                if next_review_date:
                    messages.success(request, f'Tekrar kaydedildi. Bir sonraki tekrar tarihi: {next_review_date.strftime("%d.%m.%Y")}')
                    
                    # Sonraki ayete yönlendir
                    if next_verse_study:
                        return redirect('repetition:review_verse', verse_id=next_verse_study.verse.id)
                    else:
                        return redirect('repetition:dashboard')
                else:
                    messages.error(request, 'Tekrar kaydedilemedi.')
                    
            except Exception as e:
                logger.error(f"Tekrar kaydedilirken hata: {str(e)}")
                messages.error(request, f'Tekrar kaydedilirken bir hata oluştu: {str(e)}')
        
        return render(request, 'repetition/review.html', {
            'verse': verse,
            'verse_study': verse_study,
            'active_session': active_session,
            'prev_verse_study': prev_verse_study,
            'next_verse_study': next_verse_study,
            'surah_verses': surah_verses,
            'now': timezone.now()
        })
    
    except Exception as e:
        logger.error(f"Ayet görüntülenirken hata: {str(e)}")
        messages.error(request, f'Ayet görüntülenirken bir hata oluştu: {str(e)}')
        return redirect('repetition:dashboard')

@login_required
def memorize_verse(request, verse_id):
    """
    Ayet ezberleme görünümü.
    """
    verse = get_object_or_404(Verse, id=verse_id)
    
    # Kullanıcının bu ayet için çalışması var mı kontrol et
    verse_study = VerseStudy.objects.filter(user=request.user, verse=verse).first()
    
    # Aktif çalışma oturumu var mı kontrol et
    active_session = StudySession.objects.filter(user=request.user, end_time__isnull=True).first()
    
    # Eğer kullanıcı bu ayeti çalışmıyorsa ve yeni çalışma başlatmak istiyorsa
    if request.method == 'POST' and not verse_study:
        try:
            with transaction.atomic():
                verse_study = SpacedRepetitionService.start_new_verse_study(request.user, verse.id, active_session)
            messages.success(request, 'Ayet çalışması başlatıldı.')
        except Exception as e:
            messages.error(request, f'Ayet çalışması başlatılırken bir hata oluştu: {str(e)}')
    
    # Aynı suredeki diğer ayetleri al
    surah_verses = VerseStudy.objects.filter(
        user=request.user, 
        verse__surah=verse.surah
    ).select_related('verse').order_by('verse__verse_number')
    
    # Önceki ve sonraki ayetleri bul
    prev_verse_study = None
    next_verse_study = None
    
    for i, vs in enumerate(surah_verses):
        if vs.verse.id == verse.id:
            if i > 0:
                prev_verse_study = surah_verses[i-1]
            if i < len(surah_verses) - 1:
                next_verse_study = surah_verses[i+1]
            break
    
    return render(request, 'repetition/review.html', {
        'verse': verse,
        'verse_study': verse_study,
        'active_session': active_session,
        'prev_verse_study': prev_verse_study,
        'next_verse_study': next_verse_study,
        'surah_verses': surah_verses,
        'is_memorize_mode': True,
        'now': timezone.now()
    })

@login_required
def start_new_verse(request, verse_id):
    """
    Yeni bir ayet çalışması başlatır.
    """
    try:
        # Aktif oturum var mı kontrol et
        active_session = StudySession.objects.filter(user=request.user, end_time__isnull=True).first()
        
        # Ayet var mı kontrol et
        verse = get_object_or_404(Verse, id=verse_id)
        
        # Zaten çalışılıyor mu kontrol et
        if VerseStudy.objects.filter(user=request.user, verse=verse).exists():
            messages.warning(request, 'Bu ayet zaten çalışma listenizde bulunuyor.')
            return redirect('quran:surah_detail', surah_number=verse.surah.number)
        
        # Ayet çalışması oluştur
        verse_study = SpacedRepetitionService.start_new_verse_study(
            user=request.user,
            verse_id=verse_id,
            session=active_session
        )
        
        if verse_study:
            messages.success(request, 'Ayet çalışma listenize eklendi.')
        else:
            messages.warning(request, 'Bu ayet zaten çalışma listenizde bulunuyor veya eklenirken bir hata oluştu.')
        
        # Ayetin bulunduğu sureye yönlendir
        return redirect('quran:surah_detail', surah_number=verse.surah.number)
    
    except Exception as e:
        logger.error(f"Ayet çalışmaya eklenirken hata: {str(e)}")
        messages.error(request, f'Ayet çalışmaya eklenirken bir hata oluştu: {str(e)}')
        
        # Hata durumunda ana sayfaya yönlendir
        try:
            verse = Verse.objects.get(id=verse_id)
            return redirect('quran:surah_detail', surah_number=verse.surah.number)
        except:
            return redirect('quran:surah_list')

@login_required
def add_entire_surah(request, surah_number):
    """
    Bir surenin tüm ayetlerini çalışma listesine ekler.
    """
    try:
        # Aktif oturum var mı kontrol et
        active_session = StudySession.objects.filter(user=request.user, end_time__isnull=True).first()
        
        # Sureyi kontrol et
        surah = get_object_or_404(Surah, number=surah_number)
        
        # Arka planda işlemi başlat
        def background_add_surah():
            try:
                # Tüm sureyi ekle
                result = SpacedRepetitionService.add_entire_surah_to_study(
                    user=request.user,
                    surah_id=surah.id,
                    session=active_session
                )
                
                logger.info(f"Sure {surah.name_turkish} başarıyla eklendi: {result}")
            except Exception as e:
                logger.error(f"Arka planda sure eklenirken hata: {str(e)}")
        
        # Arka planda işlemi başlat
        thread = threading.Thread(target=background_add_surah)
        thread.daemon = True
        thread.start()
        
        # Kullanıcıya bilgi ver
        messages.info(request, f"{surah.name_turkish} suresi çalışma listenize ekleniyor. Bu işlem arka planda devam edecek.")
        
        # Sureye yönlendir
        return redirect('quran:surah_detail', surah_number=surah.number)
    
    except Exception as e:
        logger.error(f"Sure eklenirken hata oluştu: {str(e)}")
        messages.error(request, f"Sure eklenirken bir hata oluştu: {str(e)}")
        
        # Hata durumunda sure listesine yönlendir
        return redirect('quran:surah_list')

@login_required
def statistics(request):
    """
    Kullanıcının çalışma istatistiklerini gösterir.
    """
    # Kullanıcının çalışma istatistiklerini al
    statistics = SpacedRepetitionService.get_user_statistics(request.user)
    
    # Kullanıcının çalışma oturumlarını al
    sessions = StudySession.objects.filter(user=request.user, end_time__isnull=False).order_by('-start_time')[:10]
    
    # Kullanıcının çalıştığı ayetleri al
    verse_studies = VerseStudy.objects.filter(user=request.user).select_related('verse', 'verse__surah').order_by('next_review_date')
    
    return render(request, 'repetition/statistics.html', {
        'statistics': statistics,
        'sessions': sessions,
        'verse_studies': verse_studies
    })

# API Görünümleri

@login_required
@require_POST
def api_review_verse(request, verse_id):
    """
    Ayet tekrarını işleyen API görünümü.
    """
    try:
        quality = int(request.POST.get('quality', 3))
        
        # Tekrarı işle
        next_review_date = SpacedRepetitionService.process_verse_review(request.user, verse_id, quality)
        
        if next_review_date:
            return JsonResponse({
                'success': True,
                'next_review_date': next_review_date.strftime('%Y-%m-%d'),
                'message': f'Tekrar kaydedildi. Bir sonraki tekrar tarihi: {next_review_date.strftime("%d.%m.%Y")}'
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'Tekrar kaydedilemedi.'
            }, status=400)
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=400)

@login_required
def api_daily_plan(request):
    """
    Kullanıcının günlük çalışma planını JSON formatında döndüren API görünümü.
    """
    # Günlük çalışma planını al
    daily_plan = SpacedRepetitionService.get_daily_study_plan(request.user)
    
    verses_to_review = [{
        'id': verse.id,
        'surah': {
            'id': verse.verse.surah.id,
            'number': verse.verse.surah.number,
            'name_arabic': verse.verse.surah.name_arabic,
            'name_turkish': verse.verse.surah.name_turkish
        },
        'verse_number': verse.verse.verse_number,
        'text_arabic': verse.verse.text_arabic,
        'text_turkish': verse.verse.text_turkish,
        'full_reference': verse.verse.full_reference,
        'next_review_date': verse.next_review_date.strftime('%Y-%m-%d'),
        'easiness_factor': verse.easiness_factor,
        'interval': verse.interval,
        'repetitions': verse.repetitions,
        'difficulty': verse.difficulty,
        'is_memorized': verse.is_memorized
    } for verse in daily_plan['verses_to_review']]
    
    new_verses = [{
        'id': verse.id,
        'surah': {
            'id': verse.surah.id,
            'number': verse.surah.number,
            'name_arabic': verse.surah.name_arabic,
            'name_turkish': verse.surah.name_turkish
        },
        'verse_number': verse.verse_number,
        'text_arabic': verse.text_arabic,
        'text_turkish': verse.text_turkish,
        'full_reference': verse.full_reference
    } for verse in daily_plan['new_verses']]
    
    return JsonResponse({
        'verses_to_review': verses_to_review,
        'new_verses': new_verses,
        'total_verses': daily_plan['total_verses']
    })

@login_required
def api_statistics(request):
    """
    Kullanıcının çalışma istatistiklerini JSON formatında döndüren API görünümü.
    """
    # Kullanıcının çalışma istatistiklerini al
    statistics = SpacedRepetitionService.get_user_statistics(request.user)
    
    return JsonResponse(statistics)
