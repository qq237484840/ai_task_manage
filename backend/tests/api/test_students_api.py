"""API：学生档案（API-M001-004 创建 / 005 列表 / 006 更新）。"""

from tests.conftest import create_student


def test_create_student_success(world):
    c, ha = world["client"], world["ha"]
    resp = c.post(
        "/api/v1/students",
        json={
            "name": "小红",
            "grade_level": "五年级",
            "school_id": world["school_primary"]["school_id"],
            "relation": "女儿",
        },
        headers=ha,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "小红"
    assert body["school"]["school_id"] == world["school_primary"]["school_id"]
    assert body["school"]["stage"] == "primary"


def test_create_student_requires_valid_school(world):
    c, ha = world["client"], world["ha"]
    # 不存在但格式合法的 school_id
    resp = c.post(
        "/api/v1/students",
        json={"name": "小刚", "school_id": "00000000-0000-0000-0000-000000000000"},
        headers=ha,
    )
    assert resp.status_code == 422
    # 非法 school_id 格式
    resp = c.post("/api/v1/students", json={"name": "小刚", "school_id": "not-a-uuid"}, headers=ha)
    assert resp.status_code == 422


def test_create_student_empty_name_422(world):
    c, ha = world["client"], world["ha"]
    resp = c.post(
        "/api/v1/students",
        json={"name": "   ", "school_id": world["school_primary"]["school_id"]},
        headers=ha,
    )
    assert resp.status_code == 422


def test_list_students_family_scoped(world):
    c, ha, hb = world["client"], world["ha"], world["hb"]
    create_student(c, ha, school_id=world["school_primary"]["school_id"], name="A家孩子")
    create_student(c, hb, school_id=world["school_primary"]["school_id"], name="B家孩子")
    names_a = [s["name"] for s in c.get("/api/v1/students", headers=ha).json()]
    names_b = [s["name"] for s in c.get("/api/v1/students", headers=hb).json()]
    assert names_a == ["A家孩子"]
    assert names_b == ["B家孩子"]


def test_update_student(world):
    c, ha = world["client"], world["ha"]
    stu = create_student(c, ha, school_id=world["school_primary"]["school_id"], name="小华")
    resp = c.patch(
        f"/api/v1/students/{stu['student_id']}",
        json={"name": "小华改", "relation": "孙女"},
        headers=ha,
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "小华改"
    assert resp.json()["relation"] == "孙女"


def test_update_student_clear_nullable(world):
    c, ha = world["client"], world["ha"]
    stu = create_student(c, ha, school_id=world["school_primary"]["school_id"], name="小贝")
    resp = c.patch(
        f"/api/v1/students/{stu['student_id']}", json={"grade_level": None}, headers=ha
    )
    assert resp.status_code == 200
    assert resp.json()["grade_level"] is None


def test_update_student_change_school(world):
    c, ha = world["client"], world["ha"]
    stu = create_student(c, ha, school_id=world["school_primary"]["school_id"], name="转校生")
    target = [s for s in world["schools"] if s["school_id"] != world["school_primary"]["school_id"]][0]
    resp = c.patch(
        f"/api/v1/students/{stu['student_id']}", json={"school_id": target["school_id"]}, headers=ha
    )
    assert resp.status_code == 200
    assert resp.json()["school"]["school_id"] == target["school_id"]


def test_cross_family_student_not_found_404(world):
    c, ha, hb = world["client"], world["ha"], world["hb"]
    stu = create_student(c, ha, school_id=world["school_primary"]["school_id"], name="仅A家")
    # B 家读写 A 家档案 → 404（不泄露存在性）
    resp = c.patch(f"/api/v1/students/{stu['student_id']}", json={"name": "入侵"}, headers=hb)
    assert resp.status_code == 404
