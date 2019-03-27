from django.contrib.auth import get_user_model
from django.core.management import BaseCommand


User = get_user_model()


class Command(BaseCommand):
    help = 'Marks all users registration unfinished'

    def handle(self, *args, **options):
        for user in User.objects.all():
            user.has_finished_registration = False
            user.save()
        self.stdout.write(
            self.style.SUCCESS('All users registrations marked unfinished'))
