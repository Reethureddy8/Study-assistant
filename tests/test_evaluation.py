from parishiksha.config import SETTINGS
from parishiksha.evaluation import EVAL_SET, read_csv, summarize


def test_eval_set_shape():
    categories = [q["category"] for q in EVAL_SET]
    assert categories.count("direct") == 6
    assert categories.count("paraphrased") == 3
    assert categories.count("out_of_scope") == 3
    assert [q["id"] for q in EVAL_SET] == list(range(1, 13))


def test_summary_matches_documented_v1_and_v2_results():
    v1 = summarize(read_csv(SETTINGS.evaluation_dir / "eval_scored.csv"))
    v2 = summarize(read_csv(SETTINGS.evaluation_dir / "eval_v2_scored.csv"))
    assert (v1["correct"], v1["partial"], v1["grounded"], v1["refused"]) == (8, 1, 9, 3)
    assert (v2["correct"], v2["partial"], v2["grounded"], v2["refused"]) == (7, 1, 8, 3)
