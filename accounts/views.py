from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from .models import Event, Round, Question, QuestionOption, CandidateEntry
from .email_service import send_quiz_completion_email, send_quiz_results_email, send_email_with_brevo
from datetime import datetime, timedelta
from django.utils import timezone
import json
import logging
import traceback
import random
import string

logger = logging.getLogger(__name__)


def generate_access_code(length=6):
    """Generate a random alphanumeric access code"""
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choice(characters) for _ in range(length))


# Home page - redirect to login choice
def home(request):
    """Redirect to login choice page"""
    return redirect('login_choice')


# Login choice page - user selects candidate or admin
def login_choice(request):
    """Display login choice page"""
    return render(request, 'login_choice.html')


# Candidate login - Simple: Ask for name and access code
def candidate_login(request):
    """Handle candidate login - Ask for candidate name and round access code"""
    if request.method == 'POST':
        candidate_name = request.POST.get('candidate_name', '').strip()
        access_code = request.POST.get('access_code', '').strip()
        
        # Validate inputs
        if not candidate_name:
            messages.error(request, 'Please enter your name or team name!')
            return redirect('candidate_login')
        
        if not access_code:
            messages.error(request, 'Please enter the access code!')
            return redirect('candidate_login')
        
        try:
            # Find the round with this access code
            round_obj = Round.objects.get(access_code=access_code)
            
            # Check if round has already started
            if round_obj.is_started:
                messages.error(request, 'This round has already started! No new candidates can join.')
                return redirect('candidate_login')
            
            event = round_obj.event
            
            # Create candidate entry with is_waiting=True
            candidate_entry = CandidateEntry.objects.create(
                event=event,
                round=round_obj,
                candidate_name=candidate_name,
                is_waiting=True
            )
            
            # Store in session
            request.session['candidate_entry_id'] = candidate_entry.id
            request.session['candidate_name'] = candidate_entry.candidate_name
            
            # Redirect to waiting page
            return redirect('waiting_for_round', event_id=event.id, round_number=round_obj.round_number)
        except Round.DoesNotExist:
            messages.error(request, 'Invalid access code! Please check and try again.')
            return redirect('candidate_login')
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
            return redirect('candidate_login')
    
    return render(request, 'candidate_login.html')


# Candidate login - Step 2: Round selection and password verification
def select_round(request, event_id):
    """Handle round selection - Step 2"""
    try:
        event = Event.objects.get(id=event_id)
        
        if request.method == 'POST':
            candidate_name = request.POST.get('candidate_name')
            access_code = request.POST.get('access_code')
            
            # Validate candidate name
            if not candidate_name or candidate_name.strip() == '':
                messages.error(request, 'Please enter your name or team name!')
                return redirect('candidate_login')
            
            # Validate access code is provided
            if not access_code:
                messages.error(request, 'Please enter the access code!')
                return redirect('candidate_login')
            
            try:
                # Find the round with this access code
                round_obj = Round.objects.get(access_code=access_code)
                
                # Create candidate entry and store in session
                candidate_entry = CandidateEntry.objects.create(
                    event=round_obj.event,
                    round=round_obj,
                    candidate_name=candidate_name.strip(),
                    is_waiting=True
                )
                
                # Store candidate entry ID in session
                request.session['candidate_entry_id'] = candidate_entry.id
                request.session['candidate_name'] = candidate_entry.candidate_name
                
                # Redirect to waiting page
                return redirect('waiting_for_round', event_id=round_obj.event.id, round_number=round_obj.round_number)
            except Round.DoesNotExist:
                messages.error(request, 'Invalid access code!')
                return redirect('candidate_login')
        
        # GET request - redirect to candidate login
        return redirect('candidate_login')
    except Event.DoesNotExist:
        messages.error(request, 'Event not found!')
        return redirect('candidate_login')


