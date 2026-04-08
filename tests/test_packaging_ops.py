from doobielogic.department_parsers import parse_department_file
from doobielogic.packaging_ops import build_packaging_action_plan
from doobielogic.parser import load_csv_bytes


def test_packaging_ops_outputs_non_empty():
    rows = load_csv_bytes(open("data/sample_packaging_ops.csv", "rb").read())
    parsed = parse_department_file(rows, "packaging")
    out = build_packaging_action_plan(parsed)
    assert out["actions"]
