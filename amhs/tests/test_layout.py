from amhs import STATION_ORDER, distance_between, next_station, travel_time_seconds


def test_next_station_wraps_around():
    last = STATION_ORDER[-1]
    assert next_station(last) == STATION_ORDER[0]


def test_next_station_is_sequential():
    for i, station in enumerate(STATION_ORDER[:-1]):
        assert next_station(station) == STATION_ORDER[i + 1]


def test_distance_same_station_is_zero():
    assert distance_between(STATION_ORDER[0], STATION_ORDER[0]) == 0.0


def test_distance_is_positive_forward():
    assert distance_between(STATION_ORDER[0], STATION_ORDER[1]) > 0


def test_travel_time_scales_with_distance():
    a, b, c = STATION_ORDER[0], STATION_ORDER[1], STATION_ORDER[2]
    assert travel_time_seconds(a, c) > travel_time_seconds(a, b)


def test_travel_time_same_station_is_zero():
    assert travel_time_seconds(STATION_ORDER[0], STATION_ORDER[0]) == 0.0
