from django.contrib import admin
from .models import Event, Round, Question, QuestionOption

# Register your models here.

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('name', 'date', 'number_of_rounds', 'created_at')
    search_fields = ('name',)
    list_filter = ('date', 'created_at')
    ordering = ('-created_at',)


@admin.register(Round)
class RoundAdmin(admin.ModelAdmin):
    list_display = ('event', 'round_number', 'duration_minutes', 'created_at')
    search_fields = ('event__name',)
    list_filter = ('event', 'round_number')


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('id', 'round', 'question_text', 'created_at')
    search_fields = ('question_text', 'round__event__name')
    list_filter = ('round__event', 'created_at')


@admin.register(QuestionOption)
class QuestionOptionAdmin(admin.ModelAdmin):
    list_display = ('id', 'question', 'option_number', 'option_text', 'is_correct')
    search_fields = ('question__question_text', 'option_text')
    list_filter = ('question__round__event', 'is_correct')
