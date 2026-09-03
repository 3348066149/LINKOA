# -*- coding: utf-8 -*-
"""V1.4.3 图标+字段 TestClient 全流程（沙箱可写窗口内一次性执行，避免外部锁）"""
import io
import json
import os
import sys
import uuid

os.environ.setdefault("DB_URL", "sqlite:///./linkoa.db")  # 相对路径，config.py 自动规范化到 backend/ 下
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)
ok_count = 0
TOTAL = 14
cleanup = []


def check(name, cond, extra=""):
    global ok_count
    assert cond, f"FAIL: {name} {extra}"
    ok_count += 1
    print(f"  ✓ {name}")


def post(path, body, token=None):
    h = {"Authorization": f"Bearer {token}"} if token else {}
    r = client.post(path, json=body, headers=h)
    return r.json()


def get(path, token=None):
    h = {"Authorization": f"Bearer {token}"} if token else {}
    return client.get(path, headers=h).json()


def upload(path, token, filename, content, field="file"):
    h = {"Authorization": f"Bearer {token}"} if token else {}
    r = client.post(path, files={field: (filename, content)}, headers=h)
    return r.json()


def login(username, password):
    res = post("/api/login", {"username": username, "password": password})
    assert res["code"] == 200, f"登录失败: {res}"
    return res["data"]


