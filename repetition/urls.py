from django.urls import path
from . import views

app_name = 'repetition'

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('start-session/', views.start_session, name='start_session'),
    path('end-session/', views.end_session, name='end_session'),
    path('daily-plan/', views.daily_plan, name='daily_plan'),
    path('verse/<int:verse_id>/start/', views.start_new_verse, name='start_new_verse'),
    path('surah/<int:surah_number>/add-all/', views.add_entire_surah, name='add_entire_surah'),
    path('verse/<int:verse_id>/memorize/', views.memorize_verse, name='memorize_verse'),
    path('verse/<int:verse_id>/review/', views.review_verse, name='review_verse'),
    path('statistics/', views.statistics, name='statistics'),
    path('api/review/<int:verse_id>/', views.api_review_verse, name='api_review_verse'),
    path('api/daily-plan/', views.api_daily_plan, name='api_daily_plan'),
    path('api/statistics/', views.api_statistics, name='api_statistics'),
] 