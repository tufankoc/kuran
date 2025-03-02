from django.contrib import admin
from .models import StudySession, VerseStudy, StudyProgress

class VerseStudyInline(admin.TabularInline):
    model = VerseStudy
    extra = 0
    fields = ('verse', 'next_review_date', 'easiness_factor', 'interval', 'repetitions', 'difficulty', 'is_memorized')
    readonly_fields = ('verse', 'next_review_date', 'easiness_factor', 'interval', 'repetitions', 'difficulty', 'is_memorized')
    can_delete = False
    max_num = 10

@admin.register(StudySession)
class StudySessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'start_time', 'end_time', 'total_verses_studied', 'duration')
    list_filter = ('user', 'start_time')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('duration',)
    inlines = [VerseStudyInline]
    
    def duration(self, obj):
        if obj.duration is not None:
            return f"{obj.duration} dakika"
        return "Devam ediyor"
    duration.short_description = "Süre"

@admin.register(VerseStudy)
class VerseStudyAdmin(admin.ModelAdmin):
    list_display = ('user', 'verse', 'next_review_date', 'easiness_factor', 'interval', 'repetitions', 'difficulty', 'is_memorized')
    list_filter = ('user', 'next_review_date', 'difficulty', 'is_memorized')
    search_fields = ('user__username', 'user__email', 'verse__text_turkish')
    readonly_fields = ('first_studied_at', 'last_studied_at')

@admin.register(StudyProgress)
class StudyProgressAdmin(admin.ModelAdmin):
    list_display = ('user', 'total_verses_studied', 'total_verses_memorized', 'total_study_time', 'current_streak', 'longest_streak', 'last_study_date')
    list_filter = ('last_study_date',)
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('total_verses_studied', 'total_verses_memorized', 'total_study_time', 'current_streak', 'longest_streak', 'last_study_date')
