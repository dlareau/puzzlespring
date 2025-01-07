import json
import random
import os
import re
from collections import defaultdict
import shutil
import argparse
from dataclasses import dataclass, field
from typing import Dict, List, Any

@dataclass
class ConversionContext:
    """Holds shared state for the conversion process"""
    input_media_directory: str
    output_data_directory: str
    output_media_directory: str
    models_file: str
    output_file: str
    
    # Shared conversion state
    puzzle_pk_mapping: Dict[int, str] = field(default_factory=dict)
    media_files: List[Dict] = field(default_factory=list)
    
    @classmethod
    def from_directories(cls, old_data_dir: str, output_dir: str) -> 'ConversionContext':
        """Create context from input/output directory paths"""
        return cls(
            input_media_directory=os.path.join(old_data_dir, "media"),
            output_data_directory=output_dir,
            output_media_directory=os.path.join(output_dir, "media"),
            models_file=os.path.join(old_data_dir, 'db_09_2023.json'),
            output_file=os.path.join(output_dir, "converted_data.json")
        )

def rewrite_models(ctx: ConversionContext):
    """Main conversion function using shared context"""
    with open(ctx.models_file) as f:
        data = json.load(f)

    output = []
    submissions = {}
    users = {}
    people = {}
    puzzle_ids = []
    prepuzzle_ids = []
    hunt_ids = []
    solves = {}
    emails = []
    team_members = defaultdict(list)
    reverse_pk_mapping = {}  # puzzle_id -> old pk
    
    # First pass - collect IDs
    for model_instance in data:
        if model_instance['model'] == "huntserver.puzzle":
            puzzle_ids.append(str(model_instance['fields']['puzzle_id']))
        if model_instance['model'] == "huntserver.hunt":
            hunt_ids.append(str(model_instance['pk']))
        if model_instance['model'] == "huntserver.prepuzzle":
            prepuzzle_ids.append(str(model_instance['pk']))
    
    # Generate media files
    ctx.media_files = get_media_objects(hunt_ids, puzzle_ids, prepuzzle_ids, ctx)

    # First pass - build pk mappings
    for model_instance in data:
        if model_instance['model'] == "huntserver.puzzle":
            old_pk = model_instance['pk']
            puzzle_id = model_instance['fields']['puzzle_id']
            ctx.puzzle_pk_mapping[old_pk] = puzzle_id
            reverse_pk_mapping[puzzle_id] = old_pk
            
    # Second pass - collect puzzle unlocking data
    hunt_puzzles = defaultdict(list)  # hunt_id -> list of puzzle instances
    puzzle_unlocks = defaultdict(list)  # puzzle_id -> list of puzzles it helps unlock
    hunt_points_per_min = {}  # hunt_id -> points per minute

    for model_instance in data:
        model = model_instance['model']
        if model == "huntserver.puzzle":
            hunt_id = model_instance['fields']['hunt']
            puzzle_id = model_instance['fields']['puzzle_id']
            hunt_puzzles[hunt_id].append(model_instance)
            
            # Store which puzzles this one helps unlock, converting old pks to puzzle_ids
            if model_instance['fields']['unlocks']:
                for unlocked_pk in model_instance['fields']['unlocks']:
                    unlocked_puzzle_id = ctx.puzzle_pk_mapping[unlocked_pk]
                    puzzle_unlocks[unlocked_puzzle_id].append(puzzle_id)
        elif model == "huntserver.hunt":
            hunt_points_per_min[model_instance['pk']] = model_instance['fields']['points_per_minute']

    # Main processing loop
    for model_instance in data:
        model = model_instance['model']

        # Models that will be copied over
        if model == "huntserver.hunt":
            # Generate config for this hunt
            config = generate_hunt_config(
                hunt_puzzles[model_instance['pk']],
                puzzle_unlocks,
                hunt_points_per_min[model_instance['pk']]
            )
            rewrite_hunt(model_instance, config, ctx)
        elif model == "huntserver.puzzle":
            rewrite_puzzle(model_instance, ctx)
        elif model == "huntserver.team":
            rewrite_team(model_instance)
        elif model == "huntserver.prepuzzle":
            rewrite_prepuzzle(model_instance, ctx)
        elif model == "huntserver.hint":
            model_instance['model'] = "puzzlehunt.hint"
            model_instance['fields']['puzzle'] = ctx.puzzle_pk_mapping[model_instance['fields']['puzzle']]
            if model_instance['fields']['responder'] is not None:
                username = people[model_instance['fields']['responder']]['fields']['user'][0]
                model_instance['fields']['responder'] = users[username]['pk']
        elif model == "huntserver.submission":
            model_instance['model'] = "puzzlehunt.submission"
            model_instance['fields']['puzzle'] = ctx.puzzle_pk_mapping[model_instance['fields']['puzzle']]
            model_instance['fields']['modified_time'] = model_instance['fields']['modified_date']
            del model_instance['fields']['modified_date']
            submissions[model_instance['pk']] = model_instance
        elif model == "huntserver.unlock":
            model_instance['model'] = "puzzlehunt.puzzlestatus"
            if (model_instance['fields']['team'], model_instance['fields']['puzzle']) in solves:
                model_instance['fields']['solve_time'] = solves[
                    (model_instance['fields']['team'], model_instance['fields']['puzzle'])]
            model_instance['fields']['puzzle'] = ctx.puzzle_pk_mapping[model_instance['fields']['puzzle']]
            model_instance['fields']['unlock_time'] = model_instance['fields']['time']
            del model_instance['fields']['time']
        elif model == "huntserver.response":
            model_instance['model'] = "puzzlehunt.response"
            model_instance['fields']['puzzle'] = ctx.puzzle_pk_mapping[model_instance['fields']['puzzle']]
        elif model == "sites.site":
            pass
        # TODO: Flatpages are not migrated for now.
        # elif model == "flatpages.flatpage":
        #     pass 
        else:
            # Models that aren't carried over but still need data extracted
            if model == "huntserver.person":
                for t in model_instance['fields']['teams']:
                    team_members[t].append(users[model_instance['fields']['user'][0]]['pk'])
                people[model_instance['pk']] = model_instance
            elif model == "huntserver.solve":
                solves[(model_instance['fields']['team'], model_instance['fields']['puzzle'])] = \
                    submissions[model_instance['fields']['submission']]['fields']['submission_time']
            elif model == "auth.user":
                model_instance['model'] = "puzzlehunt.user"

                email = model_instance['fields']['email']
                if email in emails:
                    if "@" not in email:
                        model_instance['fields']['email'] = str(random.randint(0, 1000))
                    else:
                        model_instance['fields']['email'] = f"{email.split('@')[0]}+{str(random.randint(0, 10000))}@{email.split('@')[1]}"
                    print(f"Duplicate email: {email}. New email: {model_instance['fields']['email']}")
                emails.append(email)

                model_instance['fields']['display_name'] = model_instance['fields']['username']
                del model_instance['fields']['username']
                users[model_instance['fields']['display_name']] = model_instance
            elif model == "huntserver.hintunlockplan":
                pass
            continue  # Don't carry over these models

        # Copy over the model instance
        output.append(model_instance)

    output = output + list(users.values()) + ctx.media_files

    # Set team members
    for o in output:
        if o['model'] == "puzzlehunt.team":
            o['fields']['members'] = team_members[o['pk']]

    fo = open(ctx.output_file, "w")
    json.dump(output, fo)
    fo.close()