# Candidate login - Step 3: Access code verification
def verify_round_login(request, event_id, round_number):
    """Handle access code verification - Step 3: Verify access code"""
    if request.method == 'POST':
        candidate_name = request.POST.get('candidate_name')
        access_code = request.POST.get('access_code')
        
        try:
            event = Event.objects.get(id=event_id)
            round_obj = Round.objects.get(event=event, round_number=round_number)
            
            # Verify access code
            if round_obj.access_code and round_obj.access_code == access_code:
                # Code correct, create candidate entry
                candidate_entry = CandidateEntry.objects.create(
                    event=event,
                    round=round_obj,
                    candidate_name=candidate_name.strip(),
                    is_waiting=True
                )
                
                # Store in session
                request.session['candidate_entry_id'] = candidate_entry.id
                request.session['candidate_name'] = candidate_entry.candidate_name
                
                # Redirect to waiting page
                return redirect('waiting_for_round', event_id=event_id, round_number=round_number)
            else:
                messages.error(request, 'Incorrect access code!')
        except Round.DoesNotExist:
            messages.error(request, 'Round not found!')
        except Event.DoesNotExist:
            messages.error(request, 'Event not found!')
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
    
    try:
        event = Event.objects.get(id=event_id)
        context = {
            'event': event,
            'round_number': round_number,
            'event_id': event_id
        }
        return render(request, 'enter_round_password.html', context)
    except Event.DoesNotExist:
        messages.error(request, 'Event not found!')
        return redirect('candidate_login')


# Waiting for round to start
def waiting_for_round(request, event_id, round_number):
    """Display waiting page while admin starts the round"""
    try:
        event = Event.objects.get(id=event_id)
        round_obj = Round.objects.get(event=event, round_number=round_number)
        
        # Get candidate name and entry id from session
        candidate_name = request.session.get('candidate_name', 'Anonymous')
        candidate_entry_id = request.session.get('candidate_entry_id', None)
        
        context = {
            'event': event,
            'round': round_obj,
            'candidate_name': candidate_name,
            'candidate_entry_id': candidate_entry_id
        }
        return render(request, 'waiting_for_round.html', context)
    except Exception as e:
        messages.error(request, f'Error: {str(e)}')
        return redirect('candidate_login')


# Admin login
def admin_login(request):
    """Handle admin login with password only"""
    ADMIN_PASSWORD = 'gokul111'
    
    if request.method == 'POST':
        password = request.POST.get('password', '')
        
        if password == ADMIN_PASSWORD:
            # Password is correct, redirect to admin panel
            messages.success(request, 'Welcome to Admin Panel!')
            return redirect('admin_panel')
        else:
            # Password is incorrect
            messages.error(request, 'Password didn\'t match!')
    
    return render(request, 'admin_login.html')


# Admin panel
def admin_panel(request):
    """Display admin panel dashboard with events"""
    events = Event.objects.all()
    context = {
        'events': events
    }
    return render(request, 'admin_panel.html', context)


# Add event
def add_event(request):
    """Handle event creation"""
    if request.method == 'POST':
        event_name = request.POST.get('event_name')
        event_date = request.POST.get('event_date')
        number_of_rounds = request.POST.get('number_of_rounds')
        
        try:
            # Create the event
            event = Event.objects.create(
                name=event_name,
                date=event_date,
                number_of_rounds=int(number_of_rounds)
            )
            
            messages.success(request, f'Event "{event_name}" created successfully!')
        except Exception as e:
            messages.error(request, f'Error creating event: {str(e)}')
    
    return redirect('admin_panel')


# Delete event
def delete_event(request):
    """Handle event deletion"""
    if request.method == 'POST':
        event_id = request.POST.get('event_id')
        try:
            event = Event.objects.get(id=event_id)
            event_name = event.name
            event.delete()
            messages.success(request, f'Event "{event_name}" deleted successfully!')
        except Event.DoesNotExist:
            messages.error(request, 'Event not found.')
        except Exception as e:
            messages.error(request, f'Error deleting event: {str(e)}')
    
    return redirect('admin_panel')


# Round details
def round_details(request, event_id, round_number):
    """Display round details for an event"""
    try:
        event = Event.objects.get(id=event_id)
        
        # Get or create the Round object
        round_obj, created = Round.objects.get_or_create(
            event=event,
            round_number=round_number,
            defaults={'duration_minutes': 60}
        )
        
        # Auto-generate access code if it doesn't exist
        if not round_obj.access_code:
            round_obj.access_code = generate_access_code()
            round_obj.save()
        
        # Handle POST request for updating round settings
        if request.method == 'POST':
            duration = request.POST.get('duration_minutes')
            
            if duration:
                round_obj.duration_minutes = int(duration)
                round_obj.save()
                messages.success(request, 'Round settings updated successfully!')
                return redirect('round_details', event_id=event_id, round_number=round_number)
        
        context = {
            'event': event,
            'round': round_obj,
            'round_number': round_number
        }
        return render(request, 'round_details.html', context)
    except Event.DoesNotExist:
        messages.error(request, 'Event not found.')
        return redirect('admin_panel')


