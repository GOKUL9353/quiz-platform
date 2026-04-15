from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.contrib.auth import logout
from django.http import JsonResponse
from .models import Event, Round, Question, QuestionOption, CandidateEntry, CodingQuestion, DubbingQuestion, TestCase, DubbingTestCase
from datetime import timedelta
from django.utils import timezone
from django.db.models import Count, Prefetch
import json
import logging
import random
import string
import urllib.request
import urllib.error

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
        
        # Check if candidate has exited
        if candidate_entry_id:
            try:
                candidate_entry = CandidateEntry.objects.get(id=candidate_entry_id)
                if not candidate_entry.is_waiting or candidate_entry.is_submitted:
                    messages.error(request, 'You have exited the waiting room.')
                    return redirect('candidate_login')
            except CandidateEntry.DoesNotExist:
                messages.error(request, 'Invalid session. Please login again.')
                return redirect('candidate_login')
        
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
            'round_number': round_number,
            'coding_questions': round_obj.coding_questions.all(),
            'dubbing_questions': round_obj.dubbing_questions.all(),
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


@csrf_exempt
def delete_coding_question(request, event_id, round_number, question_id):
    """API endpoint to delete a coding question"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        CodingQuestion.objects.filter(id=question_id, round__event_id=event_id, round__round_number=round_number).delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
def delete_dubbing_question(request, event_id, round_number, question_id):
    """API endpoint to delete a dubbing question"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        DubbingQuestion.objects.filter(id=question_id, round__event_id=event_id, round__round_number=round_number).delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# Logout
def admin_logout(request):
    """Handle admin logout"""
    logout(request)
    messages.success(request, 'You have been logged out successfully!')
    return redirect('login_choice')


# Add coding question
def add_coding_question(request, event_id, round_number):
    """Handle coding question creation"""
    if request.method == 'POST':
        try:
            event = Event.objects.get(id=event_id)
            round_obj = Round.objects.get(event=event, round_number=round_number)

            coding_q = CodingQuestion.objects.create(
                round=round_obj,
                title=request.POST.get('title', '').strip(),
                problem_statement=request.POST.get('problem_statement', '').strip(),
                input_format=request.POST.get('input_format', '').strip(),
                output_format=request.POST.get('output_format', '').strip(),
                constraints=request.POST.get('constraints', '').strip(),
                sample_input=request.POST.get('sample_input', '').strip(),
                sample_output=request.POST.get('sample_output', '').strip(),
            )

            # Save test cases (up to 10)
            for i in range(1, 11):
                tc_input = request.POST.get(f'tc_input_{i}', '').strip()
                tc_output = request.POST.get(f'tc_output_{i}', '').strip()
                if tc_output:  # Only save if expected output is provided
                    TestCase.objects.create(
                        coding_question=coding_q,
                        input_data=tc_input,
                        expected_output=tc_output,
                        order=i
                    )

            messages.success(request, 'Coding question added successfully!')
        except Exception as e:
            messages.error(request, f'Error adding coding question: {str(e)}')
    return redirect('round_details', event_id=event_id, round_number=round_number)


