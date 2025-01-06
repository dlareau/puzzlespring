from django.core.management.base import BaseCommand, CommandError

from puzzlehunt.models import Hunt, Event, Submission, Team, User, PuzzleStatus, Hint, Puzzle

def random_user(team):
    # Return a random user from a team
    user = team.members.all().order_by("?").first()
    if user is None:
        return User.objects.first()
    return user

class Command(BaseCommand):
    help = "Makes events from other objects"

    def add_arguments(self, parser):
        parser.add_argument("hunt_ids", nargs="+", type=int)

    def handle(self, *args, **options):
        for hunt_id in options["hunt_ids"]:
            try:
                hunt = Hunt.objects.get(pk=hunt_id)
            except Hunt.DoesNotExist:
                raise CommandError('Hunt "%s" does not exist' % hunt_id)

            submissions = Submission.objects.filter(puzzle__hunt=hunt).select_related('puzzle', 'team').all()
            for sub in submissions:
                user = random_user(sub.team)
                Event.objects.create_event(
                    Event.EventType.PUZZLE_SUBMISSION,
                    sub,
                    user
                )

            statuses = PuzzleStatus.objects.filter(puzzle__hunt=hunt).select_related('puzzle', 'team').all()
            for status in statuses:
                user = random_user(status.team)
                if status.solve_time is not None:
                    Event.objects.create_event(
                        Event.EventType.PUZZLE_SOLVE,
                        status,
                        user
                    )
                if status.unlock_time is not None:
                    Event.objects.create_event(
                        Event.EventType.PUZZLE_UNLOCK,
                        status,
                        user
                    )

            hints = Hint.objects.filter(puzzle__hunt=hunt).select_related('puzzle', 'team').all()
            for hint in hints:
                user = random_user(hint.team)
                if hint.request_time is not None:
                    Event.objects.create_event(
                        Event.EventType.HINT_REQUEST,
                        hint,
                        user
                    )
                if hint.response_time is not None:
                    if hint.responder is not None:
                        user = hint.responder
                    Event.objects.create_event(
                        Event.EventType.HINT_RESPONSE,
                        hint,
                        user
                    )

            final_puzzle = hunt.puzzle_set.filter(type=Puzzle.PuzzleType.FINAL_PUZZLE).all()
            if len(final_puzzle) == 1:
                final_puzzle = final_puzzle[0]
                final_statuses = (PuzzleStatus.objects.filter(puzzle=final_puzzle, solve_time__isnull=False)
                                  .select_related('puzzle', 'team').all())
                for status in final_statuses:
                    user = random_user(status.team)
                    Event.objects.create_event(
                        Event.EventType.FINISH_HUNT,
                        status,
                        user
                    )

