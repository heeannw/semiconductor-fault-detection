import numpy as np

from simulator.spc import capability_indices, capability_rating, i_mr_limits, western_electric_flags


def test_i_mr_limits_center_is_mean():
    rng = np.random.default_rng(0)
    values = rng.normal(50, 5, size=200)
    limits = i_mr_limits(values)
    assert limits["center"] == values.mean()
    assert limits["lcl"] < limits["center"] < limits["ucl"]
    assert limits["sigma_short"] > 0


def test_capability_indices_high_cpk_for_tight_process_in_wide_spec():
    rng = np.random.default_rng(1)
    values = rng.normal(50, 1, size=300)  # 아주 안정적인 공정
    limits = i_mr_limits(values)
    cap = capability_indices(values, low=0, high=100, sigma_short=limits["sigma_short"])
    assert cap["Cpk"] > 1.33  # 규격이 넓고 산포가 작으니 능력이 우수해야 한다


def test_capability_indices_low_cpk_for_off_center_process():
    rng = np.random.default_rng(2)
    values = rng.normal(95, 2, size=300)  # 상한(100)에 바짝 붙어 있음
    limits = i_mr_limits(values)
    cap = capability_indices(values, low=0, high=100, sigma_short=limits["sigma_short"])
    assert cap["Cpk"] < cap["Cp"]  # 중심을 벗어났으니 Cpk가 Cp보다 작아야 한다


def test_capability_rating_thresholds():
    assert capability_rating(1.5) == "우수"
    assert capability_rating(1.1) == "양호(관리 필요)"
    assert capability_rating(0.8) == "부적합"


def test_western_electric_flags_catches_point_beyond_3_sigma():
    values = np.array([50.0] * 20 + [200.0])  # 마지막 값이 명백한 이상치
    flags = western_electric_flags(values, center=50.0, sigma=2.0)
    assert flags[-1] == 1
    assert flags[:-1].sum() == 0


def test_western_electric_flags_catches_run_of_eight_same_side():
    values = np.array([51.0] * 8 + [50.0] * 12)  # 처음 8개가 중심선 위
    flags = western_electric_flags(values, center=50.0, sigma=1.0)
    assert flags[7] == 1  # 8개째에서 룰 4가 발동해야 한다


def test_western_electric_flags_no_signal_on_pure_noise():
    rng = np.random.default_rng(3)
    values = rng.normal(50, 1, size=100)
    limits = i_mr_limits(values)
    flags = western_electric_flags(values, limits["center"], limits["sigma_short"])
    # 순수 잡음이면 대부분 신호가 없어야 한다(약간의 우연한 발동은 허용)
    assert flags.mean() < 0.15
