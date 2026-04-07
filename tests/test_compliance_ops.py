from doobielogic.compliance_ops import build_compliance_action_plan
from doobielogic.department_parsers import parse_department_file
from doobielogic.parser import load_csv_bytes


def test_compliance_ops_outputs_non_empty():
    rows = load_csv_bytes(open("data/sample_compliance_ops.csv", "rb").read())
    parsed = parse_department_file(rows, "compliance")
    out = build_compliance_action_plan(parsed, state="CA")
    assert out["actions"]
    assert out["legal_notice"]
