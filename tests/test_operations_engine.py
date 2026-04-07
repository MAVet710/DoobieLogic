from doobielogic.department_parsers import parse_department_file
from doobielogic.operations_engine import build_operations_outputs
from doobielogic.parser import load_csv_bytes


def test_operations_engine_routes():
    rows = load_csv_bytes(open("data/sample_extraction_ops.csv", "rb").read())
    parsed = parse_department_file(rows, "extraction")
    out = build_operations_outputs(parsed, "extraction", state="CA")
    assert out["department"] == "extraction"
    assert out["knowledge_matches"]
    assert out["action_plan"]
