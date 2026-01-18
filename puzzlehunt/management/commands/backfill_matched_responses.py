import re
from django.core.management.base import BaseCommand, CommandError

from puzzlehunt.models import Hunt, Puzzle, Submission, Response


class Command(BaseCommand):
    help = "Backfill matched_response FK on Submission objects by re-evaluating against current Response regexes"

    def add_arguments(self, parser):
        parser.add_argument(
            "--hunt",
            type=int,
            help="Only process submissions for the specified hunt ID"
        )
        parser.add_argument(
            "--puzzle",
            type=int,
            help="Only process submissions for the specified puzzle ID"
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be updated without making changes"
        )

    def handle(self, *args, **options):
        hunt_id = options.get("hunt")
        puzzle_id = options.get("puzzle")
        dry_run = options.get("dry_run")

        # Build queryset based on filters
        submissions = Submission.objects.select_related('puzzle')

        if puzzle_id:
            try:
                puzzle = Puzzle.objects.get(pk=puzzle_id)
            except Puzzle.DoesNotExist:
                raise CommandError(f'Puzzle "{puzzle_id}" does not exist')
            submissions = submissions.filter(puzzle=puzzle)
            self.stdout.write(f"Filtering to puzzle: {puzzle.name}")
        elif hunt_id:
            try:
                hunt = Hunt.objects.get(pk=hunt_id)
            except Hunt.DoesNotExist:
                raise CommandError(f'Hunt "{hunt_id}" does not exist')
            submissions = submissions.filter(puzzle__hunt=hunt)
            self.stdout.write(f"Filtering to hunt: {hunt.name}")

        total_count = submissions.count()
        self.stdout.write(f"Processing {total_count} submissions...")

        # Pre-fetch all responses grouped by puzzle to avoid N+1 queries
        if puzzle_id:
            puzzle_ids = [puzzle_id]
        elif hunt_id:
            puzzle_ids = list(Puzzle.objects.filter(hunt_id=hunt_id).values_list('id', flat=True))
        else:
            puzzle_ids = list(submissions.values_list('puzzle_id', flat=True).distinct())

        responses_by_puzzle = {}
        for pid in puzzle_ids:
            responses_by_puzzle[pid] = list(Response.objects.filter(puzzle_id=pid))

        updated_count = 0
        matched_count = 0

        for submission in submissions.iterator():
            responses = responses_by_puzzle.get(submission.puzzle_id, [])
            matched_response = None

            for resp in responses:
                if re.match(resp.regex, submission.submission_text, re.IGNORECASE):
                    matched_response = resp
                    break

            # Only update if the matched_response changed
            if submission.matched_response_id != (matched_response.id if matched_response else None):
                updated_count += 1
                if matched_response:
                    matched_count += 1

                if not dry_run:
                    submission.matched_response = matched_response
                    submission.save(update_fields=['matched_response'])

        if dry_run:
            self.stdout.write(self.style.WARNING(
                f"DRY RUN: Would update {updated_count} submissions "
                f"({matched_count} with matches, {updated_count - matched_count} cleared)"
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"Updated {updated_count} submissions "
                f"({matched_count} with matches, {updated_count - matched_count} cleared)"
            ))
