import io
import zipfile
import json
from pathlib import Path
from django.core import serializers
from django.db import transaction
from django.core.exceptions import ValidationError

from django.http import Http404
from django.shortcuts import get_object_or_404

from puzzlehunt import models
from django.core.files import File
from django_eventstream.channelmanager import DefaultChannelManager
from .models import PuzzleFile, SolutionFile, HuntFile, PrepuzzleFile, Puzzle, Hunt, Prepuzzle, Team, TeamRankingRule, \
    CannedHint, Response, Hint, Update, PuzzleStatus, Submission, User


class PuzzlehuntChannelManager(DefaultChannelManager):
    def can_read_channel(self, user, channel):
        # require auth for all channels
        if user is None:
            return False

        if channel == "staff" and user.is_staff:
            return True

        if channel.startswith('team'):
            try:
                team = models.Team.objects.get(pk=channel.split("-", 1)[1])
            except models.Team.DoesNotExist:
                return False
            if user in team.members.all():
                return True

        # Default access is false
        return False


def get_media_file_model(object_type):
    object_type_map = {"puzzle": PuzzleFile, "solution": SolutionFile, "hunt": HuntFile, "prepuzzle": PrepuzzleFile}
    file_object = object_type_map.get(object_type, None)
    if file_object is None:
        raise Http404("Invalid file type")
    return file_object


def get_media_file_parent_model(object_type):
    object_type_map = {"puzzle": Puzzle, "solution": Puzzle, "hunt": Hunt, "prepuzzle": Prepuzzle}
    file_object = object_type_map.get(object_type, None)
    if file_object is None:
        raise Http404("Invalid file type")
    return file_object


def get_media_file_model_from_object(parent_object, is_solution_file):
    match type(parent_object):
        case models.Puzzle:
            return models.SolutionFile if is_solution_file else models.PuzzleFile
        case models.Hunt:
            return HuntFile
        case models.Prepuzzle:
            return PrepuzzleFile
        case _:
            raise Http404("Invalid parent object type")


def create_media_files(parent_object, file, is_solution_file=False):
    if file is None:
        return "No file!"
    media_file_model = get_media_file_model_from_object(parent_object, is_solution_file)

    file_type = file.content_type
    if file_type == "application/zip" or file_type == "application/x-zip-compressed":
        with zipfile.ZipFile(file, 'r') as zip_ref:
            files = zip_ref.namelist()
            for file_name in files:
                if file_name.startswith("__MACOSX/") or zipfile.Path(root=zip_ref, at=file_name).is_dir():
                    continue
                current_file = media_file_model.objects.filter(
                    file=f"{media_file_model.save_path}/{parent_object.id}/files/{file_name}").all()
                current_file.delete()

                with zip_ref.open(file_name) as new_file:
                    with io.BytesIO() as buf:
                        buf.write(new_file.read())
                        buf.seek(0)
                        django_file = File(buf, file_name)
                        media_file_model.objects.create(file=django_file, parent=parent_object)
    else:
        media_file_model.objects.create(file=file, parent=parent_object)


class HuntConverter:
    regex = '[0-9]+|current'

    def to_python(self, value):
        if value == "current":
            return Hunt.objects.get(is_current_hunt=True)
        else:
            return get_object_or_404(Hunt, id=int(value))

    def to_url(self, value):
        if value == "current":
            return "current"
        else:
            return '%d' % value


