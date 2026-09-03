# -*- coding: utf-8 -*-
"""V1.4.2 角色简化（普通/管理员）全链路自检

覆盖：建普通/管理员账号 / 普通=设计师权限（不能建项目管客户建模板，但能填表单评论附件）/
管理员全权限 / 客户独立只读 / 存量迁移 / 数据清理。
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
cleanup_customers = []
cleanup_projects = []


def check(name, cond, extra=""):
    global ok_count
    assert cond, f"FAIL: {name} {extra}"
    ok_count += 1
    print(f"  ✓ {name}")


def main():
    global ok_count
    print("==== V1.4.2 角色简化（普通/管理员）测试 ====")

    # 0. 管理员登录（迁移后 admin 应为管理员）
    admin = login("admin", "admin123")
    check("admin 登录且角色=管理员", admin["userInfo"]["role"] == "管理员", admin["userInfo"]["role"])
    at = admin["token"]

    # 0.5 清理可能残留的测试数据
    for u in req("/api/sysUser/list", token=at)["data"]:
        if u["username"] in ("staff_test", "boss_test", "cust_simple", "legacy_designer", "legacy_director", "legacy_office"):
            req("/api/sysUser/delete", "POST", {"userId": u["id"]}, at)
    for c in req("/api/customer/list?pageNum=1&pageSize=100", token=at)["data"]["items"]:
        if c["customerName"] == "简化测试客户":
            req("/api/customer/delete", "POST", {"id": c["id"]}, at)
    for proj in req("/api/project/list?pageNum=1&pageSize=100", token=at)["data"]["items"]:
        if proj["projectName"] == "简化测试项目":
            req("/api/project/delete", "POST", {"projectId": proj["id"]}, at)

    # 1. 存量 legacy 用户迁移已生效（真实库验证）
    users = req("/api/sysUser/list", token=at)["data"]
    check("存量 legacy 用户已被迁移为普通（库中无设计师/总监/行政）",
          all(u["role"] not in ("设计师", "设计总监", "行政") for u in users), str([(u["username"], u["role"]) for u in users]))

    # 2. 建「普通」与「管理员」两类账号
    depts = req("/api/sysDept/list", token=at)["data"]
    rd = next(d for d in depts if d["deptName"] == "研发部")["id"]
    res = req("/api/sysUser/create", "POST", {"username": "staff_test", "password": "staff123", "realName": "普通员工", "deptId": rd, "role": "普通"}, at)
    assert res["code"] == 200, f"建普通账号失败: {res}"
    cleanup_users.append(res["data"]["userId"])
    res = req("/api/sysUser/create", "POST", {"username": "boss_test", "password": "boss123", "realName": "第二管理员", "deptId": rd, "role": "管理员"}, at)
    assert res["code"] == 200, f"建管理员账号失败: {res}"
    cleanup_users.append(res["data"]["userId"])
    check("建普通/管理员两类账号", True)

    # 3. 普通账号：能查看，不能建项目/管客户/建模板/看日志/用户管理
    staff = login("staff_test", "staff123")
    check("普通登录 role=普通", staff["userInfo"]["role"] == "普通")
    res = req("/api/project/list?pageNum=1&pageSize=5", token=staff["token"])
    check("普通可查看项目", res["code"] == 200)
    res = req("/api/project/create", "POST", {"projectName": "x", "customerId": 2}, staff["token"])
    check("普通禁止建项目", res["code"] == 403, str(res))
    res = req("/api/customer/add", "POST", {"categoryId": 1, "customerName": "x"}, staff["token"])
    check("普通禁止管客户", res["code"] == 403, str(res))
    res = req("/api/flowTemplate/add", "POST", {"templateName": "x", "nodes": [], "edges": []}, staff["token"])
    check("普通禁止建模板", res["code"] == 403, str(res))
    res = req("/api/sysUser/list", token=staff["token"])
    check("普通禁止用户管理", res["code"] == 403, str(res))
    res = req("/api/sysOperationLog/globalList", token=staff["token"])
    check("普通禁止审计日志", res["code"] == 403, str(res))

    # 4. 普通账号：项目内执行（评论/表单/附件等登录即可操作）
    res = req("/api/comment/add", "POST", {"projectId": 1, "content": "普通员工评论"}, staff["token"])
    check("普通可发评论", res["code"] == 200, str(res))

    # 5. 管理员账号：全权限
    boss = login("boss_test", "boss123")
    check("管理员登录 role=管理员", boss["userInfo"]["role"] == "管理员")
    res = req("/api/customer/add", "POST", {"categoryId": 1, "customerName": "简化测试客户", "contact": "000"}, boss["token"])
    assert res["code"] == 200, f"管理员建客户失败: {res}"
    cid = res["data"]["id"]
    cleanup_customers.append(cid)
    check("管理员可管客户", True)
    res = req("/api/project/create", "POST", {"projectName": "简化测试项目", "customerId": cid}, boss["token"])
    assert res["code"] == 200, f"管理员建项目失败: {res}"
    cleanup_projects.append(res["data"]["projectId"])
    check("管理员可建项目", True)
    res = req("/api/sysDept/list", token=boss["token"])
    check("管理员可看部门（系统管理）", res["code"] == 200)
    res = req("/api/sysUser/list", token=boss["token"])
    check("管理员可用户管理", res["code"] == 200)

    # 6. 客户账号独立：只读
    res = req("/api/customer/add", "POST", {"categoryId": 1, "customerName": "简化测试客户", "contact": "000"}, at)
    cid2 = res["data"]["id"]
    cleanup_customers.append(cid2)
    res = req("/api/project/create", "POST", {"projectName": "简化测试项目", "customerId": cid2}, at)
    pid2 = res["data"]["projectId"]
    cleanup_projects.append(pid2)
    res = req("/api/sysUser/create", "POST", {"username": "cust_simple", "password": "cust123", "realName": "简化客户", "customerId": cid2}, at)
    assert res["code"] == 200, f"建客户账号失败: {res}"
    cleanup_users.append(res["data"]["userId"])
    cu = login("cust_simple", "cust123")
    check("客户账号 role=客户（独立）", cu["userInfo"]["role"] == "客户")
    res = req("/api/project/list?pageNum=1&pageSize=50", token=cu["token"])
    check("客户只见自己项目", all(i["customerName"] == "简化测试客户" for i in res["data"]["items"]))
    res = req(f"/api/project/detail/{pid2}", token=cu["token"])
    check("客户可看自己项目详情", res["code"] == 200)
    res = req("/api/project/create", "POST", {"projectName": "x", "customerId": cid2}, cu["token"])
    check("客户禁止任何写操作", res["code"] == 403, str(res))

    # 7. 编辑用户：普通↔管理员 互转 + 缺角色拦截
    staff_id = next(u["id"] for u in req("/api/sysUser/list", token=at)["data"] if u["username"] == "staff_test")
    res = req("/api/sysUser/update", "POST", {"id": staff_id, "realName": "普通员工", "deptId": rd, "role": "管理员"}, at)
    check("普通→管理员可编辑", res["code"] == 200, str(res))
    res = req("/api/sysUser/update", "POST", {"id": staff_id, "realName": "普通员工", "deptId": rd, "role": "普通"}, at)
    check("管理员→普通可编辑", res["code"] == 200, str(res))
    res = req("/api/sysUser/update", "POST", {"id": staff_id, "realName": "普通员工", "deptId": rd}, at)
    check("编辑用户缺角色拦截", res["code"] == 400, str(res))

    # ---- 清理 ----
    print("---- 清理测试数据 ----")
    for pid in cleanup_projects:
        req("/api/project/delete", "POST", {"projectId": pid}, at)
    for cid in cleanup_customers:
        req("/api/customer/delete", "POST", {"id": cid}, at)
    for uid in cleanup_users:
        req("/api/sysUser/delete", "POST", {"userId": uid}, at)
    users = req("/api/sysUser/list", token=at)["data"]
    leftover = [u for u in users if u["username"] in ("staff_test", "boss_test", "cust_simple")]
    check("测试账号已清理", not leftover, str(leftover))
    check("admin 保持管理员", any(u["username"] == "admin" and u["role"] == "管理员" for u in users))

    print(f"\n=== 通过 {ok_count}/{TOTAL} ===")
    if ok_count != TOTAL:
        sys.exit(1)


if __name__ == "__main__":
    main()