# Add dubbing question
def add_dubbing_question(request, event_id, round_number):
    """Handle dubbing (code-snippet) question creation"""
    if request.method == 'POST':
        try:
            event = Event.objects.get(id=event_id)
            round_obj = Round.objects.get(event=event, round_number=round_number)

            dubbing_q = DubbingQuestion.objects.create(
                round=round_obj,
                title=request.POST.get('title', '').strip(),
                description=request.POST.get('description', '').strip(),
                language=request.POST.get('language', 'python'),
                code_snippet=request.POST.get('code_snippet', '').strip(),
                sample_input=request.POST.get('sample_input', '').strip(),
                sample_output=request.POST.get('sample_output', '').strip(),
            )

            # Save test cases (up to 10)
            for i in range(1, 11):
                tc_input = request.POST.get(f'tc_input_{i}', '').strip()
                tc_output = request.POST.get(f'tc_output_{i}', '').strip()
                if tc_output:  # Only save if expected output is provided
                    DubbingTestCase.objects.create(
                        dubbing_question=dubbing_q,
                        input_data=tc_input,
                        expected_output=tc_output,
                        order=i
                    )
            messages.success(request, 'Dubbing question added successfully!')
        except Exception as e:
            messages.error(request, f'Error adding dubbing question: {str(e)}')
    return redirect('round_details', event_id=event_id, round_number=round_number)


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
        
        # Verify candidate entry exists and is still eligible
        try:
            candidate_entry = CandidateEntry.objects.get(id=candidate_entry_id)
            # Check if candidate has exited (is_waiting=False) or already submitted
            if not candidate_entry.is_waiting or candidate_entry.is_submitted:
                messages.error(request, 'You are not eligible to take this quiz.')
                return redirect('candidate_login')
        except CandidateEntry.DoesNotExist:
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
            Prefetch('questions', Question.objects.prefetch_related('options')),
            'coding_questions',
            'dubbing_questions'
        ).get(event=event, round_number=round_number)
        questions = round_obj.questions.all()
        coding_questions = round_obj.coding_questions.all()
        dubbing_questions = round_obj.dubbing_questions.all()
        
        # Mark candidate as no longer waiting (they've started the quiz)
        if candidate_entry_id:
            try:
                candidate_entry = CandidateEntry.objects.get(id=candidate_entry_id)
                candidate_entry.is_waiting = False
                candidate_entry.quiz_started_at = timezone.now()  # Mark quiz started
                candidate_entry.save()
            except CandidateEntry.DoesNotExist:
                pass
        
        context = {
            'event': event,
            'round': round_obj,
            'round_number': round_number,
            'questions': questions,
            'coding_questions': coding_questions,
            'dubbing_questions': dubbing_questions,
            'total_questions': questions.count() + coding_questions.count() + dubbing_questions.count(),
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
        
        # Validate required fields
        if not event_id or not round_number:
            return JsonResponse({'success': False, 'error': 'Missing event_id or round_number'}, status=400)
        
        if not isinstance(answers, dict):
            return JsonResponse({'success': False, 'error': 'Invalid answers format'}, status=400)

        # Get event and round
        event = Event.objects.get(id=event_id)
        # Optimize: prefetch questions with their options to avoid N+1 queries
        round_obj = Round.objects.prefetch_related(
            Prefetch('questions', Question.objects.prefetch_related('options'))
        ).get(event=event, round_number=round_number)
        questions = round_obj.questions.all()

        # Get candidate info
        candidate_name = data.get('candidate_name', 'Anonymous')

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
                # Safely extract question ID
                if isinstance(question_id_str, str):
                    if question_id_str.startswith('question_'):
                        question_id = int(question_id_str.replace('question_', ''))
                    else:
                        question_id = int(question_id_str)
                else:
                    question_id = int(question_id_str)
                    
                # Convert option ID to int
                option_id = int(option_id_str)

                # Use cached data instead of querying database
                if question_id not in questions_cache:
                    continue
                
                question = questions_cache[question_id]
                
                if option_id not in options_cache.get(question_id, {}):
                    continue
                
                option = options_cache[question_id][option_id]

                answers_dict[f'question_{question_id}'] = option_id
                answered_count += 1

                # Check if correct
                if option.is_correct:
                    score += 1
            except (ValueError, TypeError) as e:
                logger.warning(f"Error processing answer for question {question_id_str}: {str(e)}")
                continue
            except Exception as e:
                logger.warning(f"Unexpected error processing answer for question {question_id_str}: {str(e)}")
                continue

        total_questions = questions.count()
        percentage = (score / total_questions * 100) if total_questions > 0 else 0

        # Initialize scoring breakdown variables
        total_testcase_score = 0
        total_output_score = 0
        total_efficiency_score = 0
        total_test_cases_passed = 0
        total_test_cases = 0
        total_max_possible_score = total_questions  # Start with MCQ max score

        # Mark candidate as submitted with score and time
        # Find the specific candidate entry that submitted (by name and round)
        try:
            from .models import CandidateEntry, CodeSubmission, CodingQuestion, DubbingQuestion
            import subprocess, tempfile, os, shutil, re, time
            
            # Use more specific criteria to avoid updating wrong candidates
            candidate_entry = CandidateEntry.objects.filter(
                round=round_obj,
                candidate_name=candidate_name,
                is_waiting=False,  # Should have started the quiz
                is_submitted=False  # Not already submitted
            ).first()
            
            if candidate_entry:
                # === GRADE CODE SUBMISSIONS ===
                def run_eval(code, language, test_cases, tmp_dir):
                    if not code: return 0, 0, False, 0.0, False
                    
                    # prepare
                    timeout = 5
                    runner = None
                    cmd_args = []
                    compile_err = None
                    if language == 'python':
                        src = os.path.join(tmp_dir, 'solution.py')
                        with open(src, 'w', encoding='utf-8') as f: f.write(code)
                        runner, cmd_args = 'python', [src]
                    elif language == 'c':
                        src = os.path.join(tmp_dir, 'solution.c')
                        exe = os.path.join(tmp_dir, 'solution.exe')
                        with open(src, 'w', encoding='utf-8') as f: f.write(code)
                        comp = subprocess.run(['gcc', src, '-o', exe, '-lm'], capture_output=True, text=True, timeout=15, cwd=tmp_dir)
                        if comp.returncode != 0: compile_err = comp.stderr
                        runner, cmd_args = 'exe', [exe]
                    elif language == 'java':
                        m = re.search(r'public\s+class\s+(\w+)', code)
                        class_name = m.group(1) if m else 'Solution'
                        src = os.path.join(tmp_dir, f'{class_name}.java')
                        with open(src, 'w', encoding='utf-8') as f: f.write(code)
                        comp = subprocess.run(['javac', src], capture_output=True, text=True, timeout=15, cwd=tmp_dir)
                        if comp.returncode != 0: compile_err = comp.stderr
                        runner, cmd_args = 'java', ['-cp', tmp_dir, class_name]
                    
                    if compile_err or not runner:
                        return 0, len(test_cases), False, 0.0, False
                        
                    passed = 0
                    total_time = 0.0
                    output_success = False
                    
                    for tc in test_cases:
                        clean_input = tc.input_data.replace('\r\n', '\n').replace('\r', '\n')
                        if runner == 'python': cmd = ['python'] + cmd_args
                        elif runner == 'exe': cmd = cmd_args
                        elif runner == 'java': cmd = ['java'] + cmd_args
                        
                        start_t = time.time()
                        try:
                            res = subprocess.run(cmd, input=clean_input, capture_output=True, text=True, timeout=timeout, cwd=tmp_dir)
                            elapsed = time.time() - start_t
                            total_time += elapsed
                            if res.returncode == 0:
                                output_success = True
                            actual = res.stdout.strip().replace('\r\n', '\n').replace('\r', '\n')
                            expected = tc.expected_output.strip().replace('\r\n', '\n').replace('\r', '\n')
                            if actual == expected and res.returncode == 0:
                                passed += 1
                        except subprocess.TimeoutExpired:
                            total_time += timeout
                    
                    avg_time_ms = (total_time / len(test_cases) * 1000) if test_cases else 0.0
                    time_met = avg_time_ms < 1000.0 if test_cases else False
                    if not test_cases and runner: # if no testcases but compiles visually run once if we want to check output success
                        pass
                    return passed, len(test_cases), output_success, avg_time_ms, time_met

                # Group coding answers by question_id
                coding_subs = {}
                dubbing_subs = {}
                for k, v in answers.items():
                    if k.startswith('coding_code_'):
                        qid = int(k.split('_')[2])
                        if qid not in coding_subs: coding_subs[qid] = {'code': v, 'lang': 'python'}
                        else: coding_subs[qid]['code'] = v
                    elif k.startswith('coding_lang_'):
                        qid = int(k.split('_')[2])
                        if qid not in coding_subs: coding_subs[qid] = {'lang': v, 'code': ''}
                        else: coding_subs[qid]['lang'] = v
                    elif k.startswith('dubbing_code_'):
                        qid = int(k.split('_')[2])
                        if qid not in dubbing_subs: dubbing_subs[qid] = {'code': v, 'lang': 'python'}
                        else: dubbing_subs[qid]['code'] = v
                    elif k.startswith('dubbing_lang_'):
                        qid = int(k.split('_')[2])
                        if qid not in dubbing_subs: dubbing_subs[qid] = {'lang': v, 'code': ''}
                        else: dubbing_subs[qid]['lang'] = v

                tmp_dir = tempfile.mkdtemp(prefix='quiz_submit_')
                
                try:
                    def evaluate_and_save(q_dict, q_type, model_cls):
                        nonlocal score, total_testcase_score, total_output_score, total_efficiency_score
                        nonlocal total_test_cases_passed, total_test_cases, total_max_possible_score
                        for qid, payload in q_dict.items():
                            try:
                                q_obj = model_cls.objects.get(id=qid)
                                tcs = list(q_obj.test_cases.all())
                                passed, total, out_ok, exec_ms, time_met = run_eval(payload['code'], payload['lang'], tcs, tmp_dir)
                                
                                # Scoring Logic
                                # Test Cases: 2 marks per passing test case
                                tc_marks = passed * 2
                                
                                # Output Success: 2 marks if output is correct
                                out_marks = 2 if out_ok else 0
                                
                                # Efficiency: 2 marks if time limit met
                                eff_marks = 2 if (time_met and passed > 0) else 0
                                
                                # Total: sum of all marks
                                q_score = tc_marks + out_marks + eff_marks
                                score += q_score
                                
                                # Max possible score for this question
                                # = (test_cases * 2) + 2 (output) + 2 (efficiency)
                                q_max_score = (total * 2) + 2 + 2
                                total_max_possible_score += q_max_score
                                
                                # Accumulate breakdown scores
                                total_testcase_score += tc_marks
                                total_output_score += out_marks
                                total_efficiency_score += eff_marks
                                total_test_cases_passed += passed
                                total_test_cases += total
                                
                                CodeSubmission.objects.create(
                                    candidate=candidate_entry,
                                    question_type=q_type,
                                    question_id=qid,
                                    question_title=q_obj.title,
                                    code=payload['code'],
                                    language=payload['lang'],
                                    passed_test_cases=passed,
                                    total_test_cases=total,
                                    output_success=out_ok,
                                    execution_time_ms=exec_ms,
                                    time_limit_met=time_met,
                                    testcase_score=tc_marks,
                                    output_score=out_marks,
                                    efficiency_score=eff_marks,
                                    total_score=q_score
                                )
                            except model_cls.DoesNotExist:
                                logger.warning(f"{q_type.capitalize()} question {qid} not found")
                            except Exception as e:
                                logger.error(f"Error evaluating {q_type} question {qid}: {str(e)}")

                    evaluate_and_save(coding_subs, 'coding', CodingQuestion)
                    evaluate_and_save(dubbing_subs, 'dubbing', DubbingQuestion)
                finally:
                    shutil.rmtree(tmp_dir, ignore_errors=True)

                # Calculate percentage based on actual max possible score BEFORE saving
                actual_percentage = (score / total_max_possible_score * 100) if total_max_possible_score > 0 else 0

                candidate_entry.is_submitted = True
                candidate_entry.score = score
                candidate_entry.percentage = actual_percentage  # Save percentage
                candidate_entry.total_questions = total_max_possible_score  # Store max possible score for display
                candidate_entry.time_taken_seconds = time_taken_seconds
                candidate_entry.save(update_fields=['is_submitted', 'score', 'percentage', 'total_questions', 'time_taken_seconds'])
        except Exception as e:
            logger.error(f"Error updating candidate submission: {str(e)}")

        # Get counts for attended questions
        num_coding = len(coding_subs) if 'coding_subs' in locals() else 0
        num_dubbing = len(dubbing_subs) if 'dubbing_subs' in locals() else 0

        return JsonResponse({
            'success': True,
            'score': score,
            'total_questions': total_questions,
            'attended': answered_count + num_coding + num_dubbing if 'num_coding' in locals() else answered_count,
            'percentage': actual_percentage,
            'testcase_score': total_testcase_score,
            'output_score': total_output_score,
            'efficiency_score': total_efficiency_score,
            'test_cases_passed': total_test_cases_passed,
            'test_cases_total': total_test_cases,
            'max_score': total_max_possible_score
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
        # Get candidate_entry_id from query params if provided
        candidate_entry_id = request.GET.get('candidate_entry_id')
        
        # Optimize: Only fetch the fields we need
        round_obj = Round.objects.filter(
            event_id=event_id, 
            round_number=round_number
        ).first()
        
        if not round_obj:
            return JsonResponse({'started': False, 'error': 'Round not found'}, status=404)
        
        started = round_obj.is_started
        
        # If round has started and we have a candidate_entry_id, check if they should be redirected
        should_redirect = True
        if started and candidate_entry_id:
            try:
                candidate_entry = CandidateEntry.objects.get(id=candidate_entry_id)
                # Only redirect if they're still waiting (haven't exited)
                should_redirect = candidate_entry.is_waiting and not candidate_entry.is_submitted
            except CandidateEntry.DoesNotExist:
                should_redirect = False
        
        return JsonResponse({
            'started': started,
            'should_redirect': should_redirect
        })
    except Exception as e:
        logger.error(f"check_round_started error: {str(e)}")
        return JsonResponse({
            'started': False,
            'should_redirect': False,
            'error': str(e)
        }, status=500)


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
        
        # Only mark as not waiting if not already submitted
        # This ensures we remove them from waiting list in all phases before submission
        if candidate_entry.round and not candidate_entry.is_submitted:
            if not candidate_entry.round.is_started:
                candidate_entry.is_waiting = False
                candidate_entry.save(update_fields=['is_waiting'])
            else:
                candidate_entry.is_waiting = False
                candidate_entry.save(update_fields=['is_waiting'])
        
        return JsonResponse({'success': True, 'message': 'Candidate marked as exited', 'candidate_id': candidate_entry_id})
    except CandidateEntry.DoesNotExist:
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
        
        # Only reset waiting status if round hasn't started yet AND candidate hasn't exited
        # If is_waiting is already False, it means they exited - don't reset it
        if (candidate_entry.round and 
            not candidate_entry.round.is_started and 
            not candidate_entry.is_submitted and
            candidate_entry.is_waiting):  # Only reset if they were already waiting
            candidate_entry.last_active = current_time
            candidate_entry.save(update_fields=['last_active'])
        else:
            # Just update the heartbeat even if round has started
            candidate_entry.last_active = current_time
            candidate_entry.save(update_fields=['last_active'])
        
        return JsonResponse({'success': True, 'message': 'Waiting status initialized'})
    except CandidateEntry.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Candidate not found'}, status=404)
    except Exception as e:
        logger.error(f"init_waiting error: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
def check_connectivity(request):
    """Simple connectivity check endpoint"""
    return JsonResponse({'status': 'ok', 'timestamp': timezone.now().isoformat()})


@csrf_exempt
def run_code(request):
    """
    Execute candidate code locally using subprocess.
    If question_id is provided for a coding question, run against all stored test cases.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

    import subprocess, tempfile, os, shutil, re

    try:
        data = json.loads(request.body)
        language     = data.get('language', 'python').lower().strip()
        code         = data.get('code', '').strip()
        stdin        = data.get('stdin', '')
        question_id  = data.get('question_id')
        question_type = data.get('question_type', 'coding')

        if not code:
            return JsonResponse({'success': False, 'error': 'No code provided'}, status=400)

        TIMEOUT = 10

        # ── Helper: compile code once, return (exe_path, tmp_dir, error) ──
        def prepare_code(code, language, tmp_dir):
            if language == 'python':
                src = os.path.join(tmp_dir, 'solution.py')
                with open(src, 'w', encoding='utf-8') as f:
                    f.write(code)
                return ('python', [src], None)

            elif language == 'c':
                src = os.path.join(tmp_dir, 'solution.c')
                exe = os.path.join(tmp_dir, 'solution.exe')
                with open(src, 'w', encoding='utf-8') as f:
                    f.write(code)
                comp = subprocess.run(
                    ['gcc', src, '-o', exe, '-lm'],
                    capture_output=True, text=True, timeout=30, cwd=tmp_dir
                )
                if comp.returncode != 0:
                    return (None, None, comp.stderr)
                return ('exe', [exe], None)

            elif language == 'java':
                m = re.search(r'public\s+class\s+(\w+)', code)
                class_name = m.group(1) if m else 'Solution'
                src = os.path.join(tmp_dir, f'{class_name}.java')
                with open(src, 'w', encoding='utf-8') as f:
                    f.write(code)
                comp = subprocess.run(
                    ['javac', src],
                    capture_output=True, text=True, timeout=30, cwd=tmp_dir
                )
                if comp.returncode != 0:
                    return (None, None, comp.stderr)
                return ('java', ['-cp', tmp_dir, class_name], None)

            return (None, None, f'Unsupported language: {language}')

        # ── Helper: run compiled code with given stdin ──
        def execute(runner, cmd_args, stdin_data, tmp_dir):
            if runner == 'python':
                cmd = ['python'] + cmd_args
            elif runner == 'exe':
                cmd = cmd_args
            elif runner == 'java':
                cmd = ['java'] + cmd_args
            else:
                return '', 'Unknown runner', 1

            result = subprocess.run(
                cmd, input=stdin_data, capture_output=True, text=True,
                timeout=TIMEOUT, cwd=tmp_dir
            )
            return result.stdout, result.stderr, result.returncode

        # ── Fetch test cases if question_id is provided ──
        test_cases = []
        if question_id:
            if question_type == 'coding':
                try:
                    coding_q = CodingQuestion.objects.get(id=question_id)
                    test_cases = list(coding_q.test_cases.all())
                except CodingQuestion.DoesNotExist:
                    pass
            elif question_type == 'dubbing':
                try:
                    dubbing_q = DubbingQuestion.objects.get(id=question_id)
                    test_cases = list(dubbing_q.test_cases.all())
                except DubbingQuestion.DoesNotExist:
                    pass

        tmp_dir = tempfile.mkdtemp(prefix='quiz_run_')
        try:
            runner, cmd_args, compile_err = prepare_code(code, language, tmp_dir)
            if compile_err:
                return JsonResponse({
                    'success': False,
                    'output': compile_err,
                    'error_type': 'compile_error'
                })

            # Normalize manual stdin if provided
            if stdin:
                stdin = stdin.replace('\r\n', '\n').replace('\r', '\n')

            # ── Run against test cases ──
            if test_cases and not stdin:
                results = []
                passed = 0
                for tc in test_cases:
                    # Normalize test case input
                    clean_input = tc.input_data.replace('\r\n', '\n').replace('\r', '\n')
                    try:
                        stdout, stderr, rc = execute(runner, cmd_args, clean_input, tmp_dir)
                        actual = stdout.strip().replace('\r\n', '\n').replace('\r', '\n')
                        expected = tc.expected_output.strip().replace('\r\n', '\n').replace('\r', '\n')
                        
                        is_pass = (actual == expected and rc == 0)
                        if is_pass:
                            passed += 1
                        
                        results.append({
                            'order':    tc.order,
                            'passed':   is_pass,
                            'input':    tc.input_data[:200],
                            'expected': expected[:200],
                            'actual':   actual[:200] if rc == 0 else stderr[:200],
                        })
                    except subprocess.TimeoutExpired:
                        results.append({
                            'order':  tc.order,
                            'passed': False,
                            'input':  tc.input_data[:200],
                            'expected': tc.expected_output.strip()[:200],
                            'actual': 'Time Limit Exceeded',
                        })

                return JsonResponse({
                    'success': passed == len(test_cases),
                    'mode': 'test_cases',
                    'passed': passed,
                    'total': len(test_cases),
                    'results': results,
                })

            # ── Simple run (no test cases or dubbing) ──
            else:
                try:
                    stdout, stderr, rc = execute(runner, cmd_args, stdin, tmp_dir)
                except subprocess.TimeoutExpired:
                    return JsonResponse({
                        'success': False,
                        'output': f'⏱ Time Limit Exceeded ({TIMEOUT}s)',
                        'error_type': 'tle'
                    })

                return JsonResponse({
                    'success': rc == 0,
                    'mode': 'simple',
                    'output': stdout if stdout else stderr,
                    'exit_code': rc,
                })

        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid request data'}, status=400)
    except Exception as e:
        logger.error(f'run_code error: {e}')
        return JsonResponse({'success': False, 'error': str(e)}, status=500)



def mark_tab_switched(request, candidate_entry_id):
    """API endpoint to mark when candidate switches tabs"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        candidate_entry = CandidateEntry.objects.get(id=candidate_entry_id)
        candidate_entry.has_switched_tabs = True
        candidate_entry.save(update_fields=['has_switched_tabs'])
        return JsonResponse({'success': True, 'message': 'Tab switch recorded'})
    except CandidateEntry.DoesNotExist:
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
        ).prefetch_related('code_submissions').order_by('-is_submitted', 'entry_time') if round_obj.access_code else CandidateEntry.objects.none()
        
        # Create a list with candidate info including status
        current_time = timezone.now()
        threshold_90s = current_time - timedelta(seconds=90)
        threshold_30s = current_time - timedelta(seconds=30)
        
        candidates_data = []
        
        if round_obj.is_started:
            # After round starts: show ONLY candidates who actually started the quiz or submitted
            # Do NOT show candidates who exited the waiting room (quiz_started_at is NULL)
            
            # Candidates who submitted (is_submitted=True)
            submitted = all_candidates.filter(is_submitted=True)
            
            # Candidates currently taking test (quiz_started_at NOT NULL, is_submitted=False, active in last 90 seconds)
            actively_testing = all_candidates.filter(
                quiz_started_at__isnull=False,  # They actually started the quiz
                is_submitted=False,
                last_active__gte=threshold_90s
            )
            
            # Combine the two groups
            display_candidates = list(submitted) + list(actively_testing)
            
            for candidate in display_candidates:
                if candidate.is_submitted:
                    status = "Submitted"
                elif candidate.quiz_started_at and candidate.last_active >= threshold_90s:
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
        ).prefetch_related('code_submissions').order_by('-is_submitted', 'entry_time') if round_obj.access_code else CandidateEntry.objects.none()
        
        current_time = timezone.now()
        threshold_90s = current_time - timedelta(seconds=90)
        threshold_30s = current_time - timedelta(seconds=30)
        threshold_45s = current_time - timedelta(seconds=45)  # For waiting room timeout
        waiting_timeout = current_time - timedelta(seconds=45)  # Reduced from 60 to 45 seconds for faster detection
        
        candidates_data = []
        
        if round_obj.is_started:
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
            # After round starts: show only candidates who actually started the quiz or submitted
            # Do NOT show candidates who just exited the waiting room
            
            # Submitted candidates (always show)
            submitted = all_candidates.filter(is_submitted=True)
            
            # Actively testing candidates (must have actually started the quiz)
            # Only show if: quiz_started_at is NOT NULL and they have recent activity
            actively_testing = all_candidates.filter(
                quiz_started_at__isnull=False,  # They actually started the quiz
                is_submitted=False,
                last_active__gte=threshold_90s  # Still active in last 90 seconds
            )
            
            display_candidates = list(submitted) + list(actively_testing)
            
            for candidate in display_candidates:
                if candidate.is_submitted:
                    status = "Submitted"
                elif candidate.quiz_started_at and candidate.last_active >= threshold_90s:
                    status = "Giving Test"
                else:
                    status = "Left"
                
                time_display = ""
                if candidate.time_taken_seconds:
                    mins = candidate.time_taken_seconds // 60
                    secs = candidate.time_taken_seconds % 60
                    time_display = f"{mins}m {secs}s"
                
                # Fetch code submissions for this candidate
                code_subs = []
                for cs in candidate.code_submissions.all():
                    code_subs.append({
                        'type': cs.question_type,
                        'title': cs.question_title,
                        'passed': cs.passed_test_cases,
                        'total': cs.total_test_cases,
                        'tc_score': cs.testcase_score,
                        'out_score': cs.output_score,
                        'eff_score': cs.efficiency_score,
                        'total_score': cs.total_score,
                        'time_ms': round(cs.execution_time_ms, 2)
                    })

                candidates_data.append({
                    'id': candidate.id,
                    'name': candidate.candidate_name,
                    'is_submitted': candidate.is_submitted,
                    'status': status,
                    'score': candidate.score if candidate.score else 0,
                    'total_questions': candidate.total_questions if candidate.total_questions else 0,
                    'time_taken': time_display,
                    'has_switched_tabs': candidate.has_switched_tabs,
                    'code_submissions': code_subs
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
                marked_count = inactive_candidates.update(is_waiting=False)
            
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
                        status = "Inactive"  # Was waiting but timed out (no heartbeat for 45+s)
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
        
        
        response = JsonResponse({
            'success': True,
            'candidates': candidates_data
        })
        # Prevent caching to ensure real-time updates
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response
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
