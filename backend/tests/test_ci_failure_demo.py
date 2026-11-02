def test_deliberately_failing_test_for_s1_007_ci_evidence() -> None:
    assert {"status": "ok"} == {"status": "broken"}
