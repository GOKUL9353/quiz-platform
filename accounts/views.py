from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.conf import settings
from .models import Event, Round, Question, QuestionOption, CandidateEntry
from .email_service import send_quiz_completion_email, send_quiz_results_email
from datetime import datetime
import json
import logging
import traceback

logger = logging.getLogger(__name__)


# Home page - redirect to login choice
def home(request):
    """Redirect to login choice page"""
    return redirect('login_choice')


# Login choice page - user selects candidate or admin
def login_choice(request):
    """Display login choice page"""
    return render(request, 'login_choice.html')


# Candidate login - Step 1: Event selection and event password
def candidate_login(request):
    """Handle candidate login - Step 1: Select event and enter event password"""
    if request.method == 'POST':
        event_id = request.POST.get('event_id')
        event_password = request.POST.get('event_password')
        
        try:
            event = Event.objects.get(id=event_id)
            
            # Verify event password
            if event.event_access_password == event_password:
                # Password correct, redirect to round selection
                return redirect('select_round', event_id=event_id)
            else:
                messages.error(request, 'Incorrect event password!')
        except Event.DoesNotExist:
            messages.error(request, 'Event not found!')
    
    events = Event.objects.all()
    context = {
        'events': events
    }
    return render(request, 'candidate_login.html', context)


# Candidate login - Step 2: Round selection and password verification
def select_round(request, event_id):
    """Handle round selection and password verification - Step 2"""
    try:
        event = Event.objects.get(id=event_id)
        
        if request.method == 'POST':
            candidate_name = request.POST.get('candidate_name')
            round_number = request.POST.get('round_number')
            round_password = request.POST.get('round_password')
            
            # Validate candidate name
            if not candidate_name or candidate_name.strip() == '':
                messages.error(request, 'Please enter your name or team name!')
                return redirect('candidate_login')
            
            # Validate round number is provided
            if not round_number:
                messages.error(request, 'Please select a round!')
                return redirect('candidate_login')
            
            try:
                round_number = int(round_number)
                # Create or get the Round object
                round_obj, created = Round.objects.get_or_create(
                    event=event,
                    round_number=round_number,
                    defaults={'duration_minutes': 60}
                )
                
                # Verify round password
                if round_obj.access_password == round_password:
                    # Password correct, create candidate entry and store in session
                    candidate_entry = CandidateEntry.objects.create(
                        event=event,
                        round=round_obj,
                        candidate_name=candidate_name.strip()
                    )
                    
                    # Store candidate entry ID in session
                    request.session['candidate_entry_id'] = candidate_entry.id
                    request.session['candidate_name'] = candidate_entry.candidate_name
                    
                    # Redirect to quiz test
                    return redirect('quiz_test', event_id=event_id, round_number=round_number)
                else:
                    messages.error(request, 'Incorrect round password!')
                    return redirect('candidate_login')
            except ValueError:
                messages.error(request, 'Invalid round number!')
                return redirect('candidate_login')
        
        # GET request - redirect to candidate login
        return redirect('candidate_login')
    except Event.DoesNotExist:
        messages.error(request, 'Event not found!')
        return redirect('candidate_login')


# Candidate login - Step 3: Round password verification
def verify_round_login(request, event_id, round_number):
    """Handle round password verification - Step 3: Verify round password"""
    if request.method == 'POST':
        round_password = request.POST.get('round_password')
        
        try:
            event = Event.objects.get(id=event_id)
            round_obj, created = Round.objects.get_or_create(
                event=event,
                round_number=round_number,
                defaults={'duration_minutes': 60}
            )
            
            # Verify round password
            if round_obj.access_password == round_password:
                # Password correct, redirect to quiz test
                return redirect('quiz_test', event_id=event_id, round_number=round_number)
            else:
                messages.error(request, 'Incorrect round password!')
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
        event_password = request.POST.get('event_access_password')
        
        try:
            # Create the event
            event = Event.objects.create(
                name=event_name,
                date=event_date,
                number_of_rounds=int(number_of_rounds),
                event_access_password=event_password
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
            password = request.POST.get('access_password')
            owner_email = request.POST.get('owner_email')
            
            if duration and password:
                round_obj.duration_minutes = int(duration)
                round_obj.access_password = password
                round_obj.owner_email = owner_email if owner_email else None
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
    """API endpoint to verify event password"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        password = data.get('password')
        
        event = Event.objects.get(id=event_id)
        
        if event.event_access_password == password:
            return JsonResponse({'correct': True, 'success': True})
        else:
            return JsonResponse({'correct': False, 'success': True})
    except Event.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Event not found'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
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


# API: Verify round password
@csrf_exempt
def verify_round_password(request, event_id, round_number):
    """API endpoint to verify round password"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        password = data.get('password')
        
        event = Event.objects.get(id=event_id)
        # Create Round if it doesn't exist
        round_obj, created = Round.objects.get_or_create(
            event=event,
            round_number=round_number,
            defaults={'duration_minutes': 60}
        )
        
        if round_obj.access_password == password:
            return JsonResponse({'correct': True, 'success': True})
        else:
            return JsonResponse({'correct': False, 'success': True})
    except Event.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Event not found'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


# Quiz Test Page
def quiz_test(request, event_id, round_number):
    """Display quiz test page for candidate"""
    try:
        event = Event.objects.get(id=event_id)
        round_obj = Round.objects.get(event=event, round_number=round_number)
        questions = round_obj.questions.all()
        
        # Get candidate name from session
        candidate_name = request.session.get('candidate_name', 'Anonymous')
        candidate_entry_id = request.session.get('candidate_entry_id', None)
        
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
    """Handle quiz submission and send results email"""
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
        
        logger.info(f"Quiz submission completed - Score: {score}/{total_questions} - Time: {time_taken_seconds}s")
        
        # Send results email to round owner
        if round_obj.owner_email:
            try:
                logger.info(f"📧 Attempting to send results email to owner: {round_obj.owner_email}")
                
                # Check if email is configured
                if not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
                    logger.warning('⚠️  Email not configured (missing EMAIL_HOST_USER or EMAIL_HOST_PASSWORD) - skipping owner notification')
                else:
                    logger.info(f"✓ Email credentials found, sending to {round_obj.owner_email}")
                    result = send_quiz_results_email(
                        owner_email=round_obj.owner_email,
                        event_name=event.name,
                        round_number=round_number,
                        candidate_name=candidate_name,
                        score=score,
                        total_questions=total_questions,
                        time_taken_seconds=time_taken_seconds
                    )
                    if result:
                        logger.info(f"✅ Email sent successfully to {round_obj.owner_email}")
                    else:
                        logger.error(f"❌ Email failed to send to {round_obj.owner_email} (check SMTP settings)")
            except Exception as email_error:
                logger.error(f"❌ Exception while sending email: {type(email_error).__name__}: {str(email_error)}")
                logger.error(traceback.format_exc())
        else:
            logger.warning(f"⚠️  Round {round_number} has no owner_email set - cannot send results")
        
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
