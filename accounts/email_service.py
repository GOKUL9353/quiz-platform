"""
Email service module for sending quiz-related emails
"""
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
import logging

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
        
        # Send email
        email = EmailMultiAlternatives(
            subject=subject,
            body=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[candidate_email]
        )
        email.attach_alternative(html_message, "text/html")
        email.send()
        
        logger.info(f"Quiz completion email sent to {candidate_email}")
        return True
        
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


def send_round_owner_notification_with_pdf(owner_email, event_name, round_number, candidate_name, score, total_questions, pdf_buffer, pdf_filename):
    """
    Send notification email to round owner with candidate's score and PDF attachment
    
    Args:
        owner_email (str): Email of the round owner
        event_name (str): Name of the event
        round_number (int): Round number
        candidate_name (str): Name of the candidate
        score (int): Number of correct answers
        total_questions (int): Total number of questions
        pdf_buffer: BytesIO object containing the PDF
        pdf_filename (str): Name for the PDF file attachment
    
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        percentage = (score / total_questions * 100) if total_questions > 0 else 0
        
        subject = f'Quiz Submission Report - {event_name} Round {round_number} - {candidate_name}'
        
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
Quiz Submission Report

Event: {event_name}
Round: {round_number}
Candidate: {candidate_name}
Score: {score}/{total_questions} ({percentage:.1f}%)

Please see the attached PDF for detailed results.

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
        
        # Attach PDF
        pdf_buffer.seek(0)  # Reset buffer position to start
        email.attach(pdf_filename, pdf_buffer.read(), 'application/pdf')
        
        email.send()
        
        logger.info(f"Owner notification email with PDF sent to {owner_email}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending owner notification email with PDF to {owner_email}: {str(e)}")
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


def render_owner_notification_html(context):
    """Render HTML template for owner notification email"""
    percentage = context['percentage']
    html = f"""
    <html>
        <body style="font-family: 'Inter', Arial, sans-serif; color: #202124;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="text-align: center; margin-bottom: 30px;">
                    <h1 style="color: #1a73e8; margin: 0;">New Quiz Submission</h1>
                </div>
                
                <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
                    <p style="margin: 0;">A candidate has completed the quiz for <strong>{context['event_name']} - Round {context['round_number']}</strong></p>
                </div>
                
                <div style="background: #ffffff; border: 1px solid #dadce0; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
                    <h2 style="color: #1a73e8; margin-top: 0;">Submission Details</h2>
                    
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr style="border-bottom: 1px solid #e8eaed;">
                            <td style="padding: 10px 0; color: #5f6368;"><strong>Candidate Name:</strong></td>
                            <td style="padding: 10px 0; text-align: right; color: #202124;">{context['candidate_name']}</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #e8eaed;">
                            <td style="padding: 10px 0; color: #5f6368;"><strong>Event:</strong></td>
                            <td style="padding: 10px 0; text-align: right; color: #202124;">{context['event_name']}</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #e8eaed;">
                            <td style="padding: 10px 0; color: #5f6368;"><strong>Round:</strong></td>
                            <td style="padding: 10px 0; text-align: right; color: #202124;">{context['round_number']}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px 0; color: #5f6368;"><strong>Score:</strong></td>
                            <td style="padding: 10px 0; text-align: right; color: #202124;">{context['score']}/{context['total_questions']} ({percentage:.1f}%)</td>
                        </tr>
                    </table>
                </div>
                
                <div style="text-align: center; color: #5f6368; font-size: 12px;">
                    <p>You are receiving this email because you are the owner/coordinator of this round.</p>
                </div>
            </div>
        </body>
    </html>
    """
    return html
