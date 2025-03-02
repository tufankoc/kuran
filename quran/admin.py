from django.contrib import admin
from .models import Surah, Verse, Tafsir

class VerseInline(admin.TabularInline):
    model = Verse
    extra = 0
    show_change_link = True
    fields = ('verse_number', 'text_arabic', 'text_turkish', 'juz', 'page')
    readonly_fields = ('verse_number',)
    can_delete = False
    max_num = 10

class TafsirInline(admin.TabularInline):
    model = Tafsir
    extra = 0
    fields = ('author', 'text', 'source')

@admin.register(Surah)
class SurahAdmin(admin.ModelAdmin):
    list_display = ('number', 'name_turkish', 'name_arabic', 'revelation_type', 'verse_count')
    list_filter = ('revelation_type',)
    search_fields = ('name_turkish', 'name_arabic', 'name_english')
    ordering = ('number',)
    inlines = [VerseInline]

@admin.register(Verse)
class VerseAdmin(admin.ModelAdmin):
    list_display = ('full_reference', 'surah', 'verse_number', 'juz', 'page')
    list_filter = ('surah', 'juz', 'page')
    search_fields = ('text_turkish', 'text_arabic', 'text_transliteration')
    ordering = ('surah__number', 'verse_number')
    inlines = [TafsirInline]
    
    def full_reference(self, obj):
        return obj.full_reference
    full_reference.short_description = 'Referans'

@admin.register(Tafsir)
class TafsirAdmin(admin.ModelAdmin):
    list_display = ('verse', 'author', 'source')
    list_filter = ('author', 'source')
    search_fields = ('text', 'author', 'source')
    raw_id_fields = ('verse',)
