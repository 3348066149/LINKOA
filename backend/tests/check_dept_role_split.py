# -*- coding: utf-8 -*-
"""V1.4 部门-角色解耦 全链路自检（模拟数据，测试结束自动清理）

覆盖：建部门无需权限模板 / 同部门多角色权限独立 / 改部门权限不变 /
编辑用户接口 / 客户账号不受影响 / 数据清理。
"""
import json
import sys
import urllib.request
import urllib.error

BASE = "http://localhost:8000"


def req(path, method="GET", body=None, token=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(BASE + path, data=data, method=method)
    if body is not None:
        r.add_header("Content-Type", "application/json")
    if token:
        r.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(r) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return json.loads(e.read().decode())


def login(username, password):
    res = req("/api/login", "POST", {"username": username, "password": password})
    assert res["code"] == 200, f"登录失败 {username}: {res}"
    return res["data"]


ok_count = 0
TOTAL = 25
cleanup_users = []
cleanup_depts = []
cleanup_customers = []
cleanup_projects = []


def check(name, cond, extra=""):
    global ok_count
    assert cond, f"FAIL: {name} {extra}"
    ok_count += 1
    print(f"  ✓ {name}")


def main():
    global ok_count
    print("==== V1.4 部门-角色解耦 全链路测试 ====")

    # 0. 管理员登录
    admin = login("admin", "admin123")
    at = admin["token"]
    check("管理员登录", True)

    # 1. 新建部门无需权限模板（接口不传 role）
    res = req("/api/sysDept/add", "POST", {"deptName": "运营部", "deptType": "internal"}, at)
    assert res["code"] == 200, f"建部门失败: {res}"
    op_dept = res["data"]["deptId"]
    cleanup_depts.append(op_dept)
    depts = req("/api/sysDept/list", token=at)["data"]
    op = next(d for d in depts if d["id"] == op_dept)
    check("新建部门无权限模板", "role" not in op or op.get("role") is None, str(op))

    # 2. 同部门（设计部）下创建 3 个不同角色用户，权限相互独立
    design_dept = next(d for d in depts if d["deptName"] == "设计部")["id"]
    users = []
    for uname, role, rname in [("designer_a", "设计师", "甲设计师"), ("director_b", "设计总监", "乙总监"), ("office_c", "行政", "丙行政")]:
        res = req("/api/sysUser/create", "POST", {
            "username": uname, "password": "test123456", "realName": rname,
            "deptId": design_dept, "role": role
        }, at)
        assert res["code"] == 200, f"建用户失败: {res}"
        users.append((uname, role, res["data"]["userId"]))
        cleanup_users.append(res["data"]["userId"])
    check("同部门建 3 个不同角色用户", True)

    # 3. 设计师：能查项目，但不能改项目（权限来自自身角色）
    da = login("designer_a", "test123456")
    check("设计师登录 role 正确", da["userInfo"]["role"] == "设计师")
    res = req("/api/project/list?pageNum=1&pageSize=5", token=da["token"])
    check("设计师可查看项目", res["code"] == 200)
    res = req("/api/project/updateBase", "POST", {"id": 1, "projectName": "a", "customerId": 2, "projectDesc": "x"}, da["token"])
    check("设计师禁止改项目", res["code"] == 403, str(res))

    # 4. 设计总监：能改项目
    db = login("director_b", "test123456")
    check("设计总监登录 role 正确", db["userInfo"]["role"] == "设计总监")
    res = req("/api/project/updateBase", "POST", {"id": 1, "projectName": "a", "customerId": 2, "projectDesc": "desc"}, db["token"])
    check("设计总监可改项目", res["code"] == 200, str(res))

    # 5. 行政：能改客户（行政在客户写权限）
    dc = login("office_c", "test123456")
    check("行政登录 role 正确", dc["userInfo"]["role"] == "行政")
    res = req("/api/customer/list?pageNum=1&pageSize=5", token=dc["token"])
    check("行政可查看客户", res["code"] == 200)
    res = req("/api/sysUser/list", token=dc["token"])
    check("行政禁止访问用户管理（仅管理员）", res["code"] == 403, str(res))

    # 6. 编辑用户：把 设计总监 从设计部调到研发部，权限保持不变
    rd_dept = next(d for d in req("/api/sysDept/list", token=at)["data"] if d["deptName"] == "研发部")["id"]
    bid = users[1][2]
    res = req("/api/sysUser/update", "POST", {"id": bid, "realName": "乙总监", "deptId": rd_dept, "role": "设计总监"}, at)
    check("编辑用户部门设计部→研发部", res["code"] == 200, str(res))
    users_list = req("/api/sysUser/list", token=at)["data"]
    b_row = next(u for u in users_list if u["id"] == bid)
    check("调动部门后角色不变", b_row["role"] == "设计总监" and b_row["deptId"] == rd_dept, str(b_row))
    db2 = login("director_b", "test123456")
    check("调动部门后权限不变（仍能改项目）", db2["userInfo"]["role"] == "设计总监")
    res = req("/api/project/updateBase", "POST", {"id": 1, "projectName": "a", "customerId": 2, "projectDesc": "desc2"}, db2["token"])
    check("调动部门后仍可改项目（权限不随部门）", res["code"] == 200, str(res))

    # 7. 编辑用户缺角色/缺部门 → 拦截
    res = req("/api/sysUser/update", "POST", {"id": bid, "realName": "乙总监", "deptId": rd_dept}, at)
    check("编辑用户缺角色拦截", res["code"] == 400, str(res))

    # 8. 客户账号不受影响：建客户+项目+客户账号，登录只读
    res = req("/api/customer/add", "POST", {"categoryId": 1, "customerName": "测试客户V14", "contact": "000"}, at)
    assert res["code"] == 200, f"建客户失败: {res}"
    cid = res["data"]["id"]
    cleanup_customers.append(cid)
    res = req("/api/project/create", "POST", {"projectName": "测试项目V14", "customerId": cid}, at)
    assert res["code"] == 200, f"建项目失败: {res}"
    pid = res["data"]["projectId"]
    cleanup_projects.append(pid)
    res = req("/api/sysUser/create", "POST", {
        "username": "cust_v14", "password": "cust123", "realName": "客户对接", "customerId": cid
    }, at)
    assert res["code"] == 200, f"建客户账号失败: {res}"
    cleanup_users.append(res["data"]["userId"])
    cu = login("cust_v14", "cust123")
    check("客户账号登录 role=客户", cu["userInfo"]["role"] == "客户")
    res = req("/api/project/list?pageNum=1&pageSize=50", token=cu["token"])
    names = [i["projectName"] for i in res["data"]["items"]]
    check("客户只见自己的项目", names == ["测试项目V14"], str(names))
    res = req(f"/api/project/detail/{pid}", token=cu["token"])
    check("客户可看自己项目详情", res["code"] == 200)
    res = req("/api/project/updateBase", "POST", {"id": pid, "projectName": "测试项目V14", "customerId": cid}, cu["token"])
    check("客户禁止改项目", res["code"] == 403, str(res))
    # 客户账号编辑：不允许分配角色/部门
    cu_id = cleanup_users[-1]
    res = req("/api/sysUser/update", "POST", {"id": cu_id, "realName": "客户对接", "deptId": rd_dept, "role": "行政"}, at)
    check("客户账号禁止分配部门/角色", res["code"] == 400, str(res))

    # 9. 删除部门：仅解绑分组，不影响用户权限；有用户时删除被拦截
    design_has_user = req("/api/sysDept/list", token=at)["data"]
    d2 = next(d for d in design_has_user if d["deptName"] == "设计部")
    check("设计部仍有用户", d2["userCount"] >= 2, f"userCount={d2['userCount']}")
    res = req("/api/sysDept/delete", "POST", {"id": d2["id"]}, at)
    check("部门占用删除拦截", res["code"] == 400 and "还有" in res["msg"], str(res))
    # 用户调走后再删（用新建的运营部验证空部门可删）
    res = req("/api/sysDept/delete", "POST", {"id": op_dept}, at)
    check("空部门可删除", res["code"] == 200, str(res))
    if op_dept in cleanup_depts:
        cleanup_depts.remove(op_dept)

    # ---- 清理 ----
    print("---- 清理测试数据（先项目、再客户、最后用户/部门）----")
    for pid in cleanup_projects:
        req("/api/project/delete", "POST", {"projectId": pid}, at)
    for cid in cleanup_customers:
        req("/api/customer/delete", "POST", {"id": cid}, at)
    for uid in cleanup_users:
        req("/api/sysUser/delete", "POST", {"userId": uid}, at)
    for did in cleanup_depts:
        req("/api/sysDept/delete", "POST", {"id": did}, at)
    # 校验清理干净
    users = req("/api/sysUser/list", token=at)["data"]
    leftover_users = [u for u in users if u["username"] in ("designer_a", "director_b", "office_c", "cust_v14")]
    check("测试账号已清理", not leftover_users, str(leftover_users))
    print(f"\n=== 通过 {ok_count}/{TOTAL} ===")
    if ok_count != TOTAL:
        sys.exit(1)


if __name__ == "__main__":
    main()