def generate_hunt_config(puzzles, puzzle_unlocks, points_per_min):
    """Generate the hunt config string based on the old unlocking rules."""
    config_lines = []
    
    # Add points per minute rule if applicable
    if points_per_min > 0:
        config_lines.append(f"[{points_per_min} POINTS] <= EVERY 1 MINUTE")
    
    # Process each puzzle's unlocking rules
    for puzzle in puzzles:
        puzzle_id = puzzle['fields']['puzzle_id']
        cost = puzzle['fields']['points_cost']
        value = puzzle['fields']['points_value']
        unlock_type = puzzle['fields']['unlock_type']
        
        # Add points awarded for solving
        if value > 0:
            config_lines.append(f"[{value} POINTS] <= P{puzzle_id}")
        
        # Generate unlocking rule
        points_condition = f"{cost} POINTS" if cost > 0 else None
        
        # Add puzzle requirements if applicable
        puzzle_condition = None
        if puzzle_id in puzzle_unlocks:
            required = puzzle['fields']['num_required_to_unlock']
            contributing_puzzles = puzzle_unlocks[puzzle_id]
            if required > 0 and contributing_puzzles:
                if len(contributing_puzzles) == 1:
                    puzzle_condition = f"P{contributing_puzzles[0]}"
                if required == len(contributing_puzzles):
                    # All puzzles required - use AND
                    puzzle_condition = f"({' AND '.join(f'P{p}' for p in contributing_puzzles)})"
                else:
                    # Only some puzzles required - use X OF
                    puzzle_condition = f"{required} OF ({', '.join(f'P{p}' for p in contributing_puzzles)})"
        
        # Create the full unlock rule based on unlock_type
        if points_condition or puzzle_condition:
            match unlock_type:
                case 'SOL':  # PUZZLE_UNLOCK - only puzzles
                    if puzzle_condition:
                        config_lines.append(f"[P{puzzle_id}] <= {puzzle_condition}")
                case 'POT':  # POINTS_UNLOCK - only points
                    if points_condition:
                        config_lines.append(f"[P{puzzle_id}] <= {points_condition}")
                case 'ETH':  # EITHER_UNLOCK - either puzzles or points
                    conditions = []
                    if puzzle_condition:
                        conditions.append(puzzle_condition)
                    if points_condition:
                        conditions.append(points_condition)
                    if conditions:
                        config_lines.append(f"[P{puzzle_id}] <= ({' OR '.join(conditions)})")
                case 'BTH':  # BOTH_UNLOCK - both puzzles and points
                    conditions = []
                    if puzzle_condition:
                        conditions.append(puzzle_condition)
                    if points_condition:
                        conditions.append(points_condition)
                    if conditions:
                        config_lines.append(f"[P{puzzle_id}] <= ({' AND '.join(conditions)})")
    
    return "\n".join(config_lines)


