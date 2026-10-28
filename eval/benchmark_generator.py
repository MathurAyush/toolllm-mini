"""Generates benchmark tasks from the tool catalog with an LLM.

Each round samples 1-3 related tools, shows the model their registry
entries, and asks it for realistic instructions that need them, the tools
each one needs, and a reference plan of tool calls. Every candidate is then
filtered: duplicates, instructions naming tools that do not exist, and tasks
whose plan does not run (unknown tool, bad arguments, a failing call, an
answer that is not in the tool output) are dropped. Survivors are labelled
by difficulty and get either `expected_facts` (strings a correct answer
must contain, each one checked against the real tool output) or, for
live-data tasks, an `expected_value` check rule that compares the answer
with a fresh run of the reference plan.
"""

from __future__ import annotations

import json
import random
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Callable

from agent.llm import BaseLLM
from apis.registry import APIRegistry

DIFFICULTIES = ("easy", "medium", "hard")

# Tools whose output is random or changes too fast to check an answer
# against (a random joke, the ISS position, the latest news).
EXCLUDED_TOOLS = frozenset(
    {
        "joke",
        "random_quote",
        "cat_fact",
        "dog_fact",
        "dog_image",
        "random_user",
        "random_recipe",
        "advice",
        "trivia_questions",
        "iss_location",
        "world_time",
        "recent_earthquakes",
        "spaceflight_news",
        "hacker_news_search",
        "news_headlines",
        "openweathermap",
    }
)

# Tools returning live numbers, with how far a later run may drift from the
# value seen at generation time.
LIVE_TOLERANCES: dict[str, tuple[str, float]] = {
    "currency_exchange": ("relative", 0.05),
    "crypto_price": ("relative", 0.05),
    "github_user": ("relative", 0.05),
    "weather_forecast": ("absolute", 3.0),
    "air_quality": ("absolute", 15.0),
}

# Producer -> consumers: the first tool's output can feed the second's input.
TOOL_LINKS: dict[str, tuple[str, ...]] = {
    "geocode": ("weather_forecast", "air_quality", "elevation", "sunrise_sunset"),
    "zip_code_lookup": ("weather_forecast", "air_quality", "elevation", "sunrise_sunset"),
    "ip_geolocation": ("weather_forecast", "air_quality", "elevation"),
    "country_info": ("currency_exchange", "historical_exchange_rate", "geocode", "wikipedia_summary"),
    "nationality_from_name": ("public_holidays", "long_weekends", "age_from_name"),
    "book_search": ("author_search", "wikipedia_summary"),
    "book_by_isbn": ("author_search", "book_search"),
    "author_search": ("book_search", "wikipedia_summary"),
    "crypto_price": ("calculator", "currency_exchange"),
    "currency_exchange": ("calculator",),
    "historical_exchange_rate": ("calculator",),
    "unit_conversion": ("calculator",),
    "elevation": ("unit_conversion", "calculator"),
    "weather_forecast": ("unit_conversion", "calculator"),
    "weather": ("unit_conversion",),
    "pokemon_info": ("unit_conversion", "calculator"),
    "github_user": ("calculator",),
    "near_earth_asteroids": ("unit_conversion", "calculator"),
    "dictionary": ("related_words",),
    "related_words": ("dictionary",),
    "public_holidays": ("long_weekends",),
    "university_search": ("country_info",),
    "search": ("wikipedia_summary", "geocode"),
}

_DIFFICULTY_GUIDE = {
    "easy": "Each instruction needs exactly one tool call.",
    "medium": (
        "Each instruction needs every listed tool, but the calls are independent: "
        "no call uses another call's output (e.g. two separate facts combined in one answer)."
    ),
    "hard": (
        "Each instruction needs every listed tool, and at least one call must use the output "
        "of an earlier call (e.g. look up coordinates, then use them)."
    ),
}

