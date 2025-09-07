from pypeg2 import parse, re, attr, List, csl, some, maybe_some, comment_sh
from datetime import timedelta

# Regexes
time_delta = re.compile(r"\d?\d:\d\d")
number = re.compile(r"\d+")
puzzle_id = re.compile(r"[a-fA-F0-9X]+")
time_unit = re.compile(r"MINUTES?|HOURS?")
point_unit = re.compile(r"POINTS?")
hint_unit = re.compile(r"HINTS?")
badge_unit = re.compile(r"BADGE")

# Object grammar classes
class PuzzleID:
    grammar = "P", attr("id", puzzle_id)

class PuzzleSolve:
    grammar = attr("puzzle", PuzzleID), "SOLVE"

class PuzzleUnlock:
    grammar = attr("puzzle", PuzzleID), "UNLOCK"

class TimeSinceStart:
    grammar = "+", attr("time", time_delta)

class NumPoints:
    grammar = attr("points", number), attr("unit", point_unit)

class TimeUnit:
    grammar = attr("unit", time_unit)

class NumHints:
    grammar = attr("hints", number), attr("unit", hint_unit)

class NumPuzzleHints:
    grammar = attr("hints", number), attr("puzzle", PuzzleID), attr("unit", hint_unit)

class Badge:
    grammar = '"', attr("text", re.compile(r'[^"]*')), '"', attr("unit", badge_unit)

PointInTime = [TimeSinceStart, PuzzleSolve, PuzzleUnlock]


# Unlockables
class UnlockableList(List):
    grammar = "[", csl([PuzzleID, NumPoints, NumHints, Badge]), "]"

Unlockable = [UnlockableList, PuzzleID, NumPoints, NumHints, NumPuzzleHints, Badge]


# Single-use rules
class Parenthesized: pass
class SomeOf(List): pass
class And(List): pass
class Or(List): pass

SingleUseRuleItems = PointInTime + [PuzzleID, NumPoints, SomeOf, Or, And, Parenthesized]

Parenthesized.grammar = "(", attr("item", SingleUseRuleItems), ")"
SomeOf.grammar = attr("num", number), "OF", "(", csl(SingleUseRuleItems), ")"
And.grammar = "(", SingleUseRuleItems, some("AND", SingleUseRuleItems), ")"
Or.grammar = "(", SingleUseRuleItems, some("OR", SingleUseRuleItems), ")"


# Multi-use rules
class TimeInterval:
    grammar = "EVERY", attr("interval", number), attr("unit", TimeUnit)

class TimeIntervalAfter:
    grammar = attr("interval", TimeInterval), "AFTER", attr("start_time", PointInTime)

class ConditionalTimeInterval:
    grammar = attr("interval", [TimeIntervalAfter, TimeInterval]), "IF", attr("condition", SingleUseRuleItems)

class LimitedTimeInterval:
    grammar = attr("interval", [ConditionalTimeInterval, TimeIntervalAfter, TimeInterval]), "LIMIT", attr("limit", number)

MultiUseRuleItems = [LimitedTimeInterval, ConditionalTimeInterval, TimeIntervalAfter, TimeInterval]


# File level grammars
class UnlockRule:
    grammar = attr("unlockable", Unlockable), "<=", attr("rule", [SingleUseRuleItems] + MultiUseRuleItems)

class ConfigFile(List):
    grammar = maybe_some(UnlockRule)


def preprocess_config(config_str, puzzle_ids):
    """
    Preprocess a config string to expand PX patterns into individual lines.
    
    Args:
        config_str: The configuration string to preprocess
        puzzle_ids: Set of valid puzzle IDs to expand PX with
    
    Returns:
        The preprocessed configuration string
    """
    lines = config_str.split('\n')
    expanded_lines = []
    
    for line in lines:
        if 'PX' in line.upper():
            # Skip comment lines
            if line.strip().startswith('#'):
                expanded_lines.append(line)
                continue
                
            # Replace PX with each puzzle ID
            for pid in sorted(puzzle_ids):
                expanded_lines.append(line.upper().replace('PX', f'P{pid}'))
        else:
            expanded_lines.append(line)
            
    return '\n'.join(expanded_lines)

