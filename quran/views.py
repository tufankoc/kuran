from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from .models import Surah, Verse, Tafsir
from repetition.algorithm import SpacedRepetitionService
import subprocess
import threading
import json
from django.views.decorators.http import require_POST
import logging

logger = logging.getLogger(__name__)

# Create your views here.

@login_required
def surah_list(request):
    """
    Tüm sureleri listeleyen görünüm.
    """
    surahs = Surah.objects.all().order_by('number')
    return render(request, 'quran/surah_list.html', {'surahs': surahs})

@login_required
def surah_detail(request, surah_number):
    """
    Belirli bir surenin detaylarını ve ayetlerini gösteren görünüm.
    """
    surah = get_object_or_404(Surah, number=surah_number)
    verses = Verse.objects.filter(surah=surah).order_by('verse_number')
    
    # Sayfalama
    paginator = Paginator(verses, 10)  # Her sayfada 10 ayet
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'quran/surah_detail.html', {
        'surah': surah,
        'verses': page_obj,
        'page_obj': page_obj,
        'now': timezone.now()
    })

@login_required
def verse_detail(request, verse_id):
    """
    Belirli bir ayetin detaylarını gösteren görünüm.
    """
    verse = get_object_or_404(Verse, id=verse_id)
    
    # Önceki ve sonraki ayetleri bul
    try:
        prev_verse = Verse.objects.filter(
            surah=verse.surah, 
            verse_number__lt=verse.verse_number
        ).order_by('-verse_number').first()
    except Verse.DoesNotExist:
        prev_verse = None
    
    try:
        next_verse = Verse.objects.filter(
            surah=verse.surah, 
            verse_number__gt=verse.verse_number
        ).order_by('verse_number').first()
    except Verse.DoesNotExist:
        next_verse = None
    
    return render(request, 'quran/verse_detail.html', {
        'verse': verse,
        'prev_verse': prev_verse,
        'next_verse': next_verse,
        'now': timezone.now()
    })

@login_required
def search_verses(request):
    """
    Ayet arama görünümü.
    """
    query = request.GET.get('q', '')
    
    if query:
        # Arama sorgusu varsa, ayetleri ara
        verses = Verse.objects.filter(
            Q(text_turkish__icontains=query) | 
            Q(text_transliteration__icontains=query) |
            Q(surah__name_turkish__icontains=query)
        ).select_related('surah').order_by('surah__number', 'verse_number')
        
        # Sayfalama
        paginator = Paginator(verses, 10)  # Her sayfada 10 ayet
        page_number = request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)
        
        return render(request, 'quran/search_results.html', {
            'query': query,
            'verses': page_obj,
            'page_obj': page_obj,
            'now': timezone.now()
        })
    
    return render(request, 'quran/search.html')

# API Görünümleri

@login_required
def api_surah_list(request):
    """
    Tüm sureleri JSON formatında döndüren API görünümü.
    """
    surahs = Surah.objects.all().order_by('number')
    data = [{
        'id': surah.id,
        'number': surah.number,
        'name_arabic': surah.name_arabic,
        'name_turkish': surah.name_turkish,
        'name_english': surah.name_english,
        'revelation_type': surah.revelation_type,
        'verse_count': surah.verse_count
    } for surah in surahs]
    
    return JsonResponse({'surahs': data})

@login_required
def api_surah_detail(request, surah_number):
    """
    Belirli bir surenin detaylarını JSON formatında döndüren API görünümü.
    """
    surah = get_object_or_404(Surah, number=surah_number)
    verses = Verse.objects.filter(surah=surah).order_by('verse_number')
    
    # Kullanıcının çalıştığı ayetleri işaretle
    user_verses = request.user.verse_studies.filter(verse__surah=surah).values_list('verse_id', flat=True)
    
    surah_data = {
        'id': surah.id,
        'number': surah.number,
        'name_arabic': surah.name_arabic,
        'name_turkish': surah.name_turkish,
        'name_english': surah.name_english,
        'revelation_type': surah.revelation_type,
        'verse_count': surah.verse_count
    }
    
    verses_data = [{
        'id': verse.id,
        'verse_number': verse.verse_number,
        'text_arabic': verse.text_arabic,
        'text_turkish': verse.text_turkish,
        'text_transliteration': verse.text_transliteration,
        'juz': verse.juz,
        'page': verse.page,
        'is_studying': verse.id in user_verses
    } for verse in verses]
    
    return JsonResponse({
        'surah': surah_data,
        'verses': verses_data
    })

@login_required
def api_verse_detail(request, verse_id):
    """
    Belirli bir ayetin detaylarını JSON formatında döndüren API görünümü.
    """
    verse = get_object_or_404(Verse, id=verse_id)
    tafsirs = Tafsir.objects.filter(verse=verse)
    
    verse_data = {
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
        'text_transliteration': verse.text_transliteration,
        'juz': verse.juz,
        'page': verse.page,
        'full_reference': verse.full_reference
    }
    
    tafsirs_data = [{
        'id': tafsir.id,
        'author': tafsir.author,
        'text': tafsir.text,
        'source': tafsir.source
    } for tafsir in tafsirs]
    
    return JsonResponse({
        'verse': verse_data,
        'tafsirs': tafsirs_data
    })

@login_required
@require_POST
def fetch_transliterations_view(request):
    """
    Belirli bir sure için transliterasyon verilerini çeken görünüm.
    """
    try:
        surah_number = request.POST.get('surah')
        batch_size = request.POST.get('batch_size', '10')
        
        if not surah_number:
            return JsonResponse({'status': 'error', 'message': 'Sure numarası belirtilmedi.'}, status=400)
        
        # String değerleri integer'a dönüştür
        try:
            surah_number = int(surah_number)
            batch_size = int(batch_size)
        except ValueError:
            return JsonResponse({'status': 'error', 'message': 'Geçersiz sure numarası veya batch size değeri.'}, status=400)
        
        # Arka planda işlemi başlat
        def background_fetch():
            try:
                from django.core.management import call_command
                call_command('fetch_transliterations', surah=surah_number, batch_size=batch_size)
            except Exception as e:
                logger.error(f"Transliterasyon verisi çekilirken hata: {str(e)}")
        
        # Arka planda işlemi başlat
        thread = threading.Thread(target=background_fetch)
        thread.daemon = True
        thread.start()
        
        return JsonResponse({'status': 'success', 'message': f'{surah_number} numaralı sure için okunuşlar indiriliyor.'})
    
    except Exception as e:
        logger.error(f"Transliterasyon verisi çekilirken hata: {str(e)}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@login_required
def api_surah_transliteration(request, surah_number):
    """
    Belirli bir surenin transliterasyon bilgisini JSON formatında döndüren API görünümü.
    """
    surah = get_object_or_404(Surah, number=surah_number)
    
    # Surenin tüm ayetlerini al
    verses = Verse.objects.filter(surah=surah).order_by('verse_number')
    
    # Transliterasyon bilgisi
    transliteration_text = ""
    
    # Tüm ayetlerin transliterasyonlarını birleştir
    for verse in verses:
        if verse.text_transliteration:
            transliteration_text += f"({verse.verse_number}) {verse.text_transliteration}\n\n"
    
    # Eğer transliterasyon yoksa
    if not transliteration_text:
        transliteration_text = "Bu sure için okunuş bilgisi henüz eklenmemiş."
    
    return JsonResponse({
        'id': surah.id,
        'number': surah.number,
        'name_arabic': surah.name_arabic,
        'name_turkish': surah.name_turkish,
        'transliteration': transliteration_text
    })
