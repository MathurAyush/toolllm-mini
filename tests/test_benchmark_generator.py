import json
import random

import pytest

from agent.llm import EchoLLM
from apis.registry import keyless_registry
from eval.benchmark_generator import (
    EXCLUDED_TOOLS,
    Candidate,
    TaskFilter,
    TaskRejected,
    assign_splits,
    build_prompt,
    check_answer,
    difficulty_of,
    fact_in_text,
    generate_benchmark,
    is_dependent,
    parse_candidates,
    read_jsonl,
    run_plan,
    sample_tool_group,
    tool_pool,
    write_jsonl,
)

REGISTRY = keyless_registry()


def _candidate(instruction, plan, answer_path, facts=(), tools=None):
    return Candidate(
        instruction=instruction,
        relevant_tools=tools if tools is not None else sorted({s["tool"] for s in plan}),
        plan=plan,
        answer_path=answer_path,
        expected_facts=list(facts),
    )


GEOCODE_ELEVATION = [
    {"tool": "geocode", "args": {"place": "Berlin"}},
    {"tool": "elevation", "args": {"latitude": "{s1.latitude}", "longitude": "{s1.longitude}"}},
]


# ---------------------------------------------------------------- sampling


def test_tool_pool_leaves_out_unverifiable_tools():
    pool = tool_pool(REGISTRY)
    assert "geocode" in pool and "crypto_price" in pool
    assert not EXCLUDED_TOOLS & set(pool)


@pytest.mark.parametrize("size", [1, 2, 3])
def test_sample_tool_group_returns_distinct_pool_tools(size):
    rng = random.Random(size)
    for _ in range(20):
        group = sample_tool_group(rng, REGISTRY, size)
        assert len(group) == size == len(set(group))
        assert set(group) <= set(tool_pool(REGISTRY))


def test_sample_tool_group_is_reproducible_from_seed():
    first = [sample_tool_group(random.Random(7), REGISTRY, 3) for _ in range(5)]
    second = [sample_tool_group(random.Random(7), REGISTRY, 3) for _ in range(5)]
    assert first == second


def test_build_prompt_includes_registry_entries_and_difficulty():
    prompt = build_prompt(REGISTRY, ["geocode", "elevation"], "hard", 3, "2026-10-28")
    assert '"name": "geocode"' in prompt and '"elevation_m"' in prompt
    assert "use the output" in prompt and "2026-10-28" in prompt


# ---------------------------------------------------------------- parsing


def test_parse_candidates_reads_fenced_json_and_skips_malformed_items():
    reply = "Here you go:\n```json\n" + json.dumps(
        [
            {"instruction": "  How high is   Berlin? ", "relevant_tools": ["geocode"], "plan": [], "answer_path": "s1"},
            {"instruction": "", "plan": []},
            "not an object",
            {"instruction": "no plan"},
        ]
    ) + "\n```"
    candidates = parse_candidates(reply)
    assert [c.instruction for c in candidates] == ["How high is Berlin?"]


def test_parse_candidates_returns_nothing_for_invalid_json():
    assert parse_candidates("[{not json}]") == []
    assert parse_candidates("no array here") == []


# ---------------------------------------------------------------- execution


def test_run_plan_resolves_placeholders_from_earlier_steps():
    results = run_plan(REGISTRY, GEOCODE_ELEVATION)
    assert results[1]["elevation_m"] == 7533.0


def test_run_plan_substitutes_placeholders_inside_strings():
    plan = [
        {"tool": "crypto_price", "args": {"coin": "bitcoin"}},
        {"tool": "calculator", "args": {"expression": "{s1.price} * 2"}},
    ]
    assert run_plan(REGISTRY, plan)[1] == 81670 * 2


@pytest.mark.parametrize(
    "plan, reason",
    [
        ([], "empty plan"),
        ([{"tool": "teleport", "args": {}}], "unknown tool"),
        ([{"tool": "geocode", "args": {}}], "bad arguments"),
        ([{"tool": "geocode", "args": {"place": "Berlin", "zoom": 3}}], "bad arguments"),
        ([{"tool": "elevation", "args": {"latitude": "{s1.latitude}", "longitude": 1}}], "not run yet"),
        ([{"tool": "geocode", "args": {"place": "x"}}, {"tool": "calculator", "args": {"expression": "{s1.nope}"}}], "not in the tool output"),
        ([{"tool": "calculator", "args": {"expression": "1 / 0"}}], "calculator failed"),
    ],
)
def test_run_plan_rejects_plans_that_cannot_complete(plan, reason):
    with pytest.raises(TaskRejected, match=reason):
        run_plan(REGISTRY, plan)


def test_is_dependent_detects_chained_calls():
    assert is_dependent(GEOCODE_ELEVATION)
    assert not is_dependent([{"tool": "geocode", "args": {"place": "Berlin"}}, {"tool": "calculator", "args": {"expression": "2+2"}}])