def parse_config(config_str, puzzle_ids):
    """
    Parse a config string and validate puzzle IDs and check for circular dependencies.
    
    Args:
        config_str: The configuration string to parse
        puzzle_ids: Set of valid puzzle IDs to check against
    
    Raises:
        ValueError: If an invalid puzzle ID is referenced or circular dependencies are found
    """
    # Check that the original config string is valid
    try:
        config = parse(config_str.upper(), ConfigFile, comment=comment_sh)
    except SyntaxError as e:
        lines = config_str.split('\n')
        bad_line = None
        for line_num, line in enumerate(lines):
            try:
                config_test = parse(line.upper(), ConfigFile, comment=comment_sh)
            except SyntaxError as e:
                error_msg = str(e)
                bad_line = line_num + 1
                break

        if bad_line is None:
            error_msg = str(e)
            # Extract line number from error message
            if "(line " in error_msg:
                try:
                    bad_line = int(error_msg.split("(line ")[1].split(")")[0])
                except:
                    pass

        # If we have a line number, show the problematic line
        context = ""
        if bad_line is not None:
            lines = config_str.split('\n')
            if 0 <= bad_line - 1 < len(lines):
                context = f"on line {bad_line}:\n{lines[bad_line-1]}"

        # The error message will now use the friendly names from __str__ methods
        error_msg = f"Syntax error in configuration {context}"
        raise ValueError(error_msg)

    # Preprocess the config to expand PX patterns
    config_str = preprocess_config(config_str, puzzle_ids)

    config = parse(config_str.upper(), ConfigFile, comment=comment_sh)
    
    # Build dependency graph
    dependencies = {}
    
    def add_dependency(puzzle_id, depends_on):
        if puzzle_id not in dependencies:
            dependencies[puzzle_id] = set()
        dependencies[puzzle_id].add(depends_on)
    
    def check_cycles(puzzle_id, visited=None, path=None):
        if visited is None:
            visited = set()
        if path is None:
            path = []
            
        visited.add(puzzle_id)
        path.append(puzzle_id)
        
        if puzzle_id in dependencies:
            for dep in dependencies[puzzle_id]:
                if dep in path:
                    cycle = path[path.index(dep):] + [dep]
                    raise ValueError(f"Circular dependency detected: {' -> '.join('P' + id for id in cycle)}")
                if dep not in visited:
                    check_cycles(dep, visited, path)
        
        path.pop()
    
    # Collect dependencies and validate puzzle IDs
    referenced_ids = set()
    for rule in config:
        # Get the puzzle being unlocked
        if isinstance(rule.unlockable, List):
            unlockables = [item for item in rule.unlockable if isinstance(item, PuzzleID)]
        elif isinstance(rule.unlockable, PuzzleID):
            unlockables = [rule.unlockable]
        # elif isinstance(rule.unlockable, NumPuzzleHints):
        #     unlockables = [rule.unlockable.puzzle]
        else:
            unlockables = []
            
        for unlockable in unlockables:
            referenced_ids.add(unlockable.id)
            
        # Check rule conditions and build dependency graph
        def collect_dependencies(rule_item, target_puzzles):
            if isinstance(rule_item, PuzzleID):
                referenced_ids.add(rule_item.id)
                for target in target_puzzles:
                    add_dependency(target.id, rule_item.id)
            elif isinstance(rule_item, (PuzzleSolve, PuzzleUnlock)):
                referenced_ids.add(rule_item.puzzle.id)
                for target in target_puzzles:
                    add_dependency(target.id, rule_item.puzzle.id)
            elif isinstance(rule_item, (And, Or, SomeOf)):
                for item in rule_item:
                    if not isinstance(item, str):
                        collect_dependencies(item, target_puzzles)
            elif isinstance(rule_item, Parenthesized):
                collect_dependencies(rule_item.item, target_puzzles)
            elif isinstance(rule_item, ConditionalTimeInterval):
                collect_dependencies(rule_item.condition, target_puzzles)
        
        collect_dependencies(rule.rule, unlockables)
    
    # Check for invalid puzzle IDs if puzzle_ids was provided
    if puzzle_ids is not None:
        invalid_ids = referenced_ids - set(str(pid) for pid in puzzle_ids)
        if invalid_ids:
            raise ValueError(f"Config references non-existent puzzle IDs: {', '.join(sorted(invalid_ids))}")
    
    # Check for cycles in the dependency graph
    for puzzle_id in dependencies:
        check_cycles(puzzle_id)
    
    return config


def check_rule(rule, puzzle_status_dict, time, points):
    # Handle string inputs (like parentheses and commas)
    if isinstance(rule, str):
        return True

    match rule:
        case Parenthesized():
            return check_rule(rule.item, puzzle_status_dict, time, points)
            
        case And():
            # Get all items that aren't strings (skip parentheses, AND, commas)
            subrules = [r for r in rule if not isinstance(r, str)]
            return all(check_rule(subrule, puzzle_status_dict, time, points) for subrule in subrules)
            
        case Or():
            # Get all items that aren't strings (skip parentheses, OR, commas)
            subrules = [r for r in rule if not isinstance(r, str)]
            return any(check_rule(subrule, puzzle_status_dict, time, points) for subrule in subrules)
            
        case SomeOf():
            # Get the number and the list of items
            num = rule.num
            # Get all items that aren't strings (skip OF, parentheses, commas)
            subrules = [r for r in rule if not isinstance(r, str) and not isinstance(r, int)]
            return sum(1 for r in subrules if check_rule(r, puzzle_status_dict, time, points)) >= int(num)
            
        case PuzzleID():
            return rule.id in puzzle_status_dict and puzzle_status_dict[rule.id].solve_time is not None
            
        case TimeSinceStart():
            parts = rule.time.split(":")
            return time >= timedelta(hours=int(parts[0]), minutes=int(parts[1]))

        case PuzzleSolve():
            return rule.puzzle.id in puzzle_status_dict and puzzle_status_dict[rule.puzzle.id].solve_time is not None

        case PuzzleUnlock():
            return rule.puzzle.id in puzzle_status_dict and puzzle_status_dict[rule.puzzle.id].unlock_time is not None
            
        case NumPoints():
            return points >= int(rule.points)
            
        case _:
            raise ValueError(f"Unknown rule type: {type(rule)} - {rule}")


