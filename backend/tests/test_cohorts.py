"""Pure logic tests for the generational cohort lens -- synthetic sign data chosen
by hand so cohort grouping is verifiable by inspection."""

from app.cohorts import PersonInput, aggregate_generational_cohorts, generational_planets


def _planets(**by_planet: str) -> list[dict]:
    return [{"name": name, "sign": sign} for name, sign in by_planet.items()]


def test_generational_planets_from_config():
    assert generational_planets() == ["Uranus", "Neptune", "Pluto"]


def test_only_generational_planets_are_grouped():
    people = [PersonInput(name="A", planets=_planets(Sun="Aries", Pluto="Scorpio"))]
    report = aggregate_generational_cohorts(people)
    assert {pc.planet for pc in report.cohorts_by_planet} == {"Uranus", "Neptune", "Pluto"}


def test_people_sharing_a_sign_form_one_cohort():
    people = [
        PersonInput(name="SiblingA", planets=_planets(Pluto="Scorpio")),
        PersonInput(name="SiblingB", planets=_planets(Pluto="Scorpio")),
        PersonInput(name="Parent", planets=_planets(Pluto="Libra")),
    ]
    report = aggregate_generational_cohorts(people)
    pluto = next(pc for pc in report.cohorts_by_planet if pc.planet == "Pluto")

    assert pluto.distinct_cohort_count == 2
    cohorts_by_sign = {c.sign: set(c.people) for c in pluto.cohorts}
    assert cohorts_by_sign == {
        "Scorpio": {"SiblingA", "SiblingB"},
        "Libra": {"Parent"},
    }


def test_cohorts_sorted_largest_first():
    people = [
        PersonInput(name="A", planets=_planets(Uranus="Cancer")),
        PersonInput(name="B", planets=_planets(Uranus="Cancer")),
        PersonInput(name="C", planets=_planets(Uranus="Sagittarius")),
    ]
    report = aggregate_generational_cohorts(people)
    uranus = next(pc for pc in report.cohorts_by_planet if pc.planet == "Uranus")
    assert [c.sign for c in uranus.cohorts] == ["Cancer", "Sagittarius"]


def test_singleton_cohort_is_still_reported():
    # Unlike the thread detector, a cohort of exactly one person is meaningful --
    # the lens compares cohorts across generations, it doesn't require recurrence.
    people = [PersonInput(name="OnlyPerson", planets=_planets(Pluto="Leo"))]
    report = aggregate_generational_cohorts(people)
    pluto = next(pc for pc in report.cohorts_by_planet if pc.planet == "Pluto")
    assert pluto.distinct_cohort_count == 1
    assert pluto.cohorts[0].people == ["OnlyPerson"]


def test_person_missing_a_planet_is_simply_excluded_from_its_cohorts():
    people = [
        PersonInput(name="Full", planets=_planets(Uranus="Cancer", Neptune="Libra", Pluto="Leo")),
        PersonInput(name="MissingPluto", planets=_planets(Uranus="Cancer", Neptune="Libra")),
    ]
    report = aggregate_generational_cohorts(people)
    pluto = next(pc for pc in report.cohorts_by_planet if pc.planet == "Pluto")
    assert pluto.cohorts[0].people == ["Full"]