_PROMPT = """You are writing test tasks for a tool-using AI assistant.

Today's date is {today}.

Available tools (registry entries with an example call and its response):
{tools}

Write {n} different, realistic requests a user might type that need these tools.
{guide}

Rules:
- Write like a real user. Never mention tool names or say "use the X tool".
- Each request must be answerable from the tool outputs alone, with one clear answer.
- Use concrete arguments (real cities, words, coins, ISBNs, dates). Dates for
  historical lookups must be in the past.
- For each request give a reference plan: the tool calls, in order, with arguments.
  To pass an earlier result into a later call, write a placeholder
  {{sN.path}}, where N is the 1-based step number and path follows the keys or
  list indexes of that step's response, e.g. {{s1.latitude}} or
  {{s1.places.0.latitude}}. Placeholders can sit inside a string, e.g. a
  calculator expression "{{s1.price}} * 3".
- "answer_path" points at the value that answers the request, e.g. "s2.elevation_m".
- "expected_facts" lists 1-3 short strings (names, numbers, words) that a correct
  answer must contain, copied from what the tools would return.

Reply with only a JSON array, one object per request:
[{{"instruction": "...", "relevant_tools": ["..."], "plan": [{{"tool": "...", "args": {{}}}}],
  "answer_path": "s1....", "expected_facts": ["..."]}}]
"""