def rewrite_hunt(model_instance: Dict, config: str, ctx: ConversionContext):
    """Update hunt model instance with new structure"""
    model_instance['model'] = "puzzlehunt.hunt"
    
    # Field renames
    model_instance['fields']['name'] = model_instance['fields'].pop('hunt_name')
    model_instance['fields']['team_size_limit'] = model_instance['fields'].pop('team_size')
    
    # Process template
    template_contents = model_instance['fields'].pop('template')
    template_contents = re.sub(r"\{\{ ?STATIC_URL ?}}huntserver", "{{ STATIC_URL }}puzzlehunt", template_contents)
    template_contents = re.sub(r"puzzle_number", "order_number", template_contents)
    template_contents = re.sub(r"puzzle_type", "type", template_contents)
    template_contents = re.sub(r"puzzle_id", "id", template_contents)
    template_contents = re.sub(r"puzzle_name", "name", template_contents)
    template_contents = re.sub(r"META_PUZZLE", "PuzzleType.META_PUZZLE", template_contents)
    template_contents = re.sub(r"STANDARD_PUZZLE", "PuzzleType.STANDARD_PUZZLE", template_contents)
    template_contents = re.sub(r"FINAL_PUZZLE", "PuzzleType.FINAL_PUZZLE", template_contents)
    template_contents = re.sub(r"NON_PUZZLE", "PuzzleType.NON_PUZZLE", template_contents)
    template_contents = re.sub(r"/puzzle/\{\{(.*?)}}/", "/puzzle/{{\\1}}/view/", template_contents)
    template_contents = re.sub(r"/media/hunt/\d+/", "{% hunt_static %}", template_contents)
    template_contents = re.sub(r"{% hunt_static %}/", "{% hunt_static %}", template_contents)

    # Write template file
    template_path = f"trusted/hunt/{model_instance['pk']}/template.html"
    template_filename = f"{ctx.output_media_directory}/{template_path}"
    os.makedirs(os.path.dirname(template_filename), exist_ok=True)
    with open(template_filename, 'w') as f:
        f.write(template_contents)

    model_instance['fields']['template_file'] = template_path
    
    # Add the config
    model_instance['fields']['config'] = config
    
    # Remove unused fields
    fields_to_remove = ['hunt_number', 'extra_data', 'resource_file', 'points_per_minute']
    for field in fields_to_remove:
        model_instance['fields'].pop(field, None)


