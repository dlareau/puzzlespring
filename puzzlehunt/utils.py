import io
import zipfile

from django.http import Http404
from django.shortcuts import get_object_or_404

from puzzlehunt import models
from django.core.files import File
from django_eventstream.channelmanager import DefaultChannelManager
from .models import PuzzleFile, SolutionFile, HuntFile, PrepuzzleFile, Puzzle, Hunt, Prepuzzle


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