_PLACEHOLDER = re.compile(r"\{s(\d+)((?:\.[^.{}\s]+)+)\}")
_SNAKE_CASE = re.compile(r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b")
_NUMBER = re.compile(r"-?\d[\d,]*(?:\.\d+)?")
_WORD = re.compile(r"[a-z0-9]+")


class TaskRejected(Exception):
    """A generated candidate failed a filter; the message says which."""


@dataclass
class Candidate:
    instruction: str
    relevant_tools: list[str]
    plan: list[dict]
    answer_path: str
    expected_facts: list[str] = field(default_factory=list)


@dataclass
class GenerationStats:
    llm_calls: int = 0
    candidates: int = 0
    rejected: Counter = field(default_factory=Counter)


# ---------------------------------------------------------------- sampling


def tool_pool(registry: APIRegistry) -> list[str]:
    """Names of the registered tools whose answers can be checked."""
    return sorted(api.name for api in registry.all() if api.name not in EXCLUDED_TOOLS)


def _neighbours(name: str, pool: set[str], categories: dict[str, str]) -> list[str]:
    linked = set(TOOL_LINKS.get(name, ()))
    linked |= {src for src, dsts in TOOL_LINKS.items() if name in dsts}
    same_category = {t for t in pool if categories[t] == categories[name]}
    return sorted((linked | same_category) & pool - {name})


def sample_tool_group(
    rng: random.Random, registry: APIRegistry, size: int, attempts: int = 20
) -> list[str]:
    """Samples `size` related tools: each one after the first is linked to an
    earlier one (its output feeds the other's input, or the reverse) or shares
    its category. A walk that runs out of related tools starts over; after
    `attempts` the largest group found is returned."""
    pool = set(tool_pool(registry))
    categories = {name: registry.get(name).category for name in pool}
    starts = sorted(pool)
    best: list[str] = []
    for _ in range(attempts):
        group = [rng.choice(starts)]
        while len(group) < size:
            options = sorted({n for t in group for n in _neighbours(t, pool, categories)} - set(group))
            if not options:
                break
            group.append(rng.choice(options))
        if len(group) == size:
            return group
        best = max(best, group, key=len)
    return best


# ---------------------------------------------------------------- prompting


def build_prompt(registry: APIRegistry, tools: list[str], difficulty: str, n: int, today: str) -> str:
    entries = [registry.get(name).registry_entry() for name in tools]
    return _PROMPT.format(
        today=today,
        tools=json.dumps(entries, indent=1, default=str),
        n=n,
        guide=_DIFFICULTY_GUIDE[difficulty],
    )


def parse_candidates(text: str) -> list[Candidate]:
    """Reads the model's JSON array, skipping malformed entries. Tolerates a
    ```json fence or prose around the array."""
    start, end = text.find("["), text.rfind("]")
    if start == -1 or end <= start:
        return []
    try:
        items = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return []
    candidates = []
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        instruction = item.get("instruction")
        plan = item.get("plan")
        if not isinstance(instruction, str) or not instruction.strip() or not isinstance(plan, list):
            continue
        facts = item.get("expected_facts") or []
        candidates.append(
            Candidate(
                instruction=" ".join(instruction.split()),
                relevant_tools=[str(t) for t in item.get("relevant_tools") or []],
                plan=plan,
                answer_path=str(item.get("answer_path") or ""),
                expected_facts=[str(f).strip() for f in facts if str(f).strip()],
            )
        )
    return candidates


# ---------------------------------------------------------------- execution


def _lookup(results: list[Any], step: int, path: str) -> Any:
    if not 1 <= step <= len(results):
        raise TaskRejected(f"placeholder refers to step {step}, which has not run yet")
    value = results[step - 1]
    for key in filter(None, path.split(".")):
        if isinstance(value, list) and key.lstrip("-").isdigit() and -len(value) <= int(key) < len(value):
            value = value[int(key)]
        elif isinstance(value, dict) and key in value:
            value = value[key]
        else:
            raise TaskRejected(f"path s{step}{path} is not in the tool output")
    return value


def _resolve(arg: Any, results: list[Any]) -> Any:
    if not isinstance(arg, str):
        return arg
    whole = _PLACEHOLDER.fullmatch(arg.strip())
    if whole:
        return _lookup(results, int(whole.group(1)), whole.group(2))
    return _PLACEHOLDER.sub(lambda m: str(_lookup(results, int(m.group(1)), m.group(2))), arg)


def is_dependent(plan: list[dict]) -> bool:
    """True if any call takes an earlier call's output as an argument."""
    return any(
        isinstance(arg, str) and _PLACEHOLDER.search(arg)
        for step in plan
        for arg in (step.get("args") or {}).values()
    )


def run_plan(registry: APIRegistry, plan: list[dict]) -> list[Any]:
    """Runs a reference plan, resolving placeholders from earlier results.
    Raises TaskRejected on an unknown tool, bad arguments or a failed call."""
    if not plan:
        raise TaskRejected("empty plan")
    results: list[Any] = []
    for number, step in enumerate(plan, start=1):
        if not isinstance(step, dict):
            raise TaskRejected(f"step {number} is not an object")
        api = registry.get(str(step.get("tool")))
        if api is None:
            raise TaskRejected(f"unknown tool '{step.get('tool')}'")
        raw_args = step.get("args") or {}
        if not isinstance(raw_args, dict):
            raise TaskRejected(f"step {number} args are not an object")
        args = {name: _resolve(value, results) for name, value in raw_args.items()}
        schema = api.function_schema()["parameters"]
        unknown = set(args) - set(schema["properties"])
        missing = set(schema["required"]) - set(args)
        if unknown or missing:
            raise TaskRejected(f"bad arguments for {api.name}: unknown {sorted(unknown)}, missing {sorted(missing)}")
        try:
            response = api.call(**args)
        except Exception as exc:  # a wrapper that raises instead of failing cleanly
            raise TaskRejected(f"{api.name} raised {exc!r}") from None
        if not response.success:
            raise TaskRejected(f"{api.name} failed: {response.error}")
        results.append(response.data)
    return results


def answer_value(results: list[Any], answer_path: str) -> Any:
    match = re.fullmatch(r"s(\d+)((?:\.[^.\s]+)*)", answer_path.strip())
    if not match:
        raise TaskRejected(f"bad answer_path '{answer_path}'")
    return _lookup(results, int(match.group(1)), match.group(2))


# ---------------------------------------------------------------- checking


def _normalize(text: str) -> str:
    return " ".join(_WORD.findall(text.lower()))


def _numbers(text: str) -> list[float]:
    values = []
    for token in _NUMBER.findall(text):
        try:
            values.append(float(token.replace(",", "")))
        except ValueError:
            continue
    return values


def _as_number(text: str) -> float | None:
    found = _NUMBER.fullmatch(text.strip().rstrip("%"))
    return float(found.group(0).replace(",", "")) if found else None


def _decimals(token: str) -> int:
    return len(token.split(".")[1]) if "." in token else 0


def _same_number(a: str, b: str) -> bool:
    """True if two numbers agree once the more precise one is rounded to the
    other's precision, so 16.09 matches 16.09344 but 1949 does not match
    1950."""
    x, y = float(a.replace(",", "")), float(b.replace(",", ""))
    return round(x, _decimals(b)) == round(y, _decimals(b)) or round(y, _decimals(a)) == round(x, _decimals(a))


def fact_in_text(fact: str, text: str) -> bool:
    """True if `fact` appears in `text`: as words (case and punctuation
    ignored), or, for a number, as a number in the text that agrees with it
    up to rounding (7533 matches 7533.0, 16.09 matches 16.09344)."""
    if _as_number(fact) is not None:
        token = fact.strip().rstrip("%")
        return any(_same_number(token, other) for other in _NUMBER.findall(text))
    needle = _normalize(fact)
    return bool(needle) and f" {needle} " in f" {_normalize(text)} "


def within_tolerance(value: float, reference: float, rule: str, tolerance: float) -> bool:
    if rule == "relative":
        return abs(value - reference) <= tolerance * abs(reference)
    return abs(value - reference) <= tolerance


def check_answer(task: dict, answer: str, registry: APIRegistry) -> bool:
    """Grades an answer against a benchmark task: every expected fact must
    appear in it, or, for a live-data task, some number in it must be within
    the stored tolerance of a fresh run of the reference plan."""
    if "expected_facts" in task:
        return all(fact_in_text(fact, answer) for fact in task["expected_facts"])
    rule = task["expected_value"]
    try:
        reference = float(answer_value(run_plan(registry, rule["plan"]), rule["answer_path"]))
    except (TaskRejected, TypeError, ValueError):
        return False
    return any(within_tolerance(n, reference, rule["rule"], rule["tolerance"]) for n in _numbers(answer))


# ---------------------------------------------------------------- filtering


def difficulty_of(tools: list[str], plan: list[dict]) -> str:
    if len(set(tools)) >= 3 or is_dependent(plan):
        return "hard"
    return "medium" if len(set(tools)) == 2 else "easy"


def _signature(candidate: Candidate) -> str:
    return json.dumps(
        [[step.get("tool"), step.get("args")] for step in candidate.plan], sort_keys=True, default=str
    ).lower()


def _similar(a: str, b: str, threshold: float = 0.8) -> bool:
    words_a, words_b = set(_normalize(a).split()), set(_normalize(b).split())
    if not words_a or not words_b:
        return False
    return len(words_a & words_b) / len(words_a | words_b) >= threshold


class TaskFilter:
    """Validates candidates and remembers accepted ones for de-duplication."""

    def __init__(self, registry: APIRegistry) -> None:
        self._registry = registry
        self._tool_names = {api.name for api in registry.all()}
        self._instructions: list[str] = []
        self._signatures: set[str] = set()

    def check(self, candidate: Candidate) -> dict:
        """Returns the finished task (without id and split) or raises
        TaskRejected."""
        self._check_duplicate(candidate)
        self._check_tool_names(candidate)

        plan_tools = sorted({str(step.get("tool")) for step in candidate.plan if isinstance(step, dict)})
        if sorted(set(candidate.relevant_tools)) != plan_tools:
            raise TaskRejected(
                f"listed tools {sorted(set(candidate.relevant_tools))} do not match the plan {plan_tools}"
            )
        if any(tool in EXCLUDED_TOOLS for tool in plan_tools):
            raise TaskRejected("uses a tool with unverifiable output")

        results = run_plan(self._registry, candidate.plan)
        value = answer_value(results, candidate.answer_path)
        task: dict[str, Any] = {
            "instruction": candidate.instruction,
            "difficulty": difficulty_of(plan_tools, candidate.plan),
            "expected_tools": plan_tools,
        }

        live = [tool for tool in plan_tools if tool in LIVE_TOLERANCES]
        if live:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TaskRejected(f"live answer {value!r} is not a number")
            rule, tolerance = _loosest(live)
            unit = "%" if rule == "relative" else " units"
            amount = tolerance * 100 if rule == "relative" else tolerance
            task["expected_value"] = {
                "check": f"within {amount:g}{unit} of the live tool result",
                "rule": rule,
                "tolerance": tolerance,
                "plan": candidate.plan,
                "answer_path": candidate.answer_path,
                "value_at_generation": value,
            }
        else:
            task["expected_facts"] = self._grounded_facts(candidate, results, value)

        self._instructions.append(candidate.instruction)
        self._signatures.add(_signature(candidate))
        return task

    @staticmethod
    def _grounded_facts(candidate: Candidate, results: list[Any], value: Any) -> list[str]:
        """The answer value (when it is a single value) plus the model's
        facts. Each must appear in the tool output, at least one must come
        from the answer itself, and facts already given in the instruction
        or too short to mean anything are dropped."""
        facts = []
        for fact in [_fact_from_value(value), *candidate.expected_facts]:
            numeric = _as_number(fact) is not None
            if not fact or (not numeric and len(_normalize(fact)) < 3):
                continue
            if fact_in_text(fact, candidate.instruction) or any(fact_in_text(fact, f) for f in facts):
                continue
            facts.append(fact)
        outputs = json.dumps(results, default=str, ensure_ascii=False)
        ungrounded = [f for f in facts if not fact_in_text(f, outputs)]
        if not facts or ungrounded:
            raise TaskRejected(f"expected facts not in the tool output: {ungrounded or facts}")
        answer = json.dumps(value, default=str, ensure_ascii=False)
        if not any(fact_in_text(f, answer) for f in facts):
            raise TaskRejected(f"no expected fact comes from the answer at {candidate.answer_path}")
        return facts

    def _check_duplicate(self, candidate: Candidate) -> None:
        if _signature(candidate) in self._signatures:
            raise TaskRejected("duplicate plan")
        if any(_similar(candidate.instruction, seen) for seen in self._instructions):
            raise TaskRejected("duplicate instruction")

    def _check_tool_names(self, candidate: Candidate) -> None:
        unknown = sorted(set(candidate.relevant_tools) - self._tool_names)
        if unknown:
            raise TaskRejected(f"nonexistent tools {unknown}")
        # A snake_case identifier in the text reads as a tool name.
        named = sorted(set(_SNAKE_CASE.findall(candidate.instruction)) - self._tool_names)
        if named:
            raise TaskRejected(f"instruction names nonexistent tools {named}")


def _loosest(tools: list[str]) -> tuple[str, float]:
    """The widest tolerance among the live tools in a plan, preferring an
    absolute one (a temperature near zero has no meaningful percentage)."""
    rules = [LIVE_TOLERANCES[t] for t in tools]
    absolute = [r for r in rules if r[0] == "absolute"]
    return max(absolute or rules, key=lambda r: r[1])


def _fact_from_value(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.2f}".rstrip("0").rstrip(".")
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    # A long text answer (an article summary) is never reproduced verbatim.
    if isinstance(value, str) and len(value) <= 60:
        return value.strip()
    return ""


# ---------------------------------------------------------------- generation


def assign_splits(tasks: list[dict], seed: int, test_fraction: float = 0.7) -> None:
    """Assigns each task to "dev" or "test" with a seeded shuffle, separately
    per difficulty so both splits keep the same mix."""
    rng = random.Random(seed)
    for difficulty in DIFFICULTIES:
        group = [t for t in tasks if t["difficulty"] == difficulty]
        rng.shuffle(group)
        n_test = round(len(group) * test_fraction)
        for i, task in enumerate(group):
            task["split"] = "test" if i < n_test else "dev"


def generate_benchmark(
    llm: BaseLLM,
    registry: APIRegistry,
    per_difficulty: int = 22,
    seed: int = 0,
    per_prompt: int = 4,
    max_rounds: int = 60,
    today: str = "",
    log: Callable[[str], None] = lambda _: None,
) -> tuple[list[dict], GenerationStats]:
    """Generates up to `per_difficulty` tasks of each difficulty.

    The tool groups and the split are drawn from `seed`, so a run is
    reproducible up to the model's own sampling.
    """
    rng = random.Random(seed)
    task_filter = TaskFilter(registry)
    buckets: dict[str, list[dict]] = {d: [] for d in DIFFICULTIES}
    stats = GenerationStats()

    for _ in range(max_rounds):
        missing = [d for d in DIFFICULTIES if len(buckets[d]) < per_difficulty]
        if not missing:
            break
        target = missing[0] if len(missing) == 1 else rng.choice(missing)
        size = {"easy": 1, "medium": 2, "hard": rng.choice((2, 3))}[target]
        tools = sample_tool_group(rng, registry, size)
        stats.llm_calls += 1
        log(f"[{target}] {', '.join(tools)}")
        try:
            reply = llm.generate(build_prompt(registry, tools, target, per_prompt, today)).text or ""
        except Exception as exc:
            log(f"  model call failed: {exc!r}")
            continue
        for candidate in parse_candidates(reply):
            stats.candidates += 1
            try:
                task = task_filter.check(candidate)
            except TaskRejected as exc:
                stats.rejected[str(exc).split(":")[0]] += 1
                log(f"  - rejected ({exc}): {candidate.instruction}")
                continue
            if len(buckets[task["difficulty"]]) >= per_difficulty:
                stats.rejected["difficulty already full"] += 1
                continue
            buckets[task["difficulty"]].append(task)
            log(f"  + {task['difficulty']}: {candidate.instruction}")

    tasks = [task for d in DIFFICULTIES for task in buckets[d]]
    for number, task in enumerate(tasks, start=1):
        task["id"] = f"gen-{number:03d}"
    assign_splits(tasks, seed)
    return [_ordered(task) for task in tasks], stats


_FIELD_ORDER = ("id", "instruction", "difficulty", "expected_tools", "expected_facts", "expected_value", "split")


def _ordered(task: dict) -> dict:
    return {key: task[key] for key in _FIELD_ORDER if key in task}


def write_jsonl(tasks: list[dict], path) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for task in tasks:
            f.write(json.dumps(task, ensure_ascii=False) + "\n")


def read_jsonl(path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]
