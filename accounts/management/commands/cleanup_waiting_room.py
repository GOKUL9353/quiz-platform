"""
Management command to clean up inactive waiting room candidates.
Run this periodically (via cron or Celery) to mark candidates as inactive
if they haven't sent a heartbeat in a specified time.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Q
from datetime import timedelta
from accounts.models import CandidateEntry, Round
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Clean up inactive waiting room candidates (no heartbeat for X seconds)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--inactivity-timeout',
            type=int,
            default=60,
            help='Mark as inactive if no heartbeat for this many seconds (default: 60)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be cleaned up without actually making changes',
        )

    def handle(self, *args, **options):
        inactivity_timeout = options['inactivity_timeout']
        dry_run = options['dry_run']
        
        current_time = timezone.now()
        timeout_threshold = current_time - timedelta(seconds=inactivity_timeout)
        
        # Find inactive waiting candidates
        # Only cleanup candidates whose rounds haven't started yet
        inactive_candidates = CandidateEntry.objects.filter(
            Q(is_waiting=True) &  # Still marked as waiting
            Q(last_active__lt=timeout_threshold) &  # No heartbeat for X seconds
            Q(round__is_started=False) &  # Round hasn't started
            Q(is_submitted=False)  # Haven't submitted yet
        ).select_related('round', 'event')
        
        count = inactive_candidates.count()
        
        if count == 0:
            self.stdout.write(
                self.style.SUCCESS('✓ No inactive candidates to clean up')
            )
            return
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(f'DRY RUN: Would mark {count} candidates as inactive:')
            )
            for candidate in inactive_candidates[:10]:  # Show first 10
                last_active_ago = (current_time - candidate.last_active).total_seconds()
                self.stdout.write(
                    f'  - {candidate.candidate_name} (Round {candidate.round.round_number}, '
                    f'inactive for {int(last_active_ago)}s)'
                )
            if count > 10:
                self.stdout.write(f'  ... and {count - 10} more')
        else:
            # Actually mark them as not waiting
            updated = inactive_candidates.update(is_waiting=False)
            self.stdout.write(
                self.style.SUCCESS(f'✓ Marked {updated} inactive candidates as not waiting')
            )