# Add question
def add_question(request, event_id, round_number):
    """Handle question creation"""
    if request.method == 'POST':
        try:
            event = Event.objects.get(id=event_id)
            round_obj = Round.objects.get(event=event, round_number=round_number)
            
            question_text = request.POST.get('question_text')
            correct_option = int(request.POST.get('correct_option'))
            
            # Create the question
            question = Question.objects.create(
                round=round_obj,
                question_text=question_text
            )
            
            # Create the options
            for i in range(1, 5):
                option_text = request.POST.get(f'option_{i}')
                is_correct = (i == correct_option)
                
                QuestionOption.objects.create(
                    question=question,
                    option_text=option_text,
                    option_number=i,
                    is_correct=is_correct
                )
            
            messages.success(request, 'Question added successfully!')
        except Exception as e:
            messages.error(request, f'Error adding question: {str(e)}')
    
    return redirect('round_details', event_id=event_id, round_number=round_number)


# Logout
def admin_logout(request):
    """Handle admin logout"""
    logout(request)
    messages.success(request, 'You have been logged out successfully!')
    return redirect('login_choice')


# API: Verify event password
@csrf_exempt
def verify_event_password(request, event_id):
    """API endpoint - No longer used, events don't have passwords"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        # Events no longer have passwords, return success
        return JsonResponse({'correct': True, 'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


# API: Get rounds for an event
@csrf_exempt
def get_rounds(request, event_id):
    """API endpoint to get rounds for an event"""
    try:
        event = Event.objects.get(id=event_id)
        rounds = event.get_rounds()
        return JsonResponse({
            'rounds': rounds,
            'success': True
        })
    except Event.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Event not found'
        }, status=404)


# API: Verify round access code
@csrf_exempt
def verify_round_password(request, event_id, round_number):
    """API endpoint to verify round access code"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        access_code = data.get('access_code')
        
        event = Event.objects.get(id=event_id)
        # Get the Round
        round_obj = Round.objects.get(event=event, round_number=round_number)
        
        if round_obj.access_code and round_obj.access_code == access_code:
            return JsonResponse({'correct': True, 'success': True})
        else:
            return JsonResponse({'correct': False, 'success': True})
    except Event.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Event not found'}, status=404)
    except Round.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Round not found'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


# Quiz Test Page
def quiz_test(request, event_id, round_number):
    """Display quiz test page for candidate - Only allow access once"""
    try:
        # Get candidate name and entry id from session
        candidate_name = request.session.get('candidate_name', None)
        candidate_entry_id = request.session.get('candidate_entry_id', None)
        
        # Check if candidate has valid session
        if not candidate_name or not candidate_entry_id:
            messages.error(request, 'Invalid session. Please login again.')
            return redirect('candidate_login')
        
        # Check if candidate has already accessed the quiz page (prevent refresh)
        quiz_session_key = f'quiz_accessed_{event_id}_{round_number}_{candidate_entry_id}'
        if request.session.get(quiz_session_key):
            # They've already accessed the quiz page - this is a refresh attempt
            messages.error(request, 'You cannot re-enter the quiz. Your attempt has been recorded.')
            return redirect('waiting_for_round', event_id=event_id, round_number=round_number)
        
        # Mark that this student has accessed the quiz page
        request.session[quiz_session_key] = True
        request.session.modified = True
        
        event = Event.objects.get(id=event_id)
        round_obj = Round.objects.get(event=event, round_number=round_number)
        questions = round_obj.questions.all()
        
        # Mark candidate as no longer waiting (they've started the quiz)
        if candidate_entry_id:
            try:
                candidate_entry = CandidateEntry.objects.get(id=candidate_entry_id)
                candidate_entry.is_waiting = False
                candidate_entry.save()
            except CandidateEntry.DoesNotExist:
                pass
        
        context = {
            'event': event,
            'round': round_obj,
            'round_number': round_number,
            'questions': questions,
            'total_questions': questions.count(),
            'candidate_name': candidate_name,
            'candidate_entry_id': candidate_entry_id
        }
        return render(request, 'quiz_test.html', context)
    except Exception as e:
        messages.error(request, f'Error loading quiz: {str(e)}')
        return redirect('candidate_login')