@pytest.mark.parametrize(
    "tools, plan, expected",
    [
        (["geocode"], [{"tool": "geocode", "args": {}}], "easy"),
        (["calculator", "geocode"], [{"tool": "geocode", "args": {}}, {"tool": "calculator", "args": {}}], "medium"),
        (["elevation", "geocode"], GEOCODE_ELEVATION, "hard"),
        (["a", "b", "c"], [], "hard"),
    ],
)
def test_difficulty_of(tools, plan, expected):
    assert difficulty_of(tools, plan) == expected


# ---------------------------------------------------------------- facts


@pytest.mark.parametrize(
    "fact, text, expected",
    [
        ("Tokyo", "The capital is tokyo.", True),
        ("New Year's Day", "new years day is first", False),
        ("1949", "first published in 1949", True),
        ("1949", "first published in 1950", False),
        ("7533", "about 7,533.0 m", True),
        ("16.09344", "roughly 16.09 km", True),
        ("Tok", "Tokyo", False),
    ],
)
def test_fact_in_text(fact, text, expected):
    assert fact_in_text(fact, text) is expected


# ---------------------------------------------------------------- filtering


def test_filter_accepts_static_task_with_answer_value_as_fact():
    task = TaskFilter(REGISTRY).check(
        _candidate("How high above sea level is Berlin?", GEOCODE_ELEVATION, "s2.elevation_m", ["Germany"])
    )
    assert task["difficulty"] == "hard"
    assert task["expected_tools"] == ["elevation", "geocode"]
    assert task["expected_facts"] == ["7533", "Germany"]
    assert "expected_value" not in task


def test_filter_stores_check_rule_for_live_tasks():
    plan = [{"tool": "crypto_price", "args": {"coin": "bitcoin"}}]
    task = TaskFilter(REGISTRY).check(_candidate("What is bitcoin worth in dollars?", plan, "s1.price"))
    rule = task["expected_value"]
    assert rule["check"] == "within 5% of the live tool result"
    assert (rule["rule"], rule["tolerance"]) == ("relative", 0.05)
    assert rule["plan"] == plan and rule["value_at_generation"] == 81670
    assert "expected_facts" not in task


def test_filter_uses_absolute_tolerance_for_weather():
    plan = [{"tool": "weather_forecast", "args": {"latitude": 52.52, "longitude": 13.41}}]
    task = TaskFilter(REGISTRY).check(_candidate("How warm will Berlin get today?", plan, "s1.days.0.temp_max_c"))
    assert task["expected_value"]["check"] == "within 3 units of the live tool result"


def test_filter_rejects_live_task_without_numeric_answer():
    plan = [{"tool": "crypto_price", "args": {"coin": "bitcoin"}}]
    with pytest.raises(TaskRejected, match="not a number"):
        TaskFilter(REGISTRY).check(_candidate("Which coin is this?", plan, "s1.coin"))


@pytest.mark.parametrize(
    "candidate, reason",
    [
        (_candidate("Where is Berlin?", [{"tool": "geocode", "args": {"place": "Berlin"}}], "s1.country", tools=["geocoder"]), "nonexistent tools"),
        (_candidate("Run city_lookup_v2 on Berlin", [{"tool": "geocode", "args": {"place": "Berlin"}}], "s1.country"), "nonexistent tools"),
        (_candidate("Where is Berlin?", [{"tool": "geocode", "args": {"place": "Berlin"}}], "s1.country", tools=["geocode", "elevation"]), "do not match the plan"),
        (_candidate("Tell me a joke", [{"tool": "joke", "args": {}}], "s1.joke"), "unverifiable"),
        (_candidate("Where is Berlin?", [{"tool": "geocode", "args": {"place": "Berlin"}}], "s1.country", ["France"]), "not in the tool output"),
        (_candidate("Which country is Berlin in, Germany?", [{"tool": "geocode", "args": {"place": "Berlin"}}], "s1.country"), "not in the tool output"),
        (_candidate("What is Berlin's timezone?", [{"tool": "geocode", "args": {"place": "Berlin"}}], "s1.days"), "not in the tool output"),
    ],
)
def test_filter_rejects_bad_candidates(candidate, reason):
    with pytest.raises(TaskRejected, match=reason):
        TaskFilter(REGISTRY).check(candidate)


def test_filter_requires_a_fact_from_the_answer():
    plan = [{"tool": "zip_code_lookup", "args": {"postal_code": "90210", "country_code": "us"}}]
    # The answer is a list, so only the model's facts can be checked.
    task = TaskFilter(REGISTRY).check(_candidate("Which town has ZIP code 90210?", plan, "s1.places", ["Beverly Hills"]))
    assert task["expected_facts"] == ["Beverly Hills"]
    # "United States" is in the output, but not in the places the request asks for.
    with pytest.raises(TaskRejected, match="answer at s1.places"):
        TaskFilter(REGISTRY).check(_candidate("Which town has ZIP code 90210?", plan, "s1.places", ["United States"]))


