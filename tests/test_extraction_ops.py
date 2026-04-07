from doobielogic.department_parsers import parse_department_file
from doobielogic.extraction_ops import build_extraction_action_plan
from doobielogic.parser import load_csv_bytes


def test_extraction_ops_outputs_non_empty():
    rows = load_csv_bytes(open("data/sample_extraction_ops.csv", "rb").read())
    parsed = parse_department_file(rows, "extraction")
    out = build_extraction_action_plan(parsed)
    assert out["actions"]