def get_multi_use_count(rule, puzzle_status_dict, start_time, current_time, points):
    """Helper function to determine how many times a multi-use rule should be applied"""
    time_elapsed = current_time - start_time
    match rule:
        case TimeInterval():
            interval = int(rule.interval)
            if rule.unit.unit.upper().startswith("HOUR"):
                interval *= 60
            # Convert total timedelta to minutes
            total_minutes = int(time_elapsed.total_seconds() / 60)
            return total_minutes // interval
            
        case TimeIntervalAfter():
            new_start_time = None
            match rule.start_time:
                case TimeSinceStart():
                    parts = rule.start_time.time.split(":")
                    new_start_time = start_time + timedelta(hours=int(parts[0]), minutes=int(parts[1]))
                case PuzzleSolve():
                    if rule.start_time.puzzle.id in puzzle_status_dict:
                        new_start_time = puzzle_status_dict[rule.start_time.puzzle.id].solve_time
                case PuzzleUnlock():
                    if rule.start_time.puzzle.id in puzzle_status_dict:
                        new_start_time = puzzle_status_dict[rule.start_time.puzzle.id].unlock_time

            
            # If we can't find a start time, return 0
            if new_start_time is None:
                return 0
            
            return get_multi_use_count(rule.interval, puzzle_status_dict, new_start_time, current_time, points)
            
        case ConditionalTimeInterval():
            if not check_rule(rule.condition, puzzle_status_dict, time_elapsed, points):
                return 0
            return get_multi_use_count(rule.interval, puzzle_status_dict, start_time, current_time, points)
            
        case LimitedTimeInterval():
            return min(get_multi_use_count(rule.interval, puzzle_status_dict, start_time, current_time, points), int(rule.limit))
            
        case _:
            # Single use rules
            return 1 if check_rule(rule, puzzle_status_dict, time_elapsed, points) else 0


def process_config_rules(rules, puzzle_statuses, start_time, current_time):
    points = 0
    hints = 0
    unlocked_puzzles = set()
    processed_rules = set()
    puzzle_hints = {}  # Maps puzzle IDs to number of hints
    earned_badges = []  # Track earned badges
    
    def process_reward(rule, rule_value, item_type, value, puzzle_id=None):
        rule_id = (str(rule.rule), item_type, value, puzzle_id)
        if rule_id not in processed_rules:
            reward = rule_value * int(value)
            processed_rules.add(rule_id)
            return reward, True
        return 0, False

    puzzle_status_dict = {status.puzzle_id: status for status in puzzle_statuses}
    time_elapsed = current_time - start_time

    # Keep processing rules until no new changes occur
    changed = True
    while changed:
        changed = False
        for rule in rules:
            # Calculate rule value once
            if isinstance(rule.rule, (TimeInterval, TimeIntervalAfter, ConditionalTimeInterval, LimitedTimeInterval)):
                rule_value = get_multi_use_count(rule.rule, puzzle_status_dict, start_time, current_time, points)
                rule_applies = rule_value > 0
            else:
                rule_applies = check_rule(rule.rule, puzzle_status_dict, time_elapsed, points)
                rule_value = 1 if rule_applies else 0
                
            if rule_applies:
                unlockables = [rule.unlockable] if not isinstance(rule.unlockable, List) else rule.unlockable
                for item in unlockables:
                    match item:
                        case PuzzleID():
                            if item.id not in unlocked_puzzles:
                                unlocked_puzzles.add(item.id)
                                changed = True
                        case NumPoints():
                            reward, was_changed = process_reward(rule, rule_value, "points", item.points)
                            points += reward
                            changed = changed or was_changed
                        case NumHints():
                            reward, was_changed = process_reward(rule, rule_value, "hints", item.hints)
                            hints += reward
                            changed = changed or was_changed
                        case NumPuzzleHints():
                            reward, was_changed = process_reward(rule, rule_value, "puzzle_hints", item.hints, item.puzzle.id)
                            if item.puzzle.id not in puzzle_hints:
                                puzzle_hints[item.puzzle.id] = 0
                            puzzle_hints[item.puzzle.id] += reward
                            changed = changed or was_changed
                        case Badge():
                            badge_text = item.text
                            if badge_text not in earned_badges:
                                earned_badges.append(badge_text)
                                changed = True

    return unlocked_puzzles, points, hints, puzzle_hints, earned_badges