from django.contrib import admin
from django.utils.html import format_html
from .models import Event, Round, Question, QuestionOption, CandidateEntry, CodeSubmission, CodingQuestion, TestCase, DubbingQuestion, DubbingTestCase

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

@admin.register(CandidateEntry)
class CandidateEntryAdmin(admin.ModelAdmin):
    list_display = ('candidate_name', 'event', 'round', 'display_percentage', 'display_time_taken', 'is_submitted', 'entry_time')
    search_fields = ('candidate_name', 'event__name', 'round__event__name')
    list_filter = ('event', 'round', 'is_submitted', 'entry_time')
    readonly_fields = ('entry_time', 'last_active', 'quiz_started_at', 'percentage', 'score', 'display_percentage_detail')
    fieldsets = (
        ('Candidate Information', {
            'fields': ('candidate_name', 'event', 'round', 'access_code_used')
        }),
        ('Score Information', {
            'fields': ('score', 'percentage', 'total_questions', 'display_percentage_detail')
        }),
        ('Status', {
            'fields': ('is_submitted', 'is_waiting', 'has_switched_tabs')
        }),
        ('Timing & Tracking', {
            'fields': ('entry_time', 'quiz_started_at', 'last_active', 'time_taken_seconds')
        }),
    )
    
    def display_percentage(self, obj):
        """Display percentage with color coding"""
        if not obj.is_submitted:
            return format_html('<span style="color: #999;">Not submitted</span>')
        
        if obj.percentage is None or obj.percentage == 0:
            return format_html('<span style="color: #999;">-</span>')
        
        percentage = obj.percentage
        
        # Color code based on percentage
        if percentage >= 70:
            color = '#28a745'  # Green
        elif percentage >= 50:
            color = '#ff9800'  # Orange
        else:
            color = '#dc3545'  # Red
        
        return format_html(
            '<span style="font-weight: bold; color: {}; font-size: 13px;">{:.1f}%</span>',
            color,
            percentage
        )
    display_percentage.short_description = 'Score (%)'
    
    def display_time_taken(self, obj):
        """Display time taken in HH:MM:SS format"""
        if not obj.is_submitted or obj.time_taken_seconds is None or obj.time_taken_seconds == 0:
            return format_html('<span style="color: #999;">-</span>')
        
        seconds = obj.time_taken_seconds
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        
        return format_html(
            '<span style="font-weight: bold; color: #2196F3; font-size: 13px;">{}h {}m {}s</span>',
            int(hours),
            int(minutes),
            int(secs)
        )
    display_time_taken.short_description = 'Time Taken'
    
    def display_percentage_detail(self, obj):
        """Display detailed score breakdown"""
        if not obj.is_submitted or obj.score is None:
            return 'Not submitted yet'
        
        # Use the stored percentage 
        percentage = obj.percentage if obj.percentage is not None else 0
        
        # Get code submission count
        num_code_submissions = CodeSubmission.objects.filter(candidate=obj).count()
        mcq_max = obj.total_questions or 0
        
        # Format time
        seconds = obj.time_taken_seconds or 0
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        time_str = f"{int(hours)}h {int(minutes)}m {int(secs)}s"
        
        return format_html(
            '<div style="background: #f0f0f0; padding: 10px; border-radius: 5px;">'
            '<p><b>Score: {}</b></p>'
            '<p><b>Percentage: {:.2f}%</b></p>'
            '<p><b>Time Taken: {}</b></p>'
            '<p style="font-size: 12px; color: #666; margin-top: 8px;">'
            'MCQ Questions: {}<br>'
            'Code Submissions: {}</p>'
            '</div>',
            obj.score or 0,
            percentage,
            time_str,
            mcq_max,
            num_code_submissions
        )
    display_percentage_detail.short_description = 'Score Details'

@admin.register(CodeSubmission)
class CodeSubmissionAdmin(admin.ModelAdmin):
    list_display = ('candidate', 'question_title', 'question_type', 'display_score_breakdown', 'total_score', 'submitted_at')
    search_fields = ('candidate__candidate_name', 'question_title', 'question_type')
    list_filter = ('question_type', 'submitted_at', 'output_success', 'time_limit_met')
    readonly_fields = ('candidate', 'question_type', 'question_id', 'submitted_at', 'code', 'display_scoring_info')
    fieldsets = (
        ('Submission Details', {
            'fields': ('candidate', 'question_type', 'question_id', 'question_title', 'language')
        }),
        ('Code Information', {
            'fields': ('code',),
            'classes': ('collapse',)
        }),
        ('Test Case Results', {
            'fields': ('passed_test_cases', 'total_test_cases')
        }),
        ('Execution Results', {
            'fields': ('output_success', 'execution_time_ms', 'time_limit_met')
        }),
        ('Scoring Details', {
            'fields': ('testcase_score', 'output_score', 'efficiency_score', 'total_score', 'display_scoring_info'),
            'classes': ('wide',)
        }),
        ('Timestamps', {
            'fields': ('submitted_at',)
        }),
    )
    
    def display_score_breakdown(self, obj):
        return format_html(
            '<span style="font-family: monospace;">TC: <b>{}</b> + Out: <b>{}</b> + Eff: <b>{}</b></span>',
            obj.testcase_score,
            obj.output_score,
            obj.efficiency_score
        )
    display_score_breakdown.short_description = "Score Breakdown"
    
    def display_scoring_info(self, obj):
        return format_html(
            '<div style="background: #f0f0f0; padding: 10px; border-radius: 5px; font-family: monospace;">'
            '<p><b>Scoring System:</b></p>'
            '<p>• Test Cases: <b>{} × 2</b> = <b>{}</b> marks (2 per passing test case)</p>'
            '<p>• Output: <b>{}</b> marks (2 if output is correct, 0 otherwise)</p>'
            '<p>• Efficiency: <b>{}</b> marks (2 for best time/space complexity, 0 otherwise)</p>'
            '<p style="margin-top: 10px; border-top: 1px solid #ccc; padding-top: 10px;"><b>Total: {} marks (Maximum 6)</b></p>'
            '</div>',
            obj.passed_test_cases,
            obj.testcase_score,
            obj.output_score,
            obj.efficiency_score,
            obj.total_score
        )
    display_scoring_info.short_description = "Scoring Breakdown"
