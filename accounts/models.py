from django.db import models
from datetime import date
from django.utils import timezone

# Create your models here.

class Event(models.Model):
    """Event model to store quiz events"""
    name = models.CharField(max_length=255)
    date = models.DateField(default=date.today)
    number_of_rounds = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} - {self.date.strftime('%Y-%m-%d')}"
    
    def get_rounds(self):
        """Return a list of round numbers from 1 to number_of_rounds"""
        return list(range(1, self.number_of_rounds + 1))
    
    class Meta:
        ordering = ['-created_at']


class Round(models.Model):
    """Round model to store round settings"""
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='rounds')
    round_number = models.IntegerField()
    duration_minutes = models.IntegerField(default=60)
    access_code = models.CharField(max_length=10, blank=True, null=True)
    is_started = models.BooleanField(default=False)
    is_hosting = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.event.name} - Round {self.round_number}"
    
    class Meta:
        ordering = ['round_number']


class CandidateEntry(models.Model):
    """Model to track candidate participation in rounds"""
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='candidate_entries')
    round = models.ForeignKey(Round, on_delete=models.CASCADE, related_name='candidate_entries')
    candidate_name = models.CharField(max_length=255)
    access_code_used = models.CharField(max_length=10, blank=True, null=True, db_index=True)
    is_waiting = models.BooleanField(default=True, db_index=True)
    is_submitted = models.BooleanField(default=False, db_index=True)
    score = models.IntegerField(default=0, null=True, blank=True)
    total_questions = models.IntegerField(default=0, null=True, blank=True)
    time_taken_seconds = models.IntegerField(default=0, null=True, blank=True)
    entry_time = models.DateTimeField(auto_now_add=True, db_index=True)
    last_active = models.DateTimeField(auto_now_add=True)
    has_switched_tabs = models.BooleanField(default=False)
    quiz_started_at = models.DateTimeField(null=True, blank=True, db_index=True, default=None)
    
    def __str__(self):
        return f"{self.candidate_name} - {self.round}"
    
    class Meta:
        ordering = ['-entry_time']
        # Prevent duplicate entries: same candidate name + access code per round
        unique_together = [['round', 'candidate_name', 'access_code_used']]
        indexes = [
            models.Index(fields=['round', 'access_code_used']),
            models.Index(fields=['round', 'is_waiting']),
        ]


class Question(models.Model):
    """Question model to store quiz questions"""
    round = models.ForeignKey(Round, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.round} - Q{self.id}"
    
    class Meta:
        ordering = ['created_at']


class QuestionOption(models.Model):
    """Model to store options for questions"""
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='options')
    option_text = models.CharField(max_length=500)
    option_number = models.IntegerField(choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4')])
    is_correct = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.question} - Option {self.option_number}"
    
    def get_option_number_display(self):
        """Convert option number to letter (1->A, 2->B, etc.)"""
        return chr(64 + self.option_number)  # 65 is 'A', so 64 + 1 = 65 (A)
    
    class Meta:
        ordering = ['option_number']


CODING_LANGUAGE_CHOICES = [
    ('c', 'C'),
    ('python', 'Python'),
    ('java', 'Java'),
]


class CodingQuestion(models.Model):
    """Model to store coding/programming questions for a round"""
    round = models.ForeignKey(Round, on_delete=models.CASCADE, related_name='coding_questions')
    title = models.CharField(max_length=500)
    problem_statement = models.TextField()
    input_format = models.TextField(blank=True, default='')
    output_format = models.TextField(blank=True, default='')
    constraints = models.TextField(blank=True, default='')
    sample_input = models.TextField(blank=True, default='')
    sample_output = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.round} - Coding: {self.title}"

    class Meta:
        ordering = ['created_at']


class TestCase(models.Model):
    """Model to store test cases for coding questions"""
    coding_question = models.ForeignKey(CodingQuestion, on_delete=models.CASCADE, related_name='test_cases')
    input_data = models.TextField(blank=True, default='')
    expected_output = models.TextField()
    order = models.IntegerField(default=0)

    def __str__(self):
        return f"TestCase {self.order} for {self.coding_question.title}"

    class Meta:
        ordering = ['order']


class DubbingQuestion(models.Model):
    """Model to store code-snippet (dubbing) questions for a round"""
    round = models.ForeignKey(Round, on_delete=models.CASCADE, related_name='dubbing_questions')
    title = models.CharField(max_length=500)
    description = models.TextField(blank=True, default='')
    language = models.CharField(max_length=50, choices=CODING_LANGUAGE_CHOICES, default='python')
    code_snippet = models.TextField()
    sample_input = models.TextField(blank=True, default='')
    sample_output = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.round} - Dubbing: {self.title} [{self.language}]"  

    class Meta:
        ordering = ['created_at']


class DubbingTestCase(models.Model):
    """Model to store test cases for dubbing (debugging) questions"""
    dubbing_question = models.ForeignKey(DubbingQuestion, on_delete=models.CASCADE, related_name='test_cases')
    input_data = models.TextField(blank=True, default='')
    expected_output = models.TextField()
    order = models.IntegerField(default=0)

    def __str__(self):
        return f"DubbingTestCase {self.order} for {self.dubbing_question.title}"

    class Meta:
        ordering = ['order']
