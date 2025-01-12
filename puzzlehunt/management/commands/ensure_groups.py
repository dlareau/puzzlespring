from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.auth.management import create_permissions
from django.apps import apps


def add_perm(g, app, read_only, model):
    g.permissions.add(Permission.objects.get(content_type__app_label=app, codename=f'view_{model}'))
    if not read_only:
        g.permissions.add(Permission.objects.get(content_type__app_label=app, codename=f'add_{model}'))
        g.permissions.add(Permission.objects.get(content_type__app_label=app, codename=f'change_{model}'))
        g.permissions.add(Permission.objects.get(content_type__app_label=app, codename=f'delete_{model}'))


class Command(BaseCommand):
    help = 'Ensures all required groups and permissions exist'

    def handle(self, *args, **options):
        # First ensure all permissions exist
        for app_config in apps.get_app_configs():
            app_config.models_module = True
            create_permissions(app_config, verbosity=0)
            app_config.models_module = None

        # Create or get groups
        ro_puzzlehunt, _ = Group.objects.get_or_create(name="Read Only Puzzlehunt")
        rw_puzzlehunt, _ = Group.objects.get_or_create(name="Full Puzzlehunt")
        ro_auth, _ = Group.objects.get_or_create(name="Read Only Authentication")
        rw_auth, _ = Group.objects.get_or_create(name="Full Authentication")

        # Clear existing permissions to ensure clean state
        ro_puzzlehunt.permissions.clear()
        rw_puzzlehunt.permissions.clear()
        ro_auth.permissions.clear()
        rw_auth.permissions.clear()

        # Add permissions to Read Only Puzzlehunt
        add_perm(ro_puzzlehunt, "puzzlehunt", True, 'update')
        add_perm(ro_puzzlehunt, "puzzlehunt", True, 'event')
        add_perm(ro_puzzlehunt, "puzzlehunt", True, 'hint')
        add_perm(ro_puzzlehunt, "puzzlehunt", True, 'hunt')
        add_perm(ro_puzzlehunt, "puzzlehunt", True, 'huntfile')
        add_perm(ro_puzzlehunt, "puzzlehunt", True, 'prepuzzle')
        add_perm(ro_puzzlehunt, "puzzlehunt", True, 'prepuzzlefile')
        add_perm(ro_puzzlehunt, "puzzlehunt", True, 'puzzle')
        add_perm(ro_puzzlehunt, "puzzlehunt", True, 'puzzlefile')
        add_perm(ro_puzzlehunt, "puzzlehunt", True, 'puzzlestatus')
        add_perm(ro_puzzlehunt, "puzzlehunt", True, 'response')
        add_perm(ro_puzzlehunt, "puzzlehunt", True, 'solutionfile')
        add_perm(ro_puzzlehunt, "puzzlehunt", True, 'submission')
        add_perm(ro_puzzlehunt, "puzzlehunt", True, 'team')
        add_perm(ro_puzzlehunt, "puzzlehunt", True, 'flatpageproxyobject')
        add_perm(ro_puzzlehunt, "puzzlehunt", True, 'displayonlyhunt')
        add_perm(ro_puzzlehunt, "constance", True, 'constance')
        add_perm(ro_puzzlehunt, "flatpages", True, 'flatpage')
        ro_puzzlehunt.permissions.add(Permission.objects.get(content_type__app_label="constance", codename="view_config"))

        # Add permissions to Full Puzzlehunt
        add_perm(rw_puzzlehunt, "puzzlehunt", False, 'update')
        add_perm(rw_puzzlehunt, "puzzlehunt", False, 'event')
        add_perm(rw_puzzlehunt, "puzzlehunt", False, 'hint')
        add_perm(rw_puzzlehunt, "puzzlehunt", False, 'hunt')
        add_perm(rw_puzzlehunt, "puzzlehunt", False, 'huntfile')
        add_perm(rw_puzzlehunt, "puzzlehunt", False, 'prepuzzle')
        add_perm(rw_puzzlehunt, "puzzlehunt", False, 'prepuzzlefile')
        add_perm(rw_puzzlehunt, "puzzlehunt", False, 'puzzle')
        add_perm(rw_puzzlehunt, "puzzlehunt", False, 'puzzlefile')
        add_perm(rw_puzzlehunt, "puzzlehunt", False, 'puzzlestatus')
        add_perm(rw_puzzlehunt, "puzzlehunt", False, 'response')
        add_perm(rw_puzzlehunt, "puzzlehunt", False, 'solutionfile')
        add_perm(rw_puzzlehunt, "puzzlehunt", False, 'submission')
        add_perm(rw_puzzlehunt, "puzzlehunt", False, 'team')
        add_perm(rw_puzzlehunt, "puzzlehunt", False, 'flatpageproxyobject')
        add_perm(rw_puzzlehunt, "puzzlehunt", False, 'displayonlyhunt')
        add_perm(rw_puzzlehunt, "constance", False, 'constance')
        add_perm(rw_puzzlehunt, "flatpages", False, 'flatpage')
        rw_puzzlehunt.permissions.add(Permission.objects.get(content_type__app_label="constance", codename="view_config"))
        rw_puzzlehunt.permissions.add(Permission.objects.get(content_type__app_label="constance", codename="change_config"))

        # Add permissions to Read Only Authentication
        add_perm(ro_auth, "puzzlehunt", True, 'user')
        add_perm(ro_auth, "socialaccount", True, 'socialaccount')
        add_perm(ro_auth, "account", True, 'emailaddress')
        add_perm(ro_auth, "puzzlehunt", True, 'notificationplatform')
        add_perm(ro_auth, "puzzlehunt", True, 'notificationsubscription')
        

        # Add permissions to Full Authentication
        add_perm(rw_auth, "puzzlehunt", False, 'user')
        add_perm(rw_auth, "socialaccount", False, 'socialaccount')
        add_perm(rw_auth, "account", False, 'emailaddress')
        add_perm(rw_auth, "puzzlehunt", False, 'notificationplatform')
        add_perm(rw_auth, "puzzlehunt", False, 'notificationsubscription')
    
        self.stdout.write(self.style.SUCCESS('Successfully ensured groups and permissions')) 