def rewrite_puzzle(model_instance: Dict, ctx: ConversionContext):
    """Update puzzle model instance with new structure"""
    model_instance['model'] = "puzzlehunt.puzzle"
    
    # Field renames
    model_instance['fields']['name'] = model_instance['fields'].pop('puzzle_name')
    model_instance['fields']['order_number'] = model_instance['fields'].pop('puzzle_number')
    model_instance['fields']['type'] = model_instance['fields'].pop('puzzle_type')
    
    # Store ID mapping
    puzzle_id = model_instance['fields'].pop('puzzle_id')
    ctx.puzzle_pk_mapping[model_instance['pk']] = puzzle_id
    model_instance['pk'] = puzzle_id
    
    # Process validation type
    validation_type = model_instance['fields'].pop('answer_validation_type')
    model_instance['fields'].update({
        'allow_spaces': validation_type in ['CAS', 'ANY'],
        'case_sensitive': validation_type in ['ACA', 'CAS', 'ANY'],
        'allow_non_alphanumeric': validation_type == 'ANY'
    })
    
    # Set main files
    puzzle_dir = f"{ctx.output_media_directory}/trusted/puzzle/{model_instance['pk']}/files"
    solution_dir = f"{ctx.output_media_directory}/trusted/solution/{model_instance['pk']}/files"
    
    model_instance['fields']['main_file'] = find_main_file(
        ctx.media_files, model_instance['pk'], 'puzzle', puzzle_dir)
    model_instance['fields']['main_solution_file'] = find_main_file(
        ctx.media_files, model_instance['pk'], 'solution', solution_dir)
    
    # Remove unused fields
    fields_to_remove = [
        'points_cost', 'points_value', 'unlocks', 'num_required_to_unlock',
        'unlock_type', 'resource_file', 'puzzle_file', 'solution_file',
        'solution_resource_file', 'solution_is_webpage', 'puzzle_page_type'
    ]
    for field in fields_to_remove:
        model_instance['fields'].pop(field, None)


def rewrite_team(model_instance: Dict):
    """Update team model instance with new structure"""
    model_instance['model'] = "puzzlehunt.team"
    
    # Field renames and modifications
    model_instance['fields']['name'] = model_instance['fields'].pop('team_name')
    if len(model_instance['fields']['name']) > 100:
        model_instance['fields']['name'] = model_instance['fields']['name'][:95] + "..."
    
    # Points handling
    model_instance['fields']['points'] = model_instance['fields']['num_unlock_points']
    
    # Remove unused fields
    fields_to_remove = [
        'team_name',
        'unlockables',
        'location',
        'num_waiting_messages',
        'num_unlock_points'
    ]
    for field in fields_to_remove:
        model_instance['fields'].pop(field, None)


def rewrite_prepuzzle(model_instance: Dict, ctx: ConversionContext):
    """Update prepuzzle model instance with new structure"""
    model_instance['model'] = "puzzlehunt.prepuzzle"
    
    # Field renames
    model_instance['fields']['name'] = model_instance['fields'].pop('puzzle_name')
    
    # Handle template content
    template_contents = model_instance['fields'].pop('template')
    template_contents = re.sub(r"\{\{ ?STATIC_URL ?}}huntserver", "{{ STATIC_URL }}puzzlehunt", template_contents)
    template_contents = re.sub(r"load prepuzzle_tags", "load hunt_tags", template_contents)
    template_contents = re.sub(r"/media/prepuzzle/\d+/", "{% prepuzzle_static %}", template_contents)
    template_contents = re.sub(r"{% prepuzzle_static %}/", "{% prepuzzle_static %}", template_contents)
    template_contents = re.sub(r"{% extends \"prepuzzle.html\" %}", "{% extends \"prepuzzle_base.html\" %}", template_contents)

    # Create and write template file
    template_path = f"trusted/prepuzzle/{model_instance['pk']}/files/prepuzzle.tmpl"
    template_filename = f"{ctx.output_media_directory}/{template_path}"
    os.makedirs(os.path.dirname(template_filename), exist_ok=True)
    with open(template_filename, 'w') as f:
        f.write(template_contents)

    # Create media file entry
    new_media_file = {
        "model": "puzzlehunt.prepuzzlefile",
        "pk": len(ctx.media_files) + 1,
        "fields": {
            "file": template_path,
            "parent": model_instance['pk']
        }
    }
    ctx.media_files.append(new_media_file)
    model_instance['fields']['main_file'] = new_media_file['pk']

    # Handle validation type
    validation_type = model_instance['fields'].pop('answer_validation_type')
    model_instance['fields'].update({
        'allow_spaces': validation_type in ['CAS', 'ANY'],
        'case_sensitive': validation_type in ['ACA', 'CAS', 'ANY'],
        'allow_non_alphanumeric': validation_type == 'ANY'
    })

    # Remove unused fields
    fields_to_remove = ['puzzle_name', 'resource_file']
    for field in fields_to_remove:
        model_instance['fields'].pop(field, None)