def create_hunt_export_zip(hunt, zip_path, include_activity=False):
    """
    Creates a hunt export zip file with all relevant hunt data and files.
    
    Args:
        hunt (Hunt): The hunt to export
        zip_path (str|Path): Path where the zip file should be created
        include_activity (bool): Whether to include activity data like hints and submissions
    """
    zip_path = Path(zip_path)
    
    # First, collect all file references that need special handling
    file_references = {
        'hunt': {
            'css_file': hunt.css_file.natural_key() if hunt.css_file else None,
        }
    }

    # Collect puzzle file references
    puzzle_refs = {}
    for puzzle in hunt.puzzle_set.all():
        puzzle_refs[puzzle.id] = {
            'main_file': puzzle.main_file.natural_key() if puzzle.main_file else None,
            'main_solution_file': puzzle.main_solution_file.natural_key() if puzzle.main_solution_file else None
        }
    file_references['puzzles'] = puzzle_refs

    # Collect prepuzzle file reference - no need for ID since it's a one-to-one relationship
    if hasattr(hunt, 'prepuzzle'):
        file_references['prepuzzle'] = {
            'main_file': hunt.prepuzzle.main_file.natural_key() if hunt.prepuzzle.main_file else None
        }

    # Clear file references before serialization
    with transaction.atomic():
        # Temporarily clear hunt file references
        old_css = hunt.css_file
        hunt.css_file = None
        hunt.save()

        # Temporarily clear puzzle file references
        puzzle_old_files = {}
        for puzzle in hunt.puzzle_set.all():
            puzzle_old_files[puzzle.id] = (puzzle.main_file, puzzle.main_solution_file)
            puzzle.main_file = None
            puzzle.main_solution_file = None
            puzzle.save()

        # Temporarily clear prepuzzle file references
        prepuzzle_old_file = None
        if hasattr(hunt, 'prepuzzle'):
            prepuzzle_old_file = hunt.prepuzzle.main_file
            hunt.prepuzzle.main_file = None
            hunt.prepuzzle.save()

        with zipfile.ZipFile(zip_path, 'w') as zip_file:
            # Export file references
            zip_file.writestr('file_references.json', json.dumps(file_references, indent=2))

            # Export model data
            models_to_export = {
                'hunt.json': Hunt.objects.filter(pk=hunt.pk),
                'ranking_rules.json': TeamRankingRule.objects.filter(hunt=hunt),
                'puzzles.json': Puzzle.objects.filter(hunt=hunt),
                'puzzle_files.json': PuzzleFile.objects.filter(parent__hunt=hunt).select_related('parent'),
                'solution_files.json': SolutionFile.objects.filter(parent__hunt=hunt).select_related('parent'),
                'hunt_files.json': HuntFile.objects.filter(parent=hunt).select_related('parent'),
                'prepuzzle_files.json': PrepuzzleFile.objects.filter(parent__hunt=hunt).select_related('parent'),
                'canned_hints.json': CannedHint.objects.filter(puzzle__hunt=hunt).select_related('puzzle'),
                'responses.json': Response.objects.filter(puzzle__hunt=hunt).select_related('puzzle'),
                'prepuzzles.json': Prepuzzle.objects.filter(hunt=hunt),
            }

            if include_activity:
                activity_models = {
                    'teams.json': Team.objects.filter(hunt=hunt).select_related('hunt'),
                    'hints.json': Hint.objects.filter(puzzle__hunt=hunt).select_related('puzzle', 'team', 'team__hunt'),
                    'updates.json': Update.objects.filter(hunt=hunt).select_related('hunt', 'puzzle'),
                    'puzzle_statuses.json': PuzzleStatus.objects.filter(puzzle__hunt=hunt).select_related('puzzle', 'team', 'team__hunt'),
                    'submissions.json': Submission.objects.filter(puzzle__hunt=hunt).select_related('puzzle', 'team', 'team__hunt', 'puzzle__hunt'),
                }
                models_to_export.update(activity_models)

            # Export model data in chunks to avoid memory issues
            for filename, queryset in models_to_export.items():
                # Use iterator() to avoid loading entire queryset into memory
                serialized_chunks = []
                for chunk in queryset.iterator(chunk_size=100):
                    chunk_data = serializers.serialize('json', [chunk],
                        use_natural_foreign_keys=True,
                        use_natural_primary_keys=True,
                        indent=2
                    )
                    # Remove the outer list brackets from the chunk
                    chunk_data = chunk_data.strip()[1:-1].strip()
                    if chunk_data:  # Only add non-empty chunks
                        serialized_chunks.append(chunk_data)
                
                # Combine all chunks into a single JSON array
                combined_data = "[\n" + ",\n".join(serialized_chunks) + "\n]"
                zip_file.writestr(filename, combined_data)

            # Export template and info page files
            if hunt.template_file:
                zip_file.write(hunt.template_file.path, 'files/template.html')
            if hunt.info_page_file:
                zip_file.write(hunt.info_page_file.path, 'files/info_page.html')
            
            # Export hunt files
            for file in hunt.files.all():
                zip_file.write(file.file.path, f'files/hunt/{file.relative_name}')
            
            # Export puzzle files
            for puzzle in hunt.puzzle_set.all():
                for file in puzzle.files.all():
                    zip_file.write(file.file.path, f'files/puzzle/{puzzle.id}/{file.relative_name}')
                for file in puzzle.solution_files.all():
                    zip_file.write(file.file.path, f'files/solution/{puzzle.id}/{file.relative_name}')
            
            # Export prepuzzle files
            if hasattr(hunt, 'prepuzzle'):
                for file in hunt.prepuzzle.files.all():
                    zip_file.write(file.file.path, f'files/prepuzzle/{file.relative_name}')

        # Restore file references
        hunt.css_file = old_css
        hunt.save()

        for puzzle in hunt.puzzle_set.all():
            main_file, main_solution_file = puzzle_old_files[puzzle.id]
            puzzle.main_file = main_file
            puzzle.main_solution_file = main_solution_file
            puzzle.save()

        if hasattr(hunt, 'prepuzzle'):
            hunt.prepuzzle.main_file = prepuzzle_old_file
            hunt.prepuzzle.save()


