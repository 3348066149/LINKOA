# -*- coding: utf-8 -*-
"""[已过时-不可运行] V1.3 部门 + 客户门户 全链路自检（模拟数据，测试结束自动清理）

⚠️ 本脚本建立在「建部门时绑定权限模板 role（研发部=设计师 / 设计部=设计总监 / 市场部=行政）」
和「新建用户 role 可取设计师/设计总监/行政」的旧模型上。现行模型（V1.4.15 起）：
用户 role 收敛为 管理员 / 普通 / 客户，部门仅作组织归属、不再返回 role 字段，
故本脚本会因 v["role"] KeyError 而失败，属预期。

替代覆盖（均已通过）：
  - 部门 CRUD                    → backend/tests/full_flow_check.py 第 12 章
  - 客户门户隔离 / 跨单位拦截     → backend/tests/full_flow_check.py 第 16 章
  - 客户审核 + 反馈多文件         → backend/tests/multifile_upload_check.py 第 D/E 章

保留原因：仅作历史留档。
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
TOTAL = 30
cleanup = []  # (kind, id/name)


def check(name, cond, extra=""):
    global ok_count
    assert cond, f"FAIL: {name} {extra}"
    ok_count += 1
    print(f"  ✓ {name}")


def main():
    global ok_count
    print("==== 部门体系 + 客户门户 全链路测试 ====")

    # 0. 管理员登录
    admin = login("admin", "admin123")
    at = admin["token"]
    check("管理员登录", True)

    # 0.5 清理上次中断可能残留的测试数据
    for d in req("/api/sysDept/list", token=at)["data"]:
        if d["deptName"] in ("运营部", "运营中心", "缺模板部门"):
            req("/api/sysDept/delete", "POST", {"id": d["id"]}, at)
    for u in req("/api/sysUser/list", token=at)["data"]:
        if u["username"] in ("qd_gong1", "qd_gong2", "qd_gong3", "dev_xiao"):
            req("/api/sysUser/delete", "POST", {"userId": u["id"]}, at)
    for proj in req("/api/project/list?pageNum=1&pageSize=100", token=at)["data"]["items"]:
        if proj["projectName"] in ("青岛地铁-线路导向标识设计", "服贸会-展台设计"):
            req("/api/project/delete", "POST", {"projectId": proj["id"]}, at)
    for c in req("/api/customer/list?pageNum=1&pageSize=100", token=at)["data"]["items"]:
        if c["customerName"] in ("青岛地铁", "服贸会"):
            req("/api/customer/delete", "POST", {"id": c["id"]}, at)

    # 1. 内置部门预置（研发部=设计师 / 设计部=设计总监 / 市场部=行政）
    depts = req("/api/sysDept/list", token=at)["data"]
    internal = {d["deptName"]: d for d in depts if d["deptType"] == "internal"}
    check("内置部门预置", {"研发部": "设计师", "设计部": "设计总监", "市场部": "行政"}.items() <= {
        (k, v["role"]) for k, v in internal.items()}, str(internal))
    dept_rd = internal["研发部"]["id"]

    # 2. 部门 CRUD：新增「运营部」→ 重名拦截 → 删除
    res = req("/api/sysDept/add", "POST", {"deptName": "运营部", "deptType": "internal", "role": "行政"}, at)
    check("新建内置部门", res["code"] == 200, str(res))
    op_dept_id = res["data"]["deptId"]
    res = req("/api/sysDept/add", "POST", {"deptName": "运营部", "deptType": "internal", "role": "行政"}, at)
    check("部门重名拦截", res["code"] == 400 and "已存在" in res["msg"], str(res))
    res = req("/api/sysDept/add", "POST", {"deptName": "缺模板部门", "deptType": "internal"}, at)
    check("内置部门缺权限模板拦截", res["code"] == 400, str(res))
    # 运营部改名 + 删除
    res = req("/api/sysDept/update", "POST", {"id": op_dept_id, "deptName": "运营中心", "role": "行政"}, at)
    check("部门改名", res["code"] == 200, str(res))
    res = req("/api/sysDept/delete", "POST", {"id": op_dept_id}, at)
    check("部门删除", res["code"] == 200, str(res))

    # 3. 创建测试客户「青岛地铁」与「服贸会」
    res = req("/api/customer/add", "POST", {"categoryId": 1, "customerName": "青岛地铁", "contact": "0532-8888", "remark": "测试客户"}, at)
    assert res["code"] == 200, f"建客户失败: {res}"
    cid_qd = res["data"]["id"]
    cleanup.append(("customer", cid_qd))
    res = req("/api/customer/add", "POST", {"categoryId": 1, "customerName": "服贸会", "contact": "010-6666"}, at)
    assert res["code"] == 200, f"建客户失败: {res}"
    cid_fmh = res["data"]["id"]
    cleanup.append(("customer", cid_fmh))
    check("创建测试客户", True)

    # 4. 创建项目（青岛地铁 1 个、服贸会 1 个）
    res = req("/api/project/create", "POST", {
        "projectName": "青岛地铁-线路导向标识设计", "customerId": cid_qd,
        "projectDesc": "一期 3 条线路导向标识", "expectTime": "2026-12-31 00:00:00"
    }, at)
    assert res["code"] == 200, f"建项目失败: {res}"
    pid_qd = res["data"]["projectId"]
    cleanup.append(("project", pid_qd))
    res = req("/api/project/create", "POST", {
        "projectName": "服贸会-展台设计", "customerId": cid_fmh, "projectDesc": "2026 服贸会"
    }, at)
    assert res["code"] == 200, f"建项目失败: {res}"
    pid_fmh = res["data"]["projectId"]
    cleanup.append(("project", pid_fmh))
    check("创建测试项目", True)

    # 5. 给青岛地铁项目加 3 个节点（从节点模板库选），其中 2 个填表单 → 进度 67%
    tpls = req("/api/nodeTemplate/list", token=at)["data"]
    assert isinstance(tpls, list) and tpls, f"节点模板为空: {tpls}"
    tpl_ids = [t["id"] for t in tpls[:3]]
    node_ids = []
    for tid in tpl_ids:
        res = req("/api/projectNode/add", "POST", {"projectId": pid_qd, "nodeTemplateId": tid}, at)
        assert res["code"] == 200, f"加节点失败: {res}"
        node_ids.append(res["data"]["id"])
    # 给前 2 个节点填表单（模拟完成）：先 getForm 拿字段 id，再全量覆盖保存
    form_ok = 0
    for nid in node_ids[:2]:
        fields = req(f"/api/projectNode/getForm/{nid}", token=at)["data"]["fields"]
        vals = [{"id": f["id"], "fieldValue": f"测试填写-{f['fieldLabel']}"} for f in fields if f.get("id")]
        res = req("/api/projectNode/saveFormValue", "POST", {"projectNodeId": nid, "formValueList": vals}, at)
        if res["code"] == 200:
            form_ok += 1
        else:
            print(f"  保存失败 node={nid}: {res}")
    check("节点+表单填写", form_ok == 2, f"{form_ok}/2")

    # 6. 创建 3 个青岛地铁客户账号（一客户多账号）
    qd_users = []
    for i, name in enumerate(["张工", "李工", "王工"]):
        uname = f"qd_gong{i+1}"
        res = req("/api/sysUser/create", "POST", {
            "username": uname, "password": "qd123456", "realName": f"青岛地铁-{name}", "customerId": cid_qd
        }, at)
        assert res["code"] == 200, f"建客户账号失败: {res}"
        qd_users.append((uname, res["data"]["userId"]))
    check("创建 3 个客户账号（一客户多账号）", len(qd_users) == 3)
    for _, uid in qd_users:
        cleanup.append(("user", uid))

    # 7. 内部员工：研发部 → role=设计师
    res = req("/api/sysUser/create", "POST", {
        "username": "dev_xiao", "password": "dev123456", "realName": "研发-小陈", "deptId": dept_rd
    }, at)
    assert res["code"] == 200, f"建内部员工失败: {res}"
    dev_uid = res["data"]["userId"]
    cleanup.append(("user", dev_uid))
    dev = login("dev_xiao", "dev123456")
    check("内部员工按部门权限（研发部=设计师）", dev["userInfo"]["role"] == "设计师", dev["userInfo"]["role"])
    check("登录返回部门名", dev["userInfo"].get("deptName") == "研发部", str(dev["userInfo"]))

    # 8. 客户账号登录：role=客户，带客户名
    qd1 = login("qd_gong1", "qd123456")
    check("客户账号登录 role=客户", qd1["userInfo"]["role"] == "客户")
    check("客户登录返回客户名", qd1["userInfo"].get("customerName") == "青岛地铁", str(qd1["userInfo"]))

    # 9. 客户项目列表：只能看到青岛地铁的项目
    res = req("/api/project/list?pageNum=1&pageSize=50", token=qd1["token"])
    names = [i["projectName"] for i in res["data"]["items"]]
    check("客户只看到自己的项目", names == ["青岛地铁-线路导向标识设计"], str(names))
    p = res["data"]["items"][0]
    check("项目列表返回进度占比", p.get("progressPercent") == 67, f"progressPercent={p.get('progressPercent')}")

    # 10. 客户查看自己项目详情：3 节点 2 完成
    res = req(f"/api/project/detail/{pid_qd}", token=qd1["token"])
    nodes = res["data"]["nodes"]
    check("客户看项目详情节点进度", len(nodes) == 3 and sum(1 for n in nodes if n["formFilled"]) == 2,
          f"{sum(1 for n in nodes if n['formFilled'])}/3")

    # 11. 客户看别人客户的项目 → 403
    res = req(f"/api/project/detail/{pid_fmh}", token=qd1["token"])
    check("客户跨客户访问拦截", res["code"] == 403, str(res))
    res = req("/api/project/list?pageNum=1&pageSize=50&customerId=2", token=qd1["token"])
    check("客户列表带 customerId 过滤仍隔离", all(i["customerName"] == "青岛地铁" for i in res["data"]["items"]))

    # 12. 客户写操作拦截（改表单 / 加节点 / 评论 / 附件）
    res = req("/api/projectNode/saveFormValue", "POST", {
        "projectNodeId": node_ids[2], "values": [{"fieldLabel": "x", "fieldType": "text", "fieldValue": "恶意修改"}]
    }, qd1["token"])
    check("客户禁止修改表单", res["code"] == 403, str(res))
    res = req("/api/projectNode/add", "POST", {"projectId": pid_qd, "nodeTitle": "恶意节点"}, qd1["token"])
    check("客户禁止新增节点", res["code"] == 403, str(res))
    res = req("/api/comment/add", "POST", {"projectId": pid_qd, "content": "恶意评论"}, qd1["token"])
    check("客户禁止发表评论", res["code"] == 403, str(res))

    # 13. 客户可读自己的节点表单（只读）
    res = req(f"/api/projectNode/getForm/{node_ids[0]}", token=qd1["token"])
    check("客户可读表单内容", res["code"] == 200 and len(res["data"]["fields"]) == 2, str(res))

    # 14. 客户账号可单独停用（不影响其他账号）
    res = req("/api/sysUser/setEnable", "POST", {"userId": qd_users[1][1], "isEnable": 0}, at)
    check("停用第 2 个客户账号", res["code"] == 200)
    res = req("/api/login", "POST", {"username": "qd_gong2", "password": "qd123456"})
    check("停用后无法登录", res["code"] == 400 and "停用" in res["msg"], str(res))
    res = req("/api/login", "POST", {"username": "qd_gong1", "password": "qd123456"})
    check("其余客户账号不受影响", res["code"] == 200)
    req("/api/sysUser/setEnable", "POST", {"userId": qd_users[1][1], "isEnable": 1}, at)

    # 15. 客户账号不能访问 OA 用户管理（仅管理员）
    res = req("/api/sysUser/list", token=qd1["token"])
    check("客户禁止访问用户管理", res["code"] == 403, str(res))

    # 16. 部门占用拦截：研发部有人不能删
    res = req("/api/sysDept/delete", "POST", {"id": dept_rd}, at)
    check("部门有用户时禁止删除", res["code"] == 400 and "还有" in res["msg"], str(res))

    # ---- 清理 ----
    print("---- 清理测试数据（先项目、再客户、最后用户）----")
    for kind, rid in cleanup:
        if kind == "project":
            req("/api/project/delete", "POST", {"projectId": rid}, at)
    for kind, rid in cleanup:
        if kind == "customer":
            req("/api/customer/delete", "POST", {"id": rid}, at)
    for kind, rid in cleanup:
        if kind == "user":
            req("/api/sysUser/delete", "POST", {"userId": rid}, at)
    req("/api/sysUser/delete", "POST", {"userId": dev_uid}, at)
    for d in req("/api/sysDept/list", token=at)["data"]:
        if d["deptName"] in ("设计师", "缺模板部门"):
            req("/api/sysDept/delete", "POST", {"id": d["id"]}, at)
    # 校验清理干净
    res = req("/api/sysUser/list", token=at)["data"]
    leftover = [u for u in res if u["username"] in ("qd_gong1", "qd_gong2", "qd_gong3", "dev_xiao")]
    check("测试账号已清理", not leftover, str(leftover))
    print(f"\n=== 通过 {ok_count}/{TOTAL} ===")
    if ok_count != TOTAL:
        sys.exit(1)


if __name__ == "__main__":
    main()