def find_main_file(media_files: List[Dict], parent_pk: int, file_type: str, directory: str) -> int:
    """Find the main file ID for a puzzle or solution"""
    if os.path.exists(f"{directory}/index.html"):
        path = f"{file_type}/{parent_pk}/files/index.html"
    else:
        suffix = '_sol.pdf' if file_type == 'solution' else '.pdf'
        path = f"{file_type}/{parent_pk}/files/{parent_pk}{suffix}"
    
    for media_file in media_files:
        if (media_file['model'] == f'puzzlehunt.{file_type}file' and 
            media_file['fields']['parent'] == parent_pk and
            media_file['fields']['file'] == f"trusted/{path}"):
            return media_file['pk']
    return None


def process_media_files(ctx: ConversionContext):
    """Process and copy all media files to new structure"""
    os.makedirs(ctx.output_media_directory, exist_ok=True)
    trusted_dir = os.path.join(ctx.output_media_directory, "trusted")
    os.makedirs(trusted_dir, exist_ok=True)
    
    # Copy files for each type
    file_types = {
        'puzzles': ('puzzle', lambda x: x.split("-")[0]),
        'solutions': ('solution', lambda x: x.replace("_sol", "")),
        'hunt': ('hunt', lambda x: x),
        'prepuzzles': ('prepuzzle', lambda x: x.split("-")[0])
    }
    
    for src_dir, (dest_type, id_func) in file_types.items():
        input_dir = os.path.join(ctx.input_media_directory, src_dir)
        if not os.path.exists(input_dir):
            continue
            
        process_directory(input_dir, trusted_dir, dest_type, id_func)
    
    # Process all files for media path replacement
    process_directory_for_media_paths(ctx.output_media_directory)


def process_directory(input_dir: str, trusted_dir: str, dest_type: str, id_func: callable):
    """Process a single media directory type"""
    # Process directories first
    for item in os.scandir(input_dir):
        if item.is_dir() and "MACOSX" not in item.path:
            id = id_func(item.name)
            target_dir = f'{trusted_dir}/{dest_type}/{id}/files'
            os.makedirs(target_dir, exist_ok=True)
            shutil.copytree(item.path, target_dir, dirs_exist_ok=True)
    
    # Process remaining files
    for item in os.scandir(input_dir):
        if not item.is_file() or "MACOSX" in item.path:
            continue
            
        name, ext = os.path.splitext(item.name)
        if ext == ".zip":
            os.makedirs(f'{os.path.dirname(trusted_dir)}/original_zips', exist_ok=True)
            shutil.copy2(item.path, f'{os.path.dirname(trusted_dir)}/original_zips/{dest_type}_{item.name}')
        else:
            id = id_func(name)
            target_dir = f'{trusted_dir}/{dest_type}/{id}/files'
            os.makedirs(target_dir, exist_ok=True)
            shutil.copy2(item.path, f'{target_dir}/{item.name}')


def replace_media_paths_in_file(file_path):
    """Replace old media paths with new view paths in file if it's an HTML, JS, or CSS file."""
    # Only process specific file types
    if not file_path.lower().endswith(('.html', '.js', '.css')):
        return
        
    try:
        # Read the file content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Perform the replacement
        new_content = re.sub(r'/media/hunt/(\d+)/', r'/hunt/\1/view/', content)
        
        # Only write if content changed
        if new_content != content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
                
    except (UnicodeDecodeError, IOError) as e:
        print(f"Error processing file {file_path}: {str(e)}")


