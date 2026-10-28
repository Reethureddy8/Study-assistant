from parishiksha.ingest import classify_content_type, clean_text, split_into_sections


def test_classify_prefers_worked_example():
    assert classify_content_type("Activity 4.2: ... Example 4.1: a car starts") == "worked_example"


def test_classify_other_types():
    assert classify_content_type("Revise, reflect, refine") == "end_of_chapter"
    assert classify_content_type("Activity 6.1: Take a ball") == "activity"
    assert classify_content_type("Motion is change in position.") == "concept"


def test_clean_text_keeps_content_after_figure_caption():
    raw = "Speed is distance per time.\nFig. 4.3: A moving car\nVelocity has direction.\n12\n"
    assert clean_text(raw) == "Speed is distance per time. Velocity has direction."


def test_clean_text_strips_layout_noise():
    raw = "Chapter-4.indd 12 2026\n58 Exploration|Grade 9 58\nForce changes motion."
    assert clean_text(raw) == "Force changes motion."


def test_sections_carry_heading_forward():
    pages = [
        {"page": 1, "text": "Intro text"},
        {"page": 2, "text": "x\n4.1 Describing Position\nbody"},
        {"page": 3, "text": "more body"},
    ]
    sections = split_into_sections(pages, "Ch4")
    assert [s.section for s in sections] == ["Introduction", "4.1 Describing Position", "4.1 Describing Position"]