@csrf_exempt
def submit_quiz(request):
    """Handle quiz submission and send results to Telegram"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body)
        event_id = data.get('event_id')
        round_number = data.get('round_number')
        answers = data.get('answers', {})  # dict of question_id: option_id
        time_taken_seconds = data.get('time_taken_seconds', 0)  # time taken in seconds

        # Get event and round
        event = Event.objects.get(id=event_id)
        round_obj = Round.objects.get(event=event, round_number=round_number)
        questions = round_obj.questions.all()

        # Get candidate info
        candidate_name = data.get('candidate_name', 'Anonymous')

        logger.info(f"Submitting quiz for {candidate_name} - Event: {event.name}, Round: {round_number}")

        # Calculate score
        score = 0
        answered_count = 0
        answers_dict = {}

        for question_id_str, option_id_str in answers.items():
            try:
                question_id = int(question_id_str.replace('question_', ''))
                option_id = int(option_id_str)

                question = Question.objects.get(id=question_id, round=round_obj)
                option = QuestionOption.objects.get(id=option_id, question=question)

                answers_dict[f'question_{question_id}'] = option_id
                answered_count += 1

                # Check if correct
                if option.is_correct:
                    score += 1
            except (Question.DoesNotExist, QuestionOption.DoesNotExist, ValueError) as e:
                logger.warning(f"Error processing answer for question {question_id_str}: {str(e)}")
                continue

        total_questions = questions.count()
        percentage = (score / total_questions * 100) if total_questions > 0 else 0

        # Mark candidate as submitted with score and time
        try:
            from .models import CandidateEntry
            candidate_entries = CandidateEntry.objects.filter(
                round=round_obj,
                candidate_name=candidate_name
            )
            for entry in candidate_entries:
                entry.is_submitted = True
                entry.score = score
                entry.total_questions = total_questions
                entry.time_taken_seconds = time_taken_seconds
                entry.save()
            logger.info(f"Marked candidate {candidate_name} as submitted - Score: {score}/{total_questions} - Time: {time_taken_seconds}s")
        except Exception as e:
            logger.warning(f"Could not mark candidate as submitted: {str(e)}")

        logger.info(f"Quiz submission completed - Score: {score}/{total_questions} - Time: {time_taken_seconds}s")

        logger.info(f"✓ Quiz submission completed successfully")
        return JsonResponse({
            'success': True,
            'score': score,
            'total_questions': total_questions,
            'attended': answered_count,
            'percentage': percentage
        })

    except Event.DoesNotExist:
        logger.error(f"Event not found with ID: {event_id}")
        return JsonResponse({'success': False, 'error': 'Event not found'}, status=404)
    except Round.DoesNotExist:
        logger.error(f"Round not found - Event: {event_id}, Round: {round_number}")
        return JsonResponse({'success': False, 'error': 'Round not found'}, status=404)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in request: {str(e)}")
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Unexpected error in submit_quiz: {str(e)}")
        logger.error(traceback.format_exc())
        return JsonResponse({'success': False, 'error': f'Server error: {str(e)}'}, status=500)


@csrf_exempt
def check_round_started(request, event_id, round_number):
    """API endpoint to check if admin has started the round"""
    try:
        # Always get fresh data from database
        round_obj = Round.objects.get(event_id=event_id, round_number=round_number)
        is_started = round_obj.is_started
        logger.info(f"check_round_started - Event: {event_id}, Round: {round_number}, is_started: {is_started}")
        return JsonResponse({
            'started': is_started
        })
    except Round.DoesNotExist:
        logger.warning(f"Round not found - Event: {event_id}, Round: {round_number}")
        return JsonResponse({
            'started': False,
            'error': 'Round not found'
        }, status=404)
    except Exception as e:
        logger.error(f"check_round_started error: {str(e)}")
        return JsonResponse({
            'started': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
def update_candidate_active(request, candidate_entry_id):
    """API endpoint to update candidate's last_active timestamp"""
    try:
        candidate_entry = CandidateEntry.objects.get(id=candidate_entry_id)
        candidate_entry.last_active = timezone.now()
        candidate_entry.save()
        return JsonResponse({'success': True})
    except CandidateEntry.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Candidate not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


