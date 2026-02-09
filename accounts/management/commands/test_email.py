"""
Django management command to test email configuration
Usage: python manage.py test_email your_email@example.com
"""
from django.core.management.base import BaseCommand, CommandError
from accounts.email_service import send_test_email


class Command(BaseCommand):
    help = 'Test email configuration by sending a test email'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'email',
            type=str,
            help='Email address to send test email to'
        )
    
    def handle(self, *args, **options):
        email = options['email']
        
        self.stdout.write(self.style.WARNING(f'Sending test email to {email}...'))
        
        try:
            success = send_test_email(email)
            if success:
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Test email sent successfully to {email}!')
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f'✗ Failed to send test email to {email}')
                )
        except Exception as e:
            raise CommandError(f'Error sending test email: {str(e)}')