def validate_hunt_zip(zip_path: str | Path, include_activity: bool = False) -> None:
    """
    Validates a hunt zip file created by create_hunt_export_zip.
    
    Args:
        zip_path (str|Path): Path to the zip file containing the hunt data
        include_activity (bool): Whether to validate activity data (teams, hints, etc.)
    
    Raises:
        ValidationError: If the zip file is invalid or missing required data
    """
    zip_path = Path(zip_path)
    if not zip_path.exists():
        raise ValidationError("Zip file does not exist")

    required_files = {
        'file_references.json',
        'hunt.json',
        'ranking_rules.json',
        'puzzles.json',
        'puzzle_files.json',
        'solution_files.json',
        'hunt_files.json',
        'prepuzzle_files.json',
        'canned_hints.json',
        'responses.json',
        'prepuzzles.json'
    }

    activity_files = {
        'teams.json',
        'hints.json',
        'updates.json',
        'puzzle_statuses.json',
        'submissions.json'
    }

    with zipfile.ZipFile(zip_path, 'r') as zip_file:
        # Validate zip structure
        zip_contents = set(zip_file.namelist())
        missing_files = required_files - zip_contents
        if missing_files:
            raise ValidationError(f"Missing required files: {missing_files}")

        if include_activity:
            missing_activity = activity_files - zip_contents
            if missing_activity:
                raise ValidationError(f"Missing activity files: {missing_activity}")

        # Validate file references can be parsed
        try:
            with zip_file.open('file_references.json') as f:
                json.loads(f.read().decode('utf-8'))
        except json.JSONDecodeError:
            raise ValidationError("Invalid file_references.json format")

        # Validate all JSON files can be parsed
        for json_file in required_files | (activity_files if include_activity else set()):
            if not json_file.endswith('.json'):
                continue
            try:
                with zip_file.open(json_file) as f:
                    json.loads(f.read().decode('utf-8'))
            except json.JSONDecodeError:
                raise ValidationError(f"Invalid {json_file} format")