def process_directory_for_media_paths(directory):
    """Recursively process all files in a directory to replace media paths."""
    for root, _, files in os.walk(directory):
        for file in files:
            if "MACOSX" not in root:  # Skip Mac system files
                file_path = os.path.join(root, file)
                replace_media_paths_in_file(file_path)


def put_files_in_folders(input_dir, output_dir):
    """Copy files from input_directory to output_directory in the new structure.
    Creates output_directory if it doesn't exist."""
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Create trusted directory
    trusted_dir = os.path.join(output_dir, "trusted")
    os.makedirs(trusted_dir, exist_ok=True)
    
    # Puzzles
    puzzle_dir = input_dir + "/puzzles"
    if os.path.exists(puzzle_dir):
        # Copy directories first
        files = os.scandir(puzzle_dir)
        for file in files:
            if file.is_dir() and "MACOSX" not in file.path:
                p = file.path.split("/")
                id = p[-1].split("-")[0]
                target_dir = f'{trusted_dir}/puzzle/{id}/files'
                os.makedirs(target_dir, exist_ok=True)
                shutil.copytree(file.path, target_dir, dirs_exist_ok=True)
                
        # Copy leftover files
        files = os.scandir(puzzle_dir)
        for file in files:
            if file.is_file() and "MACOSX" not in file.path:
                p = file.path.split("/")
                name, ext = os.path.splitext(p[-1])
                if ext == ".zip":
                    os.makedirs(f'{output_dir}/original_zips', exist_ok=True)
                    shutil.copy2(file.path, f'{output_dir}/original_zips/puzzle_{p[-1]}')
                else:
                    id = name.split("-")[0]
                    target_dir = f'{trusted_dir}/puzzle/{id}/files'
                    os.makedirs(target_dir, exist_ok=True)
                    shutil.copy2(file.path, f'{target_dir}/{p[-1]}')

    # Solutions
    old_solution_dir = input_dir + "/solutions"
    if os.path.exists(old_solution_dir):
        # Handle zip files first
        files = os.scandir(old_solution_dir)
        for file in files:
            if file.is_file() and "MACOSX" not in file.path:
                p = file.path.split("/")
                name, ext = os.path.splitext(p[-1])
                if ext == ".zip":
                    os.makedirs(f'{output_dir}/original_zips', exist_ok=True)
                    shutil.copy2(file.path, f'{output_dir}/original_zips/solution_{p[-1]}')

        # Handle directories
        files = os.scandir(old_solution_dir)
        for file in files:
            if file.is_dir() and "MACOSX" not in file.path:
                puzzle_id = file.name.replace("_sol", "")
                target_dir = f'{trusted_dir}/solution/{puzzle_id}/files'
                os.makedirs(target_dir, exist_ok=True)
                shutil.copytree(file.path, target_dir, dirs_exist_ok=True)

        # Handle remaining files
        files = os.scandir(old_solution_dir)
        for file in files:
            if file.is_file() and "MACOSX" not in file.path and not file.name.endswith(".zip"):
                id = file.name.split("_")[0]
                target_dir = f'{trusted_dir}/solution/{id}/files'
                os.makedirs(target_dir, exist_ok=True)
                shutil.copy2(file.path, f'{target_dir}/{file.name}')

    # Hunts
    hunt_dir = input_dir + "/hunt"
    if os.path.exists(hunt_dir):
        # Handle zip files first
        files = os.scandir(hunt_dir)
        for file in files:
            if file.is_file() and "MACOSX" not in file.path:
                p = file.path.split("/")
                name, ext = os.path.splitext(p[-1])
                if ext == ".zip":
                    os.makedirs(f'{output_dir}/original_zips', exist_ok=True)
                    shutil.copy2(file.path, f'{output_dir}/original_zips/hunt_{p[-1]}')

        files = os.scandir(hunt_dir)
        for file in files:
            if file.is_dir() and "MACOSX" not in file.path:
                target_dir = f'{trusted_dir}/hunt/{file.name}/files'
                os.makedirs(target_dir, exist_ok=True)
                shutil.copytree(file.path, target_dir, dirs_exist_ok=True)

    # Add prepuzzles handling after puzzles section
    prepuzzle_dir = input_dir + "/prepuzzles"
    if os.path.exists(prepuzzle_dir):
        # Copy directories first
        files = os.scandir(prepuzzle_dir)
        for file in files:
            if file.is_dir() and "MACOSX" not in file.path:
                p = file.path.split("/")
                id = p[-1].split("-")[0]
                target_dir = f'{trusted_dir}/prepuzzle/{id}/files'
                os.makedirs(target_dir, exist_ok=True)
                shutil.copytree(file.path, target_dir, dirs_exist_ok=True)
                
        # Copy leftover files
        files = os.scandir(prepuzzle_dir)
        for file in files:
            if file.is_file() and "MACOSX" not in file.path:
                p = file.path.split("/")
                name, ext = os.path.splitext(p[-1])
                if ext == ".zip":
                    os.makedirs(f'{output_dir}/original_zips', exist_ok=True)
                    shutil.copy2(file.path, f'{output_dir}/original_zips/prepuzzle_{p[-1]}')
                else:
                    id = name.split("-")[0]
                    target_dir = f'{trusted_dir}/prepuzzle/{id}/files'
                    os.makedirs(target_dir, exist_ok=True)
                    shutil.copy2(file.path, f'{target_dir}/{p[-1]}')

    # After all files are copied, process them for media path replacement
    process_directory_for_media_paths(output_dir)


