#!/usr/bin/env python
"""
Test script for the simplified candidate login flow
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth import get_user_model
from accounts.models import Event, Round, CandidateEntry
from django.test import Client
from datetime import datetime

# Create test data
def create_test_data():
    """Create test event and round"""
    print("\n" + "="*60)
    print("Creating test data...")
    print("="*60)
    
    # Create test event
    event = Event.objects.create(
        name="Test Event",
        date=datetime.now().date()
    )
    print(f"✓ Event created: {event.name} (ID: {event.id})")
    
    # Create test round with access code
    round_obj = Round.objects.create(
        event=event,
        round_number=1,
        duration_minutes=60,
        is_started=False
    )
    print(f"✓ Round created: Round {round_obj.round_number}")
    
    return event, round_obj

def test_login_flow(event, round_obj):
    """Test the candidate login flow"""
    print("\n" + "="*60)
    print("Testing Candidate Login Flow")
    print("="*60)
    
    client = Client()
    
    # Test 1: GET request should show the login form
    print("\n[1] Testing GET request to login page...")
    response = client.get('/login/candidate/')
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert 'Join Quiz' in response.content.decode(), "Login form not found"
    print("✓ Login page loads successfully")
    print("✓ Page contains 'Join Quiz' title")
    
    # Test 2: POST with valid access code
    print("\n[2] Testing POST with valid access code...")
    response = client.post('/login/candidate/', {
        'candidate_name': 'Test Student',
        'access_code': 'TEST123'
    }, follow=True)
    
    print(f"Status code: {response.status_code}")
    print(f"Final URL: {response.redirect_chain}")
    
    # Check if redirected to waiting page
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    print("✓ Request processed successfully")
    
    # Check if candidate was created
    candidates = CandidateEntry.objects.filter(candidate_name='Test Student')
    assert candidates.exists(), "Candidate entry was not created"
    candidate = candidates.first()
    print(f"✓ Candidate created: {candidate.candidate_name}")
    print(f"✓ Candidate is_waiting: {candidate.is_waiting}")
    assert candidate.is_waiting == True, "Candidate is_waiting should be True"
    
    # Test 3: POST with invalid access code
    print("\n[3] Testing POST with invalid access code...")
    response = client.post('/login/candidate/', {
        'candidate_name': 'Invalid Student',
        'access_code': 'WRONG123'
    })
    
    assert response.status_code == 302, f"Expected redirect (302), got {response.status_code}"
    print("✓ Invalid access code triggers redirect")
    
    # Check that invalid candidate was NOT created
    invalid_candidates = CandidateEntry.objects.filter(candidate_name='Invalid Student')
    assert not invalid_candidates.exists(), "Invalid candidate should not be created"
    print("✓ Invalid candidate entry was not created")
    
    # Test 4: POST without access code
    print("\n[4] Testing POST without access code...")
    response = client.post('/login/candidate/', {
        'candidate_name': 'Test Student 2'
    })
    
    assert response.status_code == 302, f"Expected redirect (302), got {response.status_code}"
    print("✓ Missing access code triggers redirect")
    
    print("\n" + "="*60)
    print("✓ ALL TESTS PASSED!")
    print("="*60)

if __name__ == '__main__':
    try:
        # Clean up previous test data
        print("Cleaning up previous test data...")
        Event.objects.filter(name="Test Event").delete()
        CandidateEntry.objects.filter(candidate_name__startswith="Test ").delete()
        
        # Create fresh test data
        event, round_obj = create_test_data()
        
        # Run tests
        test_login_flow(event, round_obj)
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
