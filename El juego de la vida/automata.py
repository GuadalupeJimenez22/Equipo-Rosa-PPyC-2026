from dataclasses import dataclass, field
from typing import Set


@dataclass
class AutomataRule:
    born: Set[int]
    survive: Set[int]
    name: str = ""

    def should_survive(self, living_neighbors: int) -> bool:
        return living_neighbors in self.survive

    def should_reproduce(self, living_neighbors: int) -> bool:
        return living_neighbors in self.born

    @property
    def rule_string(self) -> str:
        b = "".join(str(n) for n in sorted(self.born))
        s = "".join(str(n) for n in sorted(self.survive))
        return f"B{b}/S{s}"

    def __str__(self) -> str:
        label = f" ({self.name})" if self.name else ""
        return f"{self.rule_string}{label}"


PRESETS: dict[str, AutomataRule] = {
    "conway":     AutomataRule({3}, {2, 3}, "Conway's Life"),
    "highlife":   AutomataRule({3, 6}, {2, 3}, "HighLife"),
    "seeds":      AutomataRule({2}, set(), "Seeds"),
    "maze":       AutomataRule({3}, {1, 2, 3, 4, 5}, "Maze"),
    "daynight":   AutomataRule({3, 6, 7, 8}, {3, 4, 6, 7, 8}, "Day & Night"),
    "replicator": AutomataRule({1, 3, 5, 7}, {1, 3, 5, 7}, "Replicator"),
    "morley":     AutomataRule({3, 6, 8}, {2, 4, 5}, "Morley"),
    "diamoeba":   AutomataRule({3, 5, 6, 7, 8}, {5, 6, 7, 8}, "Diamoeba"),
    "2x2":        AutomataRule({3, 6}, {1, 2, 5}, "2x2"),
    "34life":     AutomataRule({3, 4}, {3, 4}, "34 Life"),
    "longlife":   AutomataRule({3,4,5}, {5}, "Long Life"),
}

PRESET_NAMES = list(PRESETS.keys())


def parse_rule(rule_string: str) -> AutomataRule:
    parts = rule_string.strip().upper().split("/")
    born = set()
    survive = set()
    for part in parts:
        if part.startswith("B"):
            born = {int(d) for d in part[1:]}
        elif part.startswith("S"):
            survive = {int(d) for d in part[1:]}
    if not born and not survive:
        parts = rule_string.strip().split("/")
        if len(parts) == 2:
            born = {int(d) for d in parts[0]}
            survive = {int(d) for d in parts[1]}
    return AutomataRule(born, survive, f"Custom ({rule_string})")


def get_rule(name_or_string: str) -> AutomataRule:
    if name_or_string in PRESETS:
        return PRESETS[name_or_string]
    return parse_rule(name_or_string)