def import_hunt_from_zip(zip_path: str | Path, include_activity: bool = False) -> Hunt:
    """
    Imports a hunt from a zip file created by create_hunt_export_zip.
    
    Args:
        zip_path (str|Path): Path to the zip file containing the hunt data
        include_activity (bool): Whether to import activity data (teams, hints, etc.)
    
    Returns:
        Hunt: The newly created hunt object
        
    Raises:
        ValidationError: If the zip file is invalid or missing required data
        IntegrityError: If referenced users don't exist
    """
    # First validate the zip file
    validate_hunt_zip(zip_path, include_activity)

    with zipfile.ZipFile(zip_path, 'r') as zip_file:
        # Load file references
        with zip_file.open('file_references.json') as f:
            file_references = json.loads(f.read().decode('utf-8'))

        # Start transaction
        with transaction.atomic():
            # 1. Import hunt without file references
            hunt_objects = list(serializers.deserialize('json', zip_file.read('hunt.json')))
            new_hunt = hunt_objects[0].object
            new_hunt.is_current_hunt = False
            new_hunt.css_file = None
            config = new_hunt.config
            new_hunt.config = ""
            new_hunt.save()
            new_hunt.refresh_from_db()

            # Import template and info page files
            if 'files/template.html' in zip_file.namelist():
                with zip_file.open('files/template.html') as f:
                    new_hunt.template_file.save('template.html', File(f))
            if 'files/info_page.html' in zip_file.namelist():
                with zip_file.open('files/info_page.html') as f:
                    new_hunt.info_page_file.save('info_page.html', File(f))

            # 2. Import puzzles without file references
            puzzles = {}
            for obj in serializers.deserialize('json', zip_file.read('puzzles.json')):
                puzzle = obj.object
                puzzle.hunt = new_hunt
                puzzle.main_file = None  # Will be set later
                puzzle.main_solution_file = None  # Will be set later
                puzzle.save()
                puzzles[puzzle.id] = puzzle

            # Only set config after puzzles are created
            new_hunt.config = config
            new_hunt.save()

            # 3. Import prepuzzles without file references
            for obj in serializers.deserialize('json', zip_file.read('prepuzzles.json')):
                prepuzzle = obj.object
                prepuzzle.hunt = new_hunt
                prepuzzle.main_file = None  # Will be set later
                prepuzzle.save()

            # 4. Import all files and create file objects
            # Track specific files we need later
            hunt_css_file = None
            prepuzzle_main_file = None

            # Import hunt files
            for obj in serializers.deserialize('json', zip_file.read('hunt_files.json')):
                file_obj = obj.object
                file_obj.parent = new_hunt
                zip_path = f'files/hunt/{file_obj.relative_name}'
                if zip_path in zip_file.namelist():
                    with zip_file.open(zip_path) as f:
                        file_obj.file = File(f, name=Path(file_obj.file.name).name)
                        file_obj.save()
                        if (
                            file_references['hunt']['css_file'] and 
                            tuple(file_obj.natural_key()) == tuple(file_references['hunt']['css_file'])
                        ):
                            hunt_css_file = file_obj

            # Import puzzle files
            for obj in serializers.deserialize('json', zip_file.read('puzzle_files.json')):
                file_obj = obj.object
                puzzle_id = file_obj.parent_id
                file_obj.parent = puzzles[puzzle_id]
                zip_path = f'files/puzzle/{puzzle_id}/{file_obj.relative_name}'
                if zip_path in zip_file.namelist():
                    with zip_file.open(zip_path) as f:
                        file_obj.file = File(f, name=Path(file_obj.file.name).name)
                        file_obj.save()
                else:
                    print(f"Puzzle file {file_obj.relative_name} not found in zip")

            # Import solution files
            for obj in serializers.deserialize('json', zip_file.read('solution_files.json')):
                file_obj = obj.object
                puzzle_id = file_obj.parent_id
                file_obj.parent = puzzles[puzzle_id]
                zip_path = f'files/solution/{puzzle_id}/{file_obj.relative_name}'
                if zip_path in zip_file.namelist():
                    with zip_file.open(zip_path) as f:
                        file_obj.file = File(f, name=Path(file_obj.file.name).name)
                        file_obj.save()
                else:
                    print(f"Solution file {file_obj.relative_name} not found in zip")

            # Import prepuzzle files
            for obj in serializers.deserialize('json', zip_file.read('prepuzzle_files.json')):
                file_obj = obj.object
                file_obj.parent = new_hunt.prepuzzle  # We know there's only one prepuzzle
                zip_path = f'files/prepuzzle/{file_obj.relative_name}'
                if zip_path in zip_file.namelist():
                    with zip_file.open(zip_path) as f:
                        file_obj.file = File(f, name=Path(file_obj.file.name).name)
                        file_obj.save()
                        if (
                            'prepuzzle' in file_references and 
                            file_references['prepuzzle']['main_file'] and 
                            tuple(file_obj.natural_key()) == tuple(file_references['prepuzzle']['main_file'])
                        ):
                            prepuzzle_main_file = file_obj
                else:
                    print(f"Prepuzzle file {file_obj.relative_name} not found in zip")

            # 5. Import remaining models that don't need special handling
            for filename in ['responses.json', 'canned_hints.json', 'ranking_rules.json']:
                for obj in serializers.deserialize('json', zip_file.read(filename)):
                    obj.save()

            # 6. Import activity data if requested
            if include_activity:
                activity_order = [
                    'teams.json',  # Teams depend on Hunt
                    'updates.json',  # Updates depend on Hunt and optionally Puzzle
                    'puzzle_statuses.json',  # PuzzleStatus depends on Team and Puzzle
                    'submissions.json',  # Submissions depend on Team and Puzzle
                    'hints.json'  # Hints depend on Team and Puzzle
                ]
                for filename in activity_order:
                    for obj in serializers.deserialize('json', zip_file.read(filename)):
                        obj.save()

            # 7. Restore file references
            # Update hunt file references
            hunt_refs = file_references['hunt']
            if hunt_refs['css_file']:
                Hunt.objects.filter(pk=new_hunt.pk).update(css_file=hunt_css_file)
                new_hunt.refresh_from_db()

            # Update puzzle file references
            for puzzle_id, refs in file_references['puzzles'].items():
                puzzle = puzzles[puzzle_id]
                if refs['main_file']:
                    puzzle.main_file = PuzzleFile.objects.get_by_natural_key(*refs['main_file'])
                if refs['main_solution_file']:
                    puzzle.main_solution_file = SolutionFile.objects.get_by_natural_key(*refs['main_solution_file'])
                puzzle.save()

            # Update prepuzzle file reference - we know there's only one prepuzzle
            if 'prepuzzle' in file_references and hasattr(new_hunt, 'prepuzzle'):
                prepuzzle_refs = file_references['prepuzzle']
                if prepuzzle_refs['main_file']:
                    new_hunt.prepuzzle.main_file = prepuzzle_main_file
                    new_hunt.prepuzzle.save()

            return new_hunt