def test_filter_rejects_duplicates():
    task_filter = TaskFilter(REGISTRY)
    task_filter.check(_candidate("How high above sea level is Berlin?", GEOCODE_ELEVATION, "s2.elevation_m"))
    with pytest.raises(TaskRejected, match="duplicate plan"):
        task_filter.check(_candidate("What is the altitude of the city of Berlin?", GEOCODE_ELEVATION, "s2.elevation_m"))
    other_plan = [
        {"tool": "geocode", "args": {"place": "Berlin, Germany"}},
        {"tool": "elevation", "args": {"latitude": "{s1.latitude}", "longitude": "{s1.longitude}"}},
    ]
    with pytest.raises(TaskRejected, match="duplicate instruction"):
        task_filter.check(_candidate("How high above sea level is Berlin??", other_plan, "s2.elevation_m"))


# ---------------------------------------------------------------- grading


def test_check_answer_with_expected_facts():
    task = {"expected_facts": ["7533", "Germany"]}
    assert check_answer(task, "Berlin, Germany sits at 7,533 m.", REGISTRY)
    assert not check_answer(task, "Berlin sits at 7,533 m.", REGISTRY)


def test_check_answer_reruns_plan_for_live_value():
    plan = [{"tool": "crypto_price", "args": {"coin": "bitcoin"}}]
    task = TaskFilter(REGISTRY).check(_candidate("What is bitcoin worth in dollars?", plan, "s1.price"))
    assert check_answer(task, "Bitcoin trades at about $83,000.", REGISTRY)
    assert not check_answer(task, "Bitcoin trades at about $90,000.", REGISTRY)
    assert not check_answer(task, "I could not find the price.", REGISTRY)


# ---------------------------------------------------------------- generation


def _reply(*items):
    return json.dumps([{"relevant_tools": sorted({s["tool"] for s in i[1]}), "instruction": i[0], "plan": i[1], "answer_path": i[2]} for i in items])


SCRIPTED_REPLIES = [
    _reply(
        ("Where is Berlin located?", [{"tool": "geocode", "args": {"place": "Berlin"}}], "s1.country"),
        ("What is bitcoin worth right now?", [{"tool": "crypto_price", "args": {"coin": "bitcoin"}}], "s1.price"),
        ("Where is Berlin located, please?", [{"tool": "geocode", "args": {"place": "Berlin"}}], "s1.country"),
    ),
    _reply(
        (
            "Which country is Berlin in, and how much does Pikachu weigh?",
            [{"tool": "geocode", "args": {"place": "Berlin"}}, {"tool": "pokemon_info", "args": {"pokemon": "pikachu"}}],
            "s2.weight_kg",
        ),
        ("How high above sea level is Berlin?", GEOCODE_ELEVATION, "s2.elevation_m"),
    ),
]


def test_generate_benchmark_labels_ids_and_splits():
    llm = EchoLLM(responses=SCRIPTED_REPLIES, default_response="[]")
    tasks, stats = generate_benchmark(llm, REGISTRY, per_difficulty=2, seed=3, max_rounds=4)

    assert [t["id"] for t in tasks] == [f"gen-{i:03d}" for i in range(1, len(tasks) + 1)]
    assert [t["difficulty"] for t in tasks] == ["easy", "easy", "medium", "hard"]
    assert all(t["split"] in {"dev", "test"} for t in tasks)
    assert all(("expected_facts" in t) != ("expected_value" in t) for t in tasks)
    assert list(tasks[0]) == ["id", "instruction", "difficulty", "expected_tools", "expected_facts", "split"]
    assert stats.llm_calls == 4 and stats.rejected["duplicate plan"] == 1


def test_generate_benchmark_survives_model_errors():
    class FailingLLM(EchoLLM):
        def generate(self, prompt):
            raise RuntimeError("quota exceeded")

    tasks, stats = generate_benchmark(FailingLLM(), REGISTRY, per_difficulty=1, max_rounds=2)
    assert tasks == [] and stats.llm_calls == 2


def test_assign_splits_is_seeded_and_stratified():
    tasks = [{"difficulty": d, "n": i} for d in ("easy", "medium", "hard") for i in range(10)]
    first = [dict(t) for t in tasks]
    second = [dict(t) for t in tasks]
    assign_splits(first, seed=1)
    assign_splits(second, seed=1)
    assert [t["split"] for t in first] == [t["split"] for t in second]
    for difficulty in ("easy", "medium", "hard"):
        splits = [t["split"] for t in first if t["difficulty"] == difficulty]
        assert splits.count("test") == 7 and splits.count("dev") == 3


def test_jsonl_round_trip(tmp_path):
    tasks = [{"id": "gen-001", "instruction": "Où est Berlin?", "difficulty": "easy"}]
    path = tmp_path / "benchmark.jsonl"
    write_jsonl(tasks, path)
    assert read_jsonl(path) == tasks
