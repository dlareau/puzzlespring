from pypeg2 import parse, re, attr, List, csl, some, maybe_some, comment_sh
from datetime import timedelta

# Regexes
time_delta = re.compile(r"\d?\d:\d\d")
number = re.compile(r"\d+")
puzzle_id = re.compile(r"[a-fA-F0-9]+")
time_unit = re.compile(r"MINUTES?|HOURS?")
point_unit = re.compile(r"POINTS?")
hint_unit = re.compile(r"HINTS?")

# region grammar classes
class PuzzleID:
    grammar = "P", attr("id", puzzle_id)

    def __repr__(self):
        return "P" + self.id

class TimeSinceStart:
    grammar = "+", attr("time", time_delta)

    def __repr__(self):
        return f"{self.time} after start"

class NumPoints:
    grammar = attr("points", number), attr("unit", point_unit)

    def __repr__(self):
        return f"{self.points} points"

class TimeUnit:
    grammar = attr("unit", time_unit)

class TimeInterval:
    grammar = "EVERY", attr("interval", number), attr("unit", TimeUnit)

    def __repr__(self):
        return f"every {self.interval} {self.unit.unit.lower()}"

# Add new class for Hints
class NumHints:
    grammar = attr("hints", number), attr("unit", hint_unit)

    def __repr__(self):
        return f"{self.hints} hints"

# Define what can be unlocked
class Unlockable(List):
    grammar = "[", csl([PuzzleID, NumPoints, NumHints]), "]"

    def __repr__(self):
        return f"[{', '.join(map(str, self))}]"

# Single unlockable can be either a list or single item
SingleUnlockable = [Unlockable, PuzzleID, NumPoints, NumHints]

# Define what can be used in rules
RuleItems = [PuzzleID, TimeSinceStart, NumPoints, TimeInterval]

class SomeOf(List):
    grammar = attr("num", number), "OF", "(", csl(RuleItems), ")"

class And(List): pass
class Or(List): pass

# Add SomeOf, And, and Or to the list of possible rule items
RuleItems.extend([SomeOf, Or, And])

And.grammar = "(", RuleItems, some("AND", RuleItems), ")"
Or.grammar = "(", RuleItems, some("OR", RuleItems), ")"

class UnlockRule:
    # Use RuleItems for all rule types
    grammar = attr("unlockable", SingleUnlockable), "<=", attr("rule", RuleItems)

    def __repr__(self):
        return f"{self.unlockable} <= {self.rule}"

class ConfigFile(List):
    grammar = maybe_some(UnlockRule)

    def __repr__(self):
        return "\n".join(map(str, self))

def parse_config(config_str, puzzle_ids=None):
    """
    Parse a config string and validate puzzle IDs and check for circular dependencies.
    
    Args:
        config_str: The configuration string to parse
        puzzle_ids: Optional set of valid puzzle IDs to check against
    
    Raises:
        ValueError: If an invalid puzzle ID is referenced or circular dependencies are found
    """
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
            elif isinstance(rule_item, (And, Or, SomeOf)):
                for item in rule_item:
                    if not isinstance(item, str):
                        collect_dependencies(item, target_puzzles)
        
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

def check_rule(rule, solved_puzzles, time, points):
    # Handle string inputs (like parentheses and commas)
    if isinstance(rule, str):
        return True

    match rule:
        case And():
            # Get all items that aren't strings (skip parentheses, AND, commas)
            subrules = [r for r in rule if not isinstance(r, str)]
            return all(check_rule(subrule, solved_puzzles, time, points) for subrule in subrules)
            
        case Or():
            # Get all items that aren't strings (skip parentheses, OR, commas)
            subrules = [r for r in rule if not isinstance(r, str)]
            return any(check_rule(subrule, solved_puzzles, time, points) for subrule in subrules)
            
        case SomeOf():
            # Get the number and the list of items
            num = rule.num
            # Get all items that aren't strings (skip OF, parentheses, commas)
            subrules = [r for r in rule if not isinstance(r, str) and not isinstance(r, int)]
            return sum(1 for r in subrules if check_rule(r, solved_puzzles, time, points)) >= int(num)
            
        case PuzzleID():
            return rule.id in solved_puzzles
            
        case TimeSinceStart():
            parts = rule.time.split(":")
            return time >= timedelta(hours=int(parts[0]), minutes=int(parts[1]))
            
        case NumPoints():
            return points >= int(rule.points)
            
        case TimeInterval():
            return True  # Time intervals are handled differently
            
        case _:
            raise ValueError(f"Unknown rule type: {type(rule)} - {rule}")

def process_config_rules(rules, solved_puzzles, time):
    points = 0
    hints = 0
    unlocked_puzzles = set()
    processed_rules = set()
    
    def process_reward(rule, item_type, value):
        rule_id = (str(rule.rule), item_type, value)
        if rule_id not in processed_rules:
            if isinstance(rule.rule, TimeInterval):
                interval = int(rule.rule.interval)
                if rule.rule.unit.unit.upper().startswith("HOUR"):
                    interval *= 60
                # Convert total timedelta to minutes
                total_minutes = int(time.total_seconds() / 60)
                reward = total_minutes * int(value) // interval
            else:
                reward = int(value)
            processed_rules.add(rule_id)
            return reward, True
        return 0, False

    # Keep processing rules until no new changes occur
    changed = True
    while changed:
        changed = False
        for rule in rules:
            if check_rule(rule.rule, solved_puzzles, time, points):
                unlockables = [rule.unlockable] if not isinstance(rule.unlockable, List) else rule.unlockable
                for item in unlockables:
                    match item:
                        case PuzzleID():
                            if item.id not in unlocked_puzzles:
                                unlocked_puzzles.add(item.id)
                                changed = True
                        case NumPoints():
                            reward, was_changed = process_reward(rule, "points", item.points)
                            points += reward
                            changed = changed or was_changed
                        case NumHints():
                            reward, was_changed = process_reward(rule, "hints", item.hints)
                            hints += reward
                            changed = changed or was_changed

    return unlocked_puzzles, points, hints