"""Pure logic tests for the family timeline -- age computation and cross-generational
timing-pattern detection, using synthetic data chosen by hand."""

from datetime import date

from app.timeline import EventInput, compute_age_at_event, detect_timing_patterns, get_life_event_types


def test_life_event_types_from_config():
    types = get_life_event_types()
    assert "marriage" in types
    assert "other" in types


def test_compute_age_at_event_before_birthday_in_event_year():
    # Born June 10; event on Jan 1 the year they turn 30 -- birthday hasn't
    # happened yet that year, so they're still 29.
    assert compute_age_at_event(date(1955, 6, 10), date(1985, 1, 1)) == 29


def test_compute_age_at_event_on_birthday():
    assert compute_age_at_event(date(1955, 6, 10), date(1985, 6, 10)) == 30


def test_compute_age_at_event_after_birthday_in_event_year():
    assert compute_age_at_event(date(1955, 6, 10), date(1985, 12, 25)) == 30


def test_same_event_type_and_age_across_people_is_a_pattern():
    events = [
        EventInput(person_name="Grandparent", event_type="marriage", age_at_event=24),
        EventInput(person_name="Parent", event_type="marriage", age_at_event=24),
    ]
    patterns = detect_timing_patterns(events)
    assert len(patterns) == 1
    assert patterns[0].event_type == "marriage"
    assert patterns[0].age_at_event == 24
    assert set(patterns[0].people) == {"Grandparent", "Parent"}
    assert patterns[0].occurrence_count == 2


def test_same_event_type_different_age_is_not_a_pattern():
    events = [
        EventInput(person_name="A", event_type="marriage", age_at_event=24),
        EventInput(person_name="B", event_type="marriage", age_at_event=27),
    ]
    assert detect_timing_patterns(events) == []


def test_same_age_different_event_type_is_not_a_pattern():
    events = [
        EventInput(person_name="A", event_type="marriage", age_at_event=24),
        EventInput(person_name="B", event_type="career_change", age_at_event=24),
    ]
    assert detect_timing_patterns(events) == []


def test_one_person_with_two_matching_events_is_not_double_counted():
    # Same person, same event_type and age twice (e.g. logged in error, or two
    # career changes at the same age) should count as one person, not a pattern
    # with occurrence_count 2 from a single individual.
    events = [
        EventInput(person_name="A", event_type="career_change", age_at_event=30),
        EventInput(person_name="A", event_type="career_change", age_at_event=30),
    ]
    assert detect_timing_patterns(events) == []


def test_three_person_pattern_reports_full_occurrence_count():
    events = [
        EventInput(person_name="A", event_type="death_of_parent", age_at_event=47),
        EventInput(person_name="B", event_type="death_of_parent", age_at_event=47),
        EventInput(person_name="C", event_type="death_of_parent", age_at_event=47),
    ]
    patterns = detect_timing_patterns(events)
    assert len(patterns) == 1
    assert patterns[0].occurrence_count == 3
