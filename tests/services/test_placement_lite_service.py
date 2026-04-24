from types import SimpleNamespace

from src.services.placement_lite_service import select_placement_units


def test_select_placement_units_samples_evenly_across_available_units():
    units = [SimpleNamespace(canonical_unit_id=f"unit-{index}") for index in range(10)]

    selected = select_placement_units(units, max_units=4)

    assert [unit.canonical_unit_id for unit in selected] == ["unit-0", "unit-3", "unit-6", "unit-9"]