def discover_media_files(directory, file_type, media_file_objects, valid_ids, ctx: ConversionContext):
    """Update discover_media_files to use ConversionContext"""
    files = os.scandir(directory)
    for file in files:
        if file.is_file() and "MACOSX" not in file.path:
            obj = create_media_file(file, file_type, len(media_file_objects) + 1, valid_ids, ctx)
            if obj is not None:
                media_file_objects.append(obj)
        elif file.is_dir():
            discover_media_files(file.path, file_type, media_file_objects, valid_ids, ctx)


def create_media_file(file, file_type, new_id, valid_ids, ctx: ConversionContext):
    """Update create_media_file to use ConversionContext"""
    p = file.path.split("/")
    if "files" not in p:
        return None
    id = p[p.index("files") - 1]

    if id not in valid_ids:
        if id == "assets":  # This is due to the legacy assets directory 
            return None
        print(f"Not attempting to insert {file_type} {file.path} with ID {id} due to missing object")
        return None
    
    # Update path to include trusted/
    new_path = file.path.removeprefix(f"{ctx.output_media_directory}/")
    if not new_path.startswith("trusted/"):
        new_path = f"trusted/{new_path}"

    new_media_file = {
        "model": f"puzzlehunt.{file_type}file",
        "pk": new_id,
        "fields": {
            "file": new_path,
            "parent": id,
        },
    }

    return new_media_file


def get_media_objects(hunt_ids, puzzle_ids, prepuzzle_ids, ctx: ConversionContext):
    """Update get_media_objects to use ConversionContext"""
    hunt_files = []
    puzzle_files = []
    solution_files = []
    prepuzzle_files = []
    trusted_dir = os.path.join(ctx.output_media_directory, "trusted")
    discover_media_files(trusted_dir + "/puzzle", "puzzle", puzzle_files, puzzle_ids, ctx)
    discover_media_files(trusted_dir + "/solution", "solution", solution_files, puzzle_ids, ctx)
    discover_media_files(trusted_dir + "/hunt", "hunt", hunt_files, hunt_ids, ctx)
    discover_media_files(trusted_dir + "/prepuzzle", "prepuzzle", prepuzzle_files, prepuzzle_ids, ctx)
    media_files = hunt_files + puzzle_files + solution_files + prepuzzle_files
    return media_files


def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Convert puzzle hunt data from old format to new format')
    parser.add_argument('old_data_dir', help='Directory containing the old data files')
    parser.add_argument('output_dir', help='Directory where converted data should be stored')
    
    args = parser.parse_args()
    
    # Setup paths based on arguments
    ctx = ConversionContext.from_directories(args.old_data_dir, args.output_dir)
    
    # Create output directory if it doesn't exist
    os.makedirs(ctx.output_data_directory, exist_ok=True)
    
    # First copy and reorganize media files
    put_files_in_folders(ctx.input_media_directory, ctx.output_media_directory)
    
    # Then generate converted database dump with media files included
    rewrite_models(ctx)


if __name__ == "__main__":
    main()
