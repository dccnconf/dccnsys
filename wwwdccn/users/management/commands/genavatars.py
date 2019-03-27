from django.core.management import BaseCommand

from users.models import generate_avatar, Profile


class Command(BaseCommand):
    help = 'Generate new avatars for all users'

    def handle(self, *args, **options):
        for profile in Profile.objects.all():
            profile.avatar_version += 1
            profile.save()
            profile.avatar = generate_avatar(profile)
            profile.save()
        self.stdout.write(
            self.style.SUCCESS('Generated new avatars for all user profiles')
        )