def start_round(request, event_id, round_number):
    """Render the Start Round page with round details and candidates."""
    try:
        round_obj = Round.objects.get(event_id=event_id, round_number=round_number)
        
        # Handle POST request to start the round
        if request.method == 'POST':
            # Only generate access code if not already started (first time only)
            if not round_obj.is_started:
                round_obj.access_code = generate_access_code()
            round_obj.is_started = True
            round_obj.save()
            logger.info(f"Round {round_number} started - is_started set to: {round_obj.is_started}")
            # Refresh from database to ensure we have the latest state
            round_obj.refresh_from_db()
            logger.info(f"After refresh - is_started: {round_obj.is_started}")
            messages.success(request, f'Round started! Access code: {round_obj.access_code}. No new candidates can join now.')
        else:
            # On GET request, ensure access code exists (for initial access)
            if not round_obj.access_code:
                round_obj.access_code = generate_access_code()
                round_obj.save()
        
        # Show all candidates who have entered this round
        all_candidates = CandidateEntry.objects.filter(round=round_obj).order_by('-is_submitted', 'entry_time')
        
        # Create a list with candidate info including status
        current_time = timezone.now()
        threshold_90s = current_time - timedelta(seconds=90)
        threshold_30s = current_time - timedelta(seconds=30)
        
        candidates_data = []
        
        if round_obj.is_started:
            # After round starts: show ONLY candidates actively giving test or submitted
            # 1. Candidates currently taking test (is_waiting=False, is_submitted=False, active in last 90 seconds)
            actively_testing = all_candidates.filter(
                is_waiting=False,
                is_submitted=False,
                last_active__gte=threshold_90s
            )
            
            # 2. Candidates who submitted (is_submitted=True)
            submitted = all_candidates.filter(is_submitted=True)
            
            # Combine the two groups
            display_candidates = list(submitted) + list(actively_testing)
            
            for candidate in display_candidates:
                if candidate.is_submitted:
                    status = "Submitted"
                elif not candidate.is_waiting and candidate.last_active >= threshold_90s:
                    status = "Giving Test"
                else:
                    status = "Left"
                
                # Format time taken
                time_display = ""
                if candidate.time_taken_seconds:
                    mins = candidate.time_taken_seconds // 60
                    secs = candidate.time_taken_seconds % 60
                    time_display = f"{mins}m {secs}s"
                
                candidates_data.append({
                    'id': candidate.id,
                    'name': candidate.candidate_name,
                    'is_submitted': candidate.is_submitted,
                    'is_waiting': candidate.is_waiting,
                    'entry_time': candidate.entry_time,
                    'last_active': candidate.last_active,
                    'status': status,
                    'score': candidate.score if candidate.score else 0,
                    'total_questions': candidate.total_questions if candidate.total_questions else 0,
                    'time_taken': time_display
                })
            
            display_label = "Candidates - All Status"
        else:
            # Before round starts: show only actively waiting candidates (active in last 30 seconds)
            display_candidates = all_candidates.filter(
                is_waiting=True,
                last_active__gte=threshold_30s
            )
            
            for candidate in display_candidates:
                candidates_data.append({
                    'id': candidate.id,
                    'name': candidate.candidate_name,
                    'is_submitted': candidate.is_submitted,
                    'is_waiting': candidate.is_waiting,
                    'entry_time': candidate.entry_time,
                    'last_active': candidate.last_active,
                    'status': "Waiting"
                })
            
            display_label = "Candidates Joined"
        
        context = {
            'round': round_obj,
            'candidates_data': candidates_data,
            'candidates': display_candidates,
            'display_label': display_label,
            'submitted_count': all_candidates.filter(is_submitted=True).count(),
            'total_count': all_candidates.count(),
            'event': round_obj.event,
        }
        return render(request, 'start_round.html', context)
    except Round.DoesNotExist:
        messages.error(request, 'Round not found!')
        return redirect('admin_panel')


def end_round(request, event_id, round_number):
    """End the round and redirect back to round details"""
    try:
        round_obj = Round.objects.get(event_id=event_id, round_number=round_number)
        
        if request.method == 'POST':
            round_obj.is_started = False
            round_obj.save()
            messages.success(request, 'Round has been ended successfully!')
            return redirect('round_details', event_id=event_id, round_number=round_number)
        else:
            # Redirect to start_round if not POST
            return redirect('start_round', event_id=event_id, round_number=round_number)
    except Round.DoesNotExist:
        messages.error(request, 'Round not found!')
        return redirect('admin_panel')
