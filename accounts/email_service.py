"""
Email service module for sending quiz-related emails
Optimized for production on Render with proper error logging and timeout handling
"""
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
import logging
import socket
import smtplib
import requests

logger = logging.getLogger(__name__)


def send_quiz_completion_email(candidate_name, candidate_email, event_name, round_number, score, total_questions, percentage):
    """
    Send email to candidate after quiz completion with score details
    
    Args:
        candidate_name (str): Name of the candidate
        candidate_email (str): Email address of the candidate
        event_name (str): Name of the event
        round_number (int): Round number
        score (int): Number of correct answers
        total_questions (int): Total number of questions
        percentage (float): Percentage score
    
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        subject = f'Quiz Completion Report - {event_name} Round {round_number}'
        
        # Prepare context for HTML email
        context = {
            'candidate_name': candidate_name,
            'event_name': event_name,
            'round_number': round_number,
            'score': score,
            'total_questions': total_questions,
            'percentage': percentage,
            'passed': percentage >= 50  # Pass if 50% or more
        }
        
        # Create email content
        html_message = render_quiz_completion_html(context)
        plain_message = f"""
Hello {candidate_name},

Thank you for completing the {event_name} - Round {round_number} quiz.

Your Score: {score}/{total_questions} ({percentage}%)

We appreciate your participation!

Best regards,
Quiz Platform Team
        """
        
        # Send email using Brevo
        return send_email_with_brevo(candidate_email, subject, html_message, plain_message)
        
    except Exception as e:
        logger.error(f"Error sending quiz completion email to {candidate_email}: {str(e)}")
        return False


def send_round_owner_notification_email(owner_email, event_name, round_number, candidate_name, score, total_questions):
    """
    Send notification email to round owner with candidate's score
    
    Args:
        owner_email (str): Email of the round owner
        event_name (str): Name of the event
        round_number (int): Round number
        candidate_name (str): Name of the candidate
        score (int): Number of correct answers
        total_questions (int): Total number of questions
    
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        percentage = (score / total_questions * 100) if total_questions > 0 else 0
        
        subject = f'New Quiz Submission - {event_name} Round {round_number}'
        
        context = {
            'owner_email': owner_email,
            'event_name': event_name,
            'round_number': round_number,
            'candidate_name': candidate_name,
            'score': score,
            'total_questions': total_questions,
            'percentage': percentage
        }
        
        html_message = render_owner_notification_html(context)
        plain_message = f"""
New Quiz Submission Received

Event: {event_name}
Round: {round_number}
Candidate: {candidate_name}
Score: {score}/{total_questions} ({percentage:.1f}%)

Regards,
Quiz Platform
        """
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[owner_email]
        )
        email.attach_alternative(html_message, "text/html")
        email.send()
        
        logger.info(f"Owner notification email sent to {owner_email}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending owner notification email to {owner_email}: {str(e)}")
        return False


def send_quiz_results_email(owner_email, event_name, round_number, candidate_name, score, total_questions, time_taken_seconds):
    """
    Send quiz results email to round owner with candidate performance in table format
    
    Args:
        owner_email (str): Email of the round owner
        event_name (str): Name of the event
        round_number (int): Round number
        candidate_name (str): Name of the candidate
        score (int): Number of correct answers
        total_questions (int): Total number of questions
        time_taken_seconds (int): Time taken to complete quiz in seconds
    
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        if not owner_email:
            logger.warning('Owner email is empty, skipping notification')
            return False
        
        percentage = (score / total_questions * 100) if total_questions > 0 else 0
        
        # Format time
        time_minutes = time_taken_seconds // 60
        time_seconds = time_taken_seconds % 60
        time_taken_str = f"{int(time_minutes)}m {int(time_seconds)}s"
        
        subject = f'Quiz Results - {event_name} Round {round_number} - {candidate_name}'
        
        context = {
            'owner_email': owner_email,
            'event_name': event_name,
            'round_number': round_number,
            'candidate_name': candidate_name,
            'score': score,
            'total_questions': total_questions,
            'percentage': percentage,
            'time_taken': time_taken_str
        }
        
        html_message = render_quiz_results_html(context)
        plain_message = f"""
