from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.contrib.auth import logout
from django.http import JsonResponse
from .models import Event, Round, Question, QuestionOption, CandidateEntry
from datetime import timedelta
from django.utils import timezone
from django.db.models import Count, Prefetch
import json
import logging
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
            
            # Check if hosting is active
            if not round_obj.is_hosting:
                messages.error(request, 'Hosting has not started yet or has ended! Please ask the host to start hosting.')
                return redirect('candidate_login')
            
            # Check if round has already started
            if round_obj.is_started:
                messages.error(request, 'This round has already started! No new candidates can join.')
                return redirect('candidate_login')
            
            event = round_obj.event
            
            # Check if candidate with this name + access code already exists for this round
            existing_entry = CandidateEntry.objects.filter(
                round=round_obj,
                candidate_name=candidate_name,
                access_code_used=access_code
            ).first()
            
            if existing_entry:
                # Reuse existing entry - update last_active timestamp and reset waiting status
                existing_entry.last_active = timezone.now()
                existing_entry.is_waiting = True  # Reset waiting status in case they left and came back
                existing_entry.save()
                candidate_entry = existing_entry
            else:
                # Create new candidate entry with access code used
                candidate_entry = CandidateEntry.objects.create(
                    event=event,
                    round=round_obj,
                    candidate_name=candidate_name,
                    access_code_used=access_code,
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


# Waiting for round to start
def waiting_for_round(request, event_id, round_number):
    """Display waiting page while admin starts the round"""
    try:
        event = Event.objects.get(id=event_id)
        round_obj = Round.objects.select_related('event').get(event=event, round_number=round_number)
        
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
    # Optimize query by prefetching related rounds and candidate entries
    events = Event.objects.prefetch_related(
        Prefetch('rounds', Round.objects.prefetch_related('questions'))
    ).annotate(
        total_rounds=Count('rounds')
    ).all()
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
            round_obj = Round.objects.select_related('event').get(event=event, round_number=round_number)
            
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


@csrf_exempt
def delete_question(request, event_id, round_number, question_id):
    """API endpoint to delete a question"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        event = Event.objects.get(id=event_id)
        round_obj = Round.objects.select_related('event').get(event=event, round_number=round_number)
        question = Question.objects.get(id=question_id, round=round_obj)
        
        # Delete the question (this will cascade delete associated options)
        question.delete()
        
        return JsonResponse({'success': True, 'message': 'Question deleted successfully'})
    except Event.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Event not found'}, status=404)
    except Round.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Round not found'}, status=404)
    except Question.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Question not found'}, status=404)
    except Exception as e:
        logger.error(f"delete_question error: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


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
    except Exception as e:
        logger.error(f"verify_round_password error: {str(e)}")
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
        # Optimize: prefetch questions with their options to avoid N+1 queries
        round_obj = Round.objects.prefetch_related(
            Prefetch('questions', Question.objects.prefetch_related('options'))
        ).get(event=event, round_number=round_number)
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
        # Optimize: prefetch questions with their options to avoid N+1 queries
        round_obj = Round.objects.prefetch_related(
            Prefetch('questions', Question.objects.prefetch_related('options'))
        ).get(event=event, round_number=round_number)
        questions = round_obj.questions.all()

        # Get candidate info
        candidate_name = data.get('candidate_name', 'Anonymous')

        logger.info(f"Submitting quiz for {candidate_name} - Event: {event.name}, Round: {round_number}")

        # Calculate score
        score = 0
        answered_count = 0
        answers_dict = {}
        # Cache questions and options in memory to avoid repeated queries
        questions_cache = {q.id: q for q in questions}
        options_cache = {}
        for q in questions:
            options_cache[q.id] = {o.id: o for o in q.options.all()}

        for question_id_str, option_id_str in answers.items():
            try:
                question_id = int(question_id_str.replace('question_', ''))
                option_id = int(option_id_str)

                # Use cached data instead of querying database
                if question_id not in questions_cache:
                    logger.warning(f"Question {question_id} not found in round")
                    continue
                
                question = questions_cache[question_id]
                
                if option_id not in options_cache.get(question_id, {}):
                    logger.warning(f"Option {option_id} not found for question {question_id}")
                    continue
                
                option = options_cache[question_id][option_id]

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


@csrf_exempt
def check_round_started(request, event_id, round_number):
    """API endpoint to check if admin has started the round"""
    try:
        # Optimize: Only fetch the fields we need
        is_started = Round.objects.filter(
            event_id=event_id, 
            round_number=round_number
        ).values_list('is_started', flat=True).first()
        
        logger.info(f"check_round_started - Event: {event_id}, Round: {round_number}, is_started: {is_started}")
        return JsonResponse({
            'started': is_started if is_started is not None else False
        })
    except Exception as e:
        logger.error(f"check_round_started error: {str(e)}")
        return JsonResponse({
            'started': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@csrf_exempt
def update_candidate_active(request, candidate_entry_id):
    """API endpoint to update candidate's last_active timestamp"""
    try:
        candidate_entry = CandidateEntry.objects.get(id=candidate_entry_id)
        current_time = timezone.now()
        candidate_entry.last_active = current_time
        
        # If round hasn't started yet and candidate was marked as not waiting, mark them as waiting again (they came back)
        if candidate_entry.round and not candidate_entry.round.is_started and not candidate_entry.is_waiting and not candidate_entry.is_submitted:
            candidate_entry.is_waiting = True
            logger.info(f"Candidate {candidate_entry.candidate_name} (ID: {candidate_entry_id}) re-activated heartbeat, marked as waiting again")
        
        candidate_entry.save(update_fields=['last_active', 'is_waiting'])
        return JsonResponse({'success': True, 'last_active': current_time.isoformat()})
    except CandidateEntry.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Candidate not found'}, status=404)
    except Exception as e:
        logger.error(f"update_candidate_active error: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
def exit_waiting(request, candidate_entry_id):
    """API endpoint to mark candidate as exited from waiting room"""
    # Accept both GET and POST (sendBeacon uses POST, beforeunload uses both)
    try:
        candidate_entry = CandidateEntry.objects.get(id=candidate_entry_id)
        
        # Only mark as not waiting if round hasn't started yet
        if candidate_entry.round and not candidate_entry.round.is_started:
            candidate_entry.is_waiting = False
            candidate_entry.save(update_fields=['is_waiting'])
            logger.info(f"Candidate {candidate_entry.candidate_name} (ID: {candidate_entry_id}) marked as exited from waiting room")
        
        return JsonResponse({'success': True, 'message': 'Candidate marked as exited'})
    except CandidateEntry.DoesNotExist:
        logger.warning(f"exit_waiting called for non-existent candidate ID: {candidate_entry_id}")
        return JsonResponse({'success': False, 'error': 'Candidate not found'}, status=404)
    except Exception as e:
        logger.error(f"exit_waiting error: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
def init_waiting(request, candidate_entry_id):
    """API endpoint to initialize/refresh candidate's waiting status on page load/refresh"""
    try:
        candidate_entry = CandidateEntry.objects.get(id=candidate_entry_id)
        current_time = timezone.now()
        
        # Only reset waiting status if round hasn't started yet
        if candidate_entry.round and not candidate_entry.round.is_started and not candidate_entry.is_submitted:
            candidate_entry.is_waiting = True
            candidate_entry.last_active = current_time
            candidate_entry.save(update_fields=['is_waiting', 'last_active'])
            logger.info(f"Candidate {candidate_entry.candidate_name} (ID: {candidate_entry_id}) re-initialized waiting status")
        else:
            # Just update the heartbeat even if round has started
            candidate_entry.last_active = current_time
            candidate_entry.save(update_fields=['last_active'])
        
        return JsonResponse({'success': True, 'message': 'Waiting status initialized'})
    except CandidateEntry.DoesNotExist:
        logger.warning(f"init_waiting called for non-existent candidate ID: {candidate_entry_id}")
        return JsonResponse({'success': False, 'error': 'Candidate not found'}, status=404)
    except Exception as e:
        logger.error(f"init_waiting error: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


def mark_tab_switched(request, candidate_entry_id):
    """API endpoint to mark when candidate switches tabs"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        candidate_entry = CandidateEntry.objects.get(id=candidate_entry_id)
        candidate_entry.has_switched_tabs = True
        candidate_entry.save(update_fields=['has_switched_tabs'])
        logger.info(f"Marked candidate {candidate_entry.candidate_name} (ID: {candidate_entry_id}) as switched tabs")
        return JsonResponse({'success': True, 'message': 'Tab switch recorded'})
    except CandidateEntry.DoesNotExist:
        logger.warning(f"mark_tab_switched called for non-existent candidate ID: {candidate_entry_id}")
        return JsonResponse({'success': False, 'error': 'Candidate not found'}, status=404)
    except Exception as e:
        logger.error(f"mark_tab_switched error: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@csrf_exempt
def check_hosting_status(request, event_id, round_number):
    """API endpoint to check if hosting is still active"""
    if request.method != 'GET':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        # Optimize: Only fetch the fields we need
        status = Round.objects.filter(
            event_id=event_id, 
            round_number=round_number
        ).values('is_hosting', 'is_started').first()
        
        if status:
            return JsonResponse({
                'success': True,
                'is_hosting': status['is_hosting'],
                'is_started': status['is_started']
            })
        else:
            return JsonResponse({'success': False, 'error': 'Round not found'}, status=404)
    except Exception as e:
        logger.error(f"check_hosting_status error: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


def start_round(request, event_id, round_number):
    """Render the Start Round page with round details and candidates."""
    try:
        # Optimize: use select_related for event to avoid N+1 queries
        round_obj = Round.objects.select_related('event').get(event_id=event_id, round_number=round_number)
        
        # Show ONLY candidates who have entered with the current round's access code
        all_candidates = CandidateEntry.objects.filter(
            round=round_obj,
            access_code_used=round_obj.access_code
        ).order_by('-is_submitted', 'entry_time') if round_obj.access_code else CandidateEntry.objects.none()
        
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
        elif round_obj.is_hosting:
            # During hosting: show ALL waiting candidates (not filtering by time since they're just waiting)
            display_candidates = all_candidates.filter(is_waiting=True)
            
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
        else:
            # Before hosting starts: show waiting candidates  
            display_candidates = all_candidates.filter(is_waiting=True)
            
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
            
            display_label = "No candidates yet"
        
        context = {
            'round': round_obj,
            'candidates_data': candidates_data,
            'candidates': display_candidates if 'display_candidates' in locals() else [],
            'display_label': display_label,
            'submitted_count': all_candidates.filter(is_submitted=True).count() if all_candidates else 0,
            'total_count': all_candidates.count() if all_candidates else 0,
            'event': round_obj.event,
        }
        return render(request, 'start_round.html', context)
    except Round.DoesNotExist:
        messages.error(request, 'Round not found!')
        return redirect('admin_panel')


@csrf_exempt
def api_start_hosting(request, event_id, round_number):
    """API endpoint to start hosting - generate NEW access code and set is_hosting=True"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        round_obj = Round.objects.select_related('event').get(event_id=event_id, round_number=round_number)
        
        # Always generate a FRESH access code when starting hosting
        round_obj.access_code = generate_access_code()
        round_obj.is_hosting = True
        round_obj.is_started = False
        round_obj.save()
        
        logger.info(f"New hosting session started for Round {round_number} with access code: {round_obj.access_code}")
        
        return JsonResponse({
            'success': True,
            'access_code': round_obj.access_code,
            'message': 'Hosting started successfully with new access code!'
        })
    except Round.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Round not found'}, status=404)
    except Exception as e:
        logger.error(f"api_start_hosting error: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
def api_end_hosting(request, event_id, round_number):
    """API endpoint to end hosting - clear access code and set is_hosting=False and is_started=False"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        round_obj = Round.objects.select_related('event').get(event_id=event_id, round_number=round_number)
        round_obj.is_hosting = False
        round_obj.is_started = False
        round_obj.access_code = None  # Clear the access code
        round_obj.save()
        
        logger.info(f"Hosting ended for Round {round_number}. Access code cleared.")
        
        return JsonResponse({
            'success': True,
            'message': 'Hosting ended successfully! Access code cleared.'
        })
    except Round.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Round not found'}, status=404)
    except Exception as e:
        logger.error(f"api_end_hosting error: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
def api_start_test(request, event_id, round_number):
    """API endpoint to start test - set is_started=True"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        round_obj = Round.objects.select_related('event').get(event_id=event_id, round_number=round_number)
        round_obj.is_started = True
        round_obj.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Test started successfully!'
        })
    except Round.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Round not found'}, status=404)
    except Exception as e:
        logger.error(f"api_start_test error: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
def api_get_candidates(request, event_id, round_number):
    """API endpoint to get current candidates list"""
    if request.method != 'GET':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        # Optimize: use select_related for event to avoid N+1 queries
        round_obj = Round.objects.select_related('event').get(event_id=event_id, round_number=round_number)
        
        # Get all candidates for this round
        all_candidates = CandidateEntry.objects.filter(
            round=round_obj,
            access_code_used=round_obj.access_code
        ).order_by('-is_submitted', 'entry_time') if round_obj.access_code else CandidateEntry.objects.none()
        
        current_time = timezone.now()
        threshold_90s = current_time - timedelta(seconds=90)
        threshold_30s = current_time - timedelta(seconds=30)
        threshold_45s = current_time - timedelta(seconds=45)  # For waiting room timeout
        waiting_timeout = current_time - timedelta(seconds=45)  # Reduced from 60 to 45 seconds for faster detection
        
        candidates_data = []
        
        if round_obj.is_started:
            # After round starts: show only candidates actively giving test or submitted
            # Filter out ghost candidates who never actually interacted
            
            # Submitted candidates (always show)
            submitted = all_candidates.filter(is_submitted=True)
            
            # Actively testing candidates (must have recent activity AND have ever sent a heartbeat)
            # Only show if they're actually testing and have been active in last 90 seconds
            # Exclude ghost entries (those created but never sent a heartbeat - activity within 1 second of creation)
            currently_active = []
            for candidate in all_candidates.filter(
                is_waiting=False,
                is_submitted=False,
                last_active__gte=threshold_90s
            ):
                # Skip if candidate never actually sent a heartbeat (entry_time == last_active)
                time_diff = (candidate.last_active - candidate.entry_time).total_seconds()
                if time_diff > 1:  # If more than 1 second has passed since creation, they sent a real update
                    currently_active.append(candidate)
            
            actively_testing = currently_active
            
            display_candidates = list(submitted) + list(actively_testing)
            
            for candidate in display_candidates:
                if candidate.is_submitted:
                    status = "Submitted"
                elif not candidate.is_waiting and candidate.last_active >= threshold_90s:
                    status = "Giving Test"
                else:
                    status = "Left"
                
                time_display = ""
                if candidate.time_taken_seconds:
                    mins = candidate.time_taken_seconds // 60
                    secs = candidate.time_taken_seconds % 60
                    time_display = f"{mins}m {secs}s"
                
                candidates_data.append({
                    'id': candidate.id,
                    'name': candidate.candidate_name,
                    'is_submitted': candidate.is_submitted,
                    'status': status,
                    'score': candidate.score if candidate.score else 0,
                    'total_questions': candidate.total_questions if candidate.total_questions else 0,
                    'time_taken': time_display,
                    'has_switched_tabs': candidate.has_switched_tabs
                })
        else:
            # Before round starts (hosting): show all candidates who entered, with their status
            # Display their current state: Waiting, Inactive, or Left
            
            # First, auto-mark candidates as inactive if they've timed out (no heartbeat for 45s)
            inactive_candidates = all_candidates.filter(
                is_waiting=True,
                last_active__lt=waiting_timeout
            )
            if inactive_candidates.exists():
                marked_count = inactive_candidates.update(is_waiting=False)  # Mark them as no longer waiting
                logger.info(f"Auto-marked {marked_count} candidates as inactive (no heartbeat > 45s) for Round {round_number}")
            
            # Get all candidates for display (both waiting and left)
            # Waiting candidates with recent heartbeat
            actively_waiting = all_candidates.filter(
                is_waiting=True
            ).order_by('entry_time')
            
            # Candidates who left the waiting room (is_waiting=False) but round hasn't started yet
            left_candidates = all_candidates.filter(
                is_waiting=False,
                is_submitted=False
            ).order_by('entry_time')
            
            # Combine: waiting candidates first (sorted by entry time), then left candidates
            combined_candidates = list(actively_waiting) + list(left_candidates)
            
            for candidate in combined_candidates:
                # Determine status based on current state
                if candidate.is_waiting:
                    if candidate.last_active >= waiting_timeout:
                        status = "Waiting"
                    else:
                        status = "Inactive"  # Was waiting but timed out
                else:
                    status = "Left"  # Explicitly left or timed out and marked as left
                
                candidates_data.append({
                    'id': candidate.id,
                    'name': candidate.candidate_name,
                    'is_submitted': candidate.is_submitted,
                    'status': status,
                    'score': 0,
                    'total_questions': 0,
                    'time_taken': '',
                    'has_switched_tabs': candidate.has_switched_tabs
                })
        
        
        return JsonResponse({
            'success': True,
            'candidates': candidates_data
        })
    except Round.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Round not found'}, status=404)
    except Exception as e:
        logger.error(f"api_get_candidates error: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


def end_round(request, event_id, round_number):
    """End the round and redirect back to round details"""
    try:
        round_obj = Round.objects.select_related('event').get(event_id=event_id, round_number=round_number)
        
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
