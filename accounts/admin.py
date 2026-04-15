from django.contrib import admin
from .models import Event, Round, Question, QuestionOption, CodingQuestion, TestCase, DubbingQuestion, DubbingTestCase

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

@admin.register(CodingQuestion)
class CodingQuestionAdmin(admin.ModelAdmin):
    list_display = ('id', 'round', 'title', 'created_at')
    search_fields = ('title', 'round__event__name')

@admin.register(TestCase)
class TestCaseAdmin(admin.ModelAdmin):
    list_display = ('id', 'coding_question', 'order')

@admin.register(DubbingQuestion)
class DubbingQuestionAdmin(admin.ModelAdmin):
    list_display = ('id', 'round', 'title', 'language', 'created_at')
    search_fields = ('title', 'round__event__name')

@admin.register(DubbingTestCase)
class DubbingTestCaseAdmin(admin.ModelAdmin):
    list_display = ('id', 'dubbing_question', 'order')
