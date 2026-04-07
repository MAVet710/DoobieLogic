from doobielogic.department_router import detect_department_from_headers


def test_detect_department_from_headers():
    assert detect_department_from_headers(["room", "strain", "cycle_days"]) == "cultivation"
    assert detect_department_from_headers(["issue_id", "corrective_action_status", "open_days"]) == "compliance"
