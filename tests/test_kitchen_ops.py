from doobielogic.department_parsers import parse_department_file
from doobielogic.kitchen_ops import build_kitchen_action_plan
from doobielogic.parser import load_csv_bytes


def test_kitchen_ops_outputs_non_empty():
    rows = load_csv_bytes(open("data/sample_kitchen_ops.csv", "rb").read())
    parsed = parse_department_file(rows, "kitchen")
    out = build_kitchen_action_plan(parsed)
    assert out["actions"]