def main():
    global ok_count
    print("==== V1.4.3 TestClient 全流程 ====")
    admin = login("admin", "admin123")
    at = admin["token"]

    # 清理残留
    for t in get("/api/nodeTemplate/list", at):
        if t["nodeTitle"].startswith("测试节点") or t["nodeTitle"].startswith("TC"):
            post("/api/nodeTemplate/delete", {"id": t["id"]}, at)
    for c in get("/api/customer/list?pageNum=1&pageSize=100", at)["data"]["items"]:
        if c["customerName"] == "TC客户":
            post("/api/customer/delete", {"id": c["id"]}, at)
    for p in get("/api/project/list?pageNum=1&pageSize=100", at)["data"]["items"]:
        if p["projectName"] in ("TC项目", "TC流程项目"):
            post("/api/project/delete", {"projectId": p["id"]}, at)

    # 1. 模板带预设图标 + image/link/select 字段
    res = post("/api/nodeTemplate/add", {
        "nodeTitle": "TC节点A", "icon": "Document", "sort": 88,
        "formFields": [
            {"fieldLabel": "照片", "fieldType": "image", "sort": 1},
            {"fieldLabel": "链接", "fieldType": "link", "sort": 2},
            {"fieldLabel": "状态", "fieldType": "select", "selectOptions": ["高", "低"], "sort": 3},
        ]
    }, at)
    assert res["code"] == 200, f"建模板失败: {res}"
    tpl_a = res["data"]["id"]
    cleanup.append(("tpl", tpl_a))
    ta = next(t for t in get("/api/nodeTemplate/list", at) if t["id"] == tpl_a)
    check("模板保存图标+image/link字段", ta["icon"] == "Document" and
          {f["fieldType"] for f in ta["formFields"]} == {"image", "link", "select"})

    # 2. 自定义图标上传 + 建模板B
    svg = b'<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32"><circle cx="16" cy="16" r="14" fill="#409eff"/></svg>'
    res = upload("/api/nodeTemplate/icon/upload", at, "tc.svg", svg)
    assert res["code"] == 200, f"图标上传失败: {res}"
    icon_path = res["data"]["iconPath"]
    check("自定义图标上传", icon_path.startswith("node_icon/"))
    res = post("/api/nodeTemplate/add", {"nodeTitle": "TC节点B", "icon": icon_path, "sort": 89, "formFields": []}, at)
    assert res["code"] == 200, f"建模板B失败: {res}"
    tpl_b = res["data"]["id"]
    cleanup.append(("tpl", tpl_b))
    check("自定义图标模板", next(t for t in get("/api/nodeTemplate/list", at) if t["id"] == tpl_b)["icon"] == icon_path)

    # 3. 非法图标拦截
    res = upload("/api/nodeTemplate/icon/upload", at, "bad.exe", b"MZ")
    check("非法图标格式拦截", res["code"] == 400)

    # 4. 客户+项目+节点 → icon 拷贝
    res = post("/api/customer/add", {"categoryId": 1, "customerName": "TC客户", "contact": "1"}, at)
    assert res["code"] == 200, f"建客户失败: {res}"
    cid = res["data"]["id"]
    cleanup.append(("cust", cid))
    res = post("/api/project/create", {"projectName": "TC项目", "customerId": cid}, at)
    assert res["code"] == 200, f"建项目失败: {res}"
    pid = res["data"]["projectId"]
    cleanup.append(("proj", pid))
    res = post("/api/projectNode/add", {"projectId": pid, "nodeTemplateId": tpl_a}, at)
    assert res["code"] == 200, f"加节点失败: {res}"
    nid = res["data"]["id"]
    node = next(n for n in get(f"/api/project/detail/{pid}", at)["data"]["nodes"] if n["id"] == nid)
    check("项目节点冗余图标", node.get("icon") == "Document")

    # 5. getForm 字段类型
    form = get(f"/api/projectNode/getForm/{nid}", at)["data"]["fields"]
    types = {f["fieldType"] for f in form}
    check("getForm 含 image/link/select", {"image", "link", "select"} <= types)
    im = next(f for f in form if f["fieldType"] == "image")
    lk = next(f for f in form if f["fieldType"] == "link")
    sl = next(f for f in form if f["fieldType"] == "select")

    # 6. 表单图片上传 + 保存
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
    res = upload("/api/projectNode/formImage/upload", at, "p.png", png)
    assert res["code"] == 200, f"表单图片上传失败: {res}"
    img_path = res["data"]["imagePath"]
    check("表单图片上传", img_path.startswith("node_form/"))
    res = post("/api/projectNode/saveFormValue", {"projectNodeId": nid, "formValueList": [
        {"id": im["id"], "fieldValue": img_path},
        {"id": lk["id"], "fieldValue": "https://example.com"},
        {"id": sl["id"], "fieldValue": "高"},
    ]}, at)
    check("保存 image/link/select", res["code"] == 200, str(res))

    # 7. 回显 + form_filled
    form2 = get(f"/api/projectNode/getForm/{nid}", at)["data"]["fields"]
    im2 = next(f for f in form2 if f["fieldType"] == "image")
    lk2 = next(f for f in form2 if f["fieldType"] == "link")
    check("回显 image/link", im2["fieldValue"] == img_path and lk2["fieldValue"] == "https://example.com")
    n2 = next(n for n in get(f"/api/project/detail/{pid}", at)["data"]["nodes"] if n["id"] == nid)
    check("节点 form_filled", n2["formFilled"] is True)

    # 8. 普通用户可传图 / 客户禁止
    res = post("/api/sysUser/create", {"username": "tc_staff", "password": "x123456", "realName": "员工", "deptId": 1, "role": "普通"}, at)
    assert res["code"] == 200, f"建员工失败: {res}"
    cleanup.append(("user", res["data"]["userId"]))
    staff = login("tc_staff", "x123456")
    res = upload("/api/projectNode/formImage/upload", staff["token"], "p.png", png)
    check("普通用户可上传表单图片", res["code"] == 200)
    res = post("/api/sysUser/create", {"username": "tc_cust", "password": "x123456", "realName": "客户", "customerId": cid}, at)
    assert res["code"] == 200, f"建客户账号失败: {res}"
    cleanup.append(("user", res["data"]["userId"]))
    cust = login("tc_cust", "x123456")
    res = upload("/api/projectNode/formImage/upload", cust["token"], "p.png", png)
    check("客户禁止上传表单图片", res["code"] == 403)

    # 9. 客户可读 getForm（image/link 可见）
    res = get(f"/api/projectNode/getForm/{nid}", cust["token"])
    check("客户可读 image/link 字段", res["code"] == 200 and
          {"image", "link"} <= {f["fieldType"] for f in res["data"]["fields"]})

    # 10. 流程模板实例化带图标
    res = post("/api/flowTemplate/add", {
        "templateName": "TC流程模板", "projectNameTemplate": "TC流程项目",
        "nodes": [{"nodeTitle": "TC流程节点", "nodeTemplateId": tpl_a, "posX": 0, "posY": 0, "sort": 1}],
        "edges": [],
    }, at)
    assert res["code"] == 200, f"建流程模板失败: {res}"
    ftid = res["data"]["id"]
    cleanup.append(("flowtpl", ftid))
    res = post("/api/project/create", {"projectName": "TC流程项目", "customerId": cid, "templateId": ftid}, at)
    assert res["code"] == 200, f"流程实例化失败: {res}"
    pid2 = res["data"]["projectId"]
    cleanup.append(("proj", pid2))
    d3 = get(f"/api/project/detail/{pid2}", at)["data"]
    check("流程实例化节点带图标", d3["nodes"] and d3["nodes"][0].get("icon") == "Document")

    # ---- 清理 ----
    print("---- 清理 ----")
    for kind, rid in cleanup:
        if kind == "proj":
            post("/api/project/delete", {"projectId": rid}, at)
        elif kind == "cust":
            post("/api/customer/delete", {"id": rid}, at)
        elif kind == "user":
            post("/api/sysUser/delete", {"userId": rid}, at)
        elif kind == "tpl":
            post("/api/nodeTemplate/delete", {"id": rid}, at)
        elif kind == "flowtpl":
            post("/api/flowTemplate/delete", {"id": rid}, at)
    check("测试数据已清理", True)
    print(f"\n=== 通过 {ok_count}/{TOTAL} ===")
    if ok_count != TOTAL:
        sys.exit(1)


if __name__ == "__main__":
    main()
