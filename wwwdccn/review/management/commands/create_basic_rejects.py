from django.core.management.base import BaseCommand, CommandError

from conferences.models import Conference
from review.models import ReviewDecisionType

REJECT_DESCRIPTIONS = [
    'Rejected after review',
    'Rejected due to missing review manuscript',
    'Rejected due to missing title, abstract or authors',
    'Rejected due to conference rules violation',
]


class Command(BaseCommand):
    help = 'Create four REJECT ReviewDecisionType model instances: ' + \
        '; '.join(f'({i+1}) {s}' for i, s in enumerate(REJECT_DESCRIPTIONS))

    def add_arguments(self, parser):
        parser.add_argument('-f', '--fake', action='store_true',
                            help='Do not write changes to the DB')
        parser.add_argument('-c', '--conference', type=int,
                            help='Conference ID')

    def handle(self, *args, **kwargs):
        fake = kwargs['fake']
        verbosity = kwargs['verbosity']

        if fake:
            self.stdout.write(self.style.NOTICE('* Started in fake mode'))

        conference_id = kwargs['conference']
        try:
            conference = Conference.objects.get(id=conference_id)
        except Conference.DoesNotExist:
            self.stdout.write(self.style.ERROR(
                f'! conference with ID={conference_id} not found'))
            return

        num_found, num_created = 0, 0
        for description in REJECT_DESCRIPTIONS:
            created = False
            dt = None
            try:
                dt = ReviewDecisionType.objects.get(
                    description=description)
                num_found += 1
                dt.conference = conference
                dt.save()
            except ReviewDecisionType.DoesNotExist:
                if not fake:
                    dt = ReviewDecisionType.objects.create(
                        description=description,
                        decision=ReviewDecisionType.REJECT,
                        conference=conference,
                    )
                    created = True
                num_created += 1
            dt_id = str(dt.id) if dt else '<not defined>'
            if verbosity > 1:
                prefix = 'created' if created else 'found'
                self.stdout.write(self.style.SUCCESS(
                    f'+ {prefix} ReviewDecisionType {dt_id} with description '
                    f'"{description}"'))
            if dt and dt.decision != ReviewDecisionType.REJECT:
                if not fake:
                    dt.decision = ReviewDecisionType.REJECT
                    dt.save()
                if verbosity > 1:
                    self.stdout.write(self.style.SUCCESS(
                        f'> updated decision to REJECT for {dt_id}'))

        self.stdout.write(self.style.SUCCESS(
            f'= finished: created {"(faked)" if fake else ""} {num_created} '
            f'and found {num_found} existing review decisions'
        ))
