from django.urls import path
from . import views

app_name = 'quran'

urlpatterns = [
    path('', views.surah_list, name='surah_list'),
    path('surah/<int:surah_number>/', views.surah_detail, name='surah_detail'),
    path('verse/<int:verse_id>/', views.verse_detail, name='verse_detail'),
    path('search/', views.search_verses, name='search_verses'),
    path('fetch-transliterations/', views.fetch_transliterations_view, name='fetch_transliterations'),
    
    # API Endpoints
    path('api/surahs/', views.api_surah_list, name='api_surah_list'),
    path('api/surah/<int:surah_number>/', views.api_surah_detail, name='api_surah_detail'),
    path('api/verse/<int:verse_id>/', views.api_verse_detail, name='api_verse_detail'),
    path('api/surah/<int:surah_number>/transliteration/', views.api_surah_transliteration, name='api_surah_transliteration'),
] 