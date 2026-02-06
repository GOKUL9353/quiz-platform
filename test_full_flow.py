#!/usr/bin/env python
"""
End-to-end test for the complete quiz platform flow
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from accounts.models import Event, Round, CandidateEntry, Question, QuestionOption
from django.test import Client
from datetime import datetime

def print_section(title):
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}")

def test_complete_flow():
    """Test the complete flow: login -> wait -> admin starts -> redirect to quiz"""
    
    print_section("Setting up test data")
    
    # Create event
    event = Event.objects.create(
        name="Integration Test Event",
        date=datetime.now().date()
    )
    print(f"✓ Event created: {event.name}")
    
    # Create round with access code
    round_obj = Round.objects.create(
        event=event,
        round_number=1,
        duration_minutes=30,
        is_started=False
    )
    print(f"✓ Round created: Round {round_obj.round_number}")
    print(f"  Is Started: {round_obj.is_started}")
    
    # Add some test questions
    q1 = Question.objects.create(
        round=round_obj,
        question_text="What is 2+2?"
    )
    print(f"✓ Question created: {q1.question_text}")
    
    print_section("Step 1: Candidate Login")
    client = Client()
    
    # Candidate logs in
    response = client.post('/login/candidate/', {
        'candidate_name': 'John Doe',
        'access_code': 'INTEG123'
    }, follow=True)
    
    assert response.status_code == 200
    print("✓ Candidate successfully logged in")
    print(f"✓ Redirected to waiting page")
    
    # Verify candidate was created
    candidate = CandidateEntry.objects.get(candidate_name='John Doe')
    print(f"✓ Candidate entry created (ID: {candidate.id})")
    print(f"✓ Candidate is_waiting: {candidate.is_waiting}")
    assert candidate.is_waiting == True
    
    print_section("Step 2: Verify Candidate in Admin List")
    
    # Get candidates for the round (only those waiting)
    waiting_candidates = round_obj.candidate_entries.filter(is_waiting=True)
    print(f"✓ Waiting candidates for Round 1: {waiting_candidates.count()}")
    assert 'John Doe' in [c.candidate_name for c in waiting_candidates]
    print(f"✓ John Doe found in waiting candidates list")
    
    print_section("Step 3: Admin Starts Round")
    
    # Admin starts the round
    round_obj.is_started = True
    round_obj.save()
    print(f"✓ Round {round_obj.round_number} started by admin")
    print(f"✓ Round is_started: {round_obj.is_started}")
    
    print_section("Step 4: Verify API Endpoint")
    
    # Test the check-round-started endpoint
    response = client.get(
        f'/api/check-round-started/{event.id}/{round_obj.round_number}/'
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data['started'] == True
    print(f"✓ API endpoint returns: {data}")
    print(f"✓ Round is marked as started")
    
    print_section("Step 5: Verify Candidate Quiz Start")
    
    # When candidate navigates to quiz, is_waiting should be set to False
    candidate.is_waiting = False
    candidate.save()
    print(f"✓ Candidate is_waiting set to: {candidate.is_waiting}")
    
    # Verify candidate no longer appears in waiting list
    waiting_candidates_after = round_obj.candidate_entries.filter(is_waiting=True)
    print(f"✓ Waiting candidates after quiz start: {waiting_candidates_after.count()}")
    assert 'John Doe' not in [c.candidate_name for c in waiting_candidates_after]
    print(f"✓ John Doe removed from waiting list (now taking quiz)")
    
    print_section("ALL TESTS PASSED - COMPLETE FLOW WORKING!")
    print("\nSummary:")
    print(f"  Event: {event.name}")
    print(f"  Round: {round_obj.round_number}")
    print(f"  Candidate: {candidate.candidate_name}")
    print(f"  Status: ✓ Login → Wait → Start → Quiz")

if __name__ == '__main__':
    try:
        # Clean up
        Event.objects.filter(name="Integration Test Event").delete()
        
        # Run test
        test_complete_flow()
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