Quiz Results

Candidate: {candidate_name}
Event: {event_name}
Round: {round_number}
Score: {score}/{total_questions}
Percentage: {percentage:.1f}%
Time Taken: {time_taken_str}

Regards,
Quiz Platform
        """
        
        logger.info(f"Preparing results email to {owner_email}")
        
        # Send email using Brevo
        return send_email_with_brevo(owner_email, subject, html_message, plain_message)
        
    except Exception as e:
        logger.error(f"Error sending quiz results email to {owner_email}: {str(e)}")
        return False


def send_test_email(recipient_email):
    """
    Send a test email to verify email configuration
    
    Args:
        recipient_email (str): Email address to send test email to
    
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        subject = 'Test Email - Quiz Platform'
        message = 'This is a test email from the Quiz Platform. If you received this, the email configuration is working correctly!'
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [recipient_email],
            fail_silently=False,
        )
        
        logger.info(f"Test email sent to {recipient_email}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending test email to {recipient_email}: {str(e)}")
        return False


def send_email_with_brevo(to_email, subject, html_content, plain_content):
    """
    Send an email using Brevo API.

    Args:
        to_email (str): Recipient email address.
        subject (str): Email subject.
        html_content (str): HTML content of the email.
        plain_content (str): Plain text content of the email.

    Returns:
        bool: True if email sent successfully, False otherwise.
    """
    url = "https://api.brevo.com/v3/smtp/email"
    headers = {
        "accept": "application/json",
        "api-key": settings.BREVO_API_KEY,
        "content-type": "application/json"
    }
    payload = {
        "sender": {"email": settings.DEFAULT_FROM_EMAIL},
        "to": [{"email": to_email}],
        "subject": subject,
        "htmlContent": html_content,
        "textContent": plain_content
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        try:
            response.raise_for_status()
            logger.info(f"Email sent successfully to {to_email}. Response: {response.json()}")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send email to {to_email}: {e}. Response: {response.text}")
            return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Error sending email to {to_email}: {str(e)}")
        return False


def render_quiz_completion_html(context):
    """Render HTML template for quiz completion email"""
    html = f"""
    <html>
        <body style="font-family: 'Inter', Arial, sans-serif; color: #202124;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="text-align: center; margin-bottom: 30px;">
                    <h1 style="color: #1a73e8; margin: 0;">Quiz Completed!</h1>
                </div>
                
                <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
                    <p style="margin: 0 0 10px 0;"><strong>Hello {context['candidate_name']},</strong></p>
                    <p style="margin: 0;">Thank you for completing the <strong>{context['event_name']}</strong> assessment!</p>
                </div>
                
                <div style="background: #ffffff; border: 1px solid #dadce0; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
                    <h2 style="color: #1a73e8; margin-top: 0;">Your Results</h2>
                    
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 15px;">
                        <div style="background: #e8f0fe; padding: 15px; border-radius: 4px; text-align: center;">
                            <div style="font-size: 24px; font-weight: 700; color: #1a73e8;">{context['score']}/{context['total_questions']}</div>
                            <div style="font-size: 12px; color: #5f6368; text-transform: uppercase;">Score</div>
                        </div>
                        <div style="background: #e8f0fe; padding: 15px; border-radius: 4px; text-align: center;">
                            <div style="font-size: 24px; font-weight: 700; color: #1a73e8;">{context['percentage']:.1f}%</div>
                            <div style="font-size: 12px; color: #5f6368; text-transform: uppercase;">Percentage</div>
                        </div>
                    </div>
                    
                    <div style="padding: 10px; border-radius: 4px; background: {'#e6f4ea' if context['passed'] else '#fce8e6'}; color: {'#1e8e3e' if context['passed'] else '#d93025'}; text-align: center; font-weight: 500;">
                        {'✓ PASSED' if context['passed'] else '✗ FAILED'}
                    </div>
                </div>
                
                <div style="text-align: center; color: #5f6368; font-size: 12px;">
                    <p>For any queries, please contact the administrator.</p>
                    <p>Round {context['round_number']} - {context['event_name']}</p>
                </div>
            </div>
        </body>
    </html>
    """
    return html


def render_quiz_results_html(context):
    """Render HTML template for quiz results email with table format"""
    html = f"""
    <html>
        <body style="font-family: 'Inter', Arial, sans-serif; color: #202124; background: #f5f5f5;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <!-- Header -->
                <div style="text-align: center; margin-bottom: 30px;">
                    <h1 style="color: #2563EB; margin: 0; font-size: 28px;">Quiz Results</h1>
                    <p style="color: #5f6368; margin: 5px 0 0 0;">{context['event_name']} - Round {context['round_number']}</p>
                </div>
                
                <!-- Results Table -->
                <div style="background: #ffffff; border-radius: 8px; padding: 20px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr style="border-bottom: 2px solid #e8eaed;">
                            <td style="padding: 12px 0; color: #5f6368; font-weight: 500;">Candidate Name</td>
                            <td style="padding: 12px 0; text-align: right; color: #202124; font-weight: 600; font-size: 16px;">{context['candidate_name']}</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #e8eaed;">
                            <td style="padding: 12px 0; color: #5f6368; font-weight: 500;">Event</td>
                            <td style="padding: 12px 0; text-align: right; color: #202124;">{context['event_name']}</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #e8eaed;">
                            <td style="padding: 12px 0; color: #5f6368; font-weight: 500;">Round Number</td>
                            <td style="padding: 12px 0; text-align: right; color: #202124;">Round {context['round_number']}</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #e8eaed;">
                            <td style="padding: 12px 0; color: #5f6368; font-weight: 500;">Total Questions</td>
                            <td style="padding: 12px 0; text-align: right; color: #202124;">{context['total_questions']}</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #e8eaed;">
                            <td style="padding: 12px 0; color: #5f6368; font-weight: 500;">Correct Answers</td>
                            <td style="padding: 12px 0; text-align: right; color: #10B981; font-weight: 600; font-size: 16px;">{context['score']}/{context['total_questions']}</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #e8eaed;">
                            <td style="padding: 12px 0; color: #5f6368; font-weight: 500;">Percentage</td>
                            <td style="padding: 12px 0; text-align: right; color: #2563EB; font-weight: 600; font-size: 16px;">{context['percentage']:.1f}%</td>
                        </tr>
                        <tr>
                            <td style="padding: 12px 0; color: #5f6368; font-weight: 500;">Time Taken</td>
                            <td style="padding: 12px 0; text-align: right; color: #202124; font-weight: 600;">{context['time_taken']}</td>
                        </tr>
                    </table>
                </div>
                
                <!-- Status Badge -->
                <div style="text-align: center; margin-bottom: 20px;">
                    <div style="padding: 12px 20px; border-radius: 6px; display: inline-block; font-weight: 600; background: {'#E6F4EA' if context['percentage'] >= 50 else '#FCE8E6'}; color: {'#1E8E3E' if context['percentage'] >= 50 else '#D93025'};">
                        {'✓ PASSED' if context['percentage'] >= 50 else '✗ NEEDS IMPROVEMENT'}
                    </div>
                </div>
                
                <!-- Footer -->
                <div style="text-align: center; color: #5f6368; font-size: 12px; border-top: 1px solid #e8eaed; padding-top: 20px;">
                    <p style="margin: 0;">This is an automated notification from the Quiz Platform.</p>
                    <p style="margin: 5px 0 0 0;">You are receiving this because you are the coordinator of this round.</p>
                </div>
            </div>
        </body>
    </html>
    """
    return html
