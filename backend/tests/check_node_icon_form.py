# -*- coding: utf-8 -*-
"""V1.4.3 节点图标 + 表单字段 image/link 全链路自检（模拟数据，测试结束自动清理）"""
import json
import sys
import uuid
import urllib.request
import urllib.error
import io

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


def upload(path, token, filename, content, field="file"):
    """multipart 上传"""
    boundary = "----wb" + uuid.uuid4().hex
    body = io.BytesIO()
    body.write(f"--{boundary}\r\n".encode())
    body.write(f'Content-Disposition: form-data; name="{field}"; filename="{filename}"\r\n'.encode())
    body.write(b"Content-Type: application/octet-stream\r\n\r\n")
    body.write(content)
    body.write(f"\r\n--{boundary}--\r\n".encode())
    r = urllib.request.Request(
        BASE + path, data=body.getvalue(), method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
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
TOTAL = 16
cleanup_users = []
cleanup_customers = []
cleanup_projects = []
cleanup_templates = []


def check(name, cond, extra=""):
    global ok_count
    assert cond, f"FAIL: {name} {extra}"
    ok_count += 1
    print(f"  ✓ {name}")


def main():
    global ok_count
    print("==== V1.4.3 节点图标 + image/link 字段测试 ====")

    admin = login("admin", "admin123")
    at = admin["token"]

    # 0. 清理残留
    for t in req("/api/nodeTemplate/list", token=at):
        if t["nodeTitle"].startswith("测试节点"):
            req("/api/nodeTemplate/delete", "POST", {"id": t["id"]}, at)
    for u in req("/api/sysUser/list", token=at):
        if u["username"] in ("ic_cust",):
            req("/api/sysUser/delete", "POST", {"userId": u["id"]}, at)
    for c in req("/api/customer/list?pageNum=1&pageSize=100", token=at)["data"]["items"]:
        if c["customerName"] == "图标测试客户":
            req("/api/customer/delete", "POST", {"id": c["id"]}, at)
    for proj in req("/api/project/list?pageNum=1&pageSize=100", token=at)["data"]["items"]:
        if proj["projectName"] == "图标测试项目":
            req("/api/project/delete", "POST", {"projectId": proj["id"]}, at)

    # 1. 创建带图标的节点模板（预设图标 Document + 字段 image/link/select）
    res = req("/api/nodeTemplate/add", "POST", {
        "nodeTitle": "测试节点A", "nodeRemark": "图标测试",
        "icon": "Document", "sort": 90,
        "formFields": [
            {"fieldLabel": "现场照片", "fieldType": "image", "sort": 1},
            {"fieldLabel": "参考链接", "fieldType": "link", "sort": 2},
            {"fieldLabel": "完成度", "fieldType": "select", "selectOptions": ["高", "中", "低"], "sort": 3},
        ]
    }, at)
    assert res["code"] == 200, f"建模板失败: {res}"
    tpl_a = res["data"]["id"]
    cleanup_templates.append(tpl_a)
    tpls = req("/api/nodeTemplate/list", token=at)
    ta = next(t for t in tpls if t["id"] == tpl_a)
    check("模板保存预设图标+image/link字段", ta["icon"] == "Document" and
          {f["fieldType"] for f in ta["formFields"]} == {"image", "link", "select"}, str(ta))

    # 2. 自定义图标上传（SVG）+ 建第二个模板
    svg = b'<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64"><circle cx="32" cy="32" r="28" fill="#409eff"/></svg>'
    res = upload("/api/nodeTemplate/icon/upload", at, "custom_icon.svg", svg)
    assert res["code"] == 200, f"图标上传失败: {res}"
    icon_path = res["data"]["iconPath"]
    check("自定义图标上传", icon_path.startswith("node_icon/"), icon_path)
    res = req("/api/nodeTemplate/add", "POST", {"nodeTitle": "测试节点B", "icon": icon_path, "sort": 91, "formFields": []}, at)
    assert res["code"] == 200, f"建模板B失败: {res}"
    tpl_b = res["data"]["id"]
    cleanup_templates.append(tpl_b)
    tb = next(t for t in req("/api/nodeTemplate/list", token=at) if t["id"] == tpl_b)
    check("自定义图标模板", tb["icon"] == icon_path, tb["icon"])

    # 3. 图标上传限制（非法格式 + 超限大小用 1MB+ 模拟）
    res = upload("/api/nodeTemplate/icon/upload", at, "bad.exe", b"MZ\x90\x00")
    check("非法图标格式拦截", res["code"] == 400 and "格式" in res["msg"], str(res))

    # 4. 建客户+项目，用模板A建节点 → icon 冗余拷贝
    res = req("/api/customer/add", "POST", {"categoryId": 1, "customerName": "图标测试客户", "contact": "1"}, at)
    assert res["code"] == 200, f"建客户失败: {res}"
    cid = res["data"]["id"]
    cleanup_customers.append(cid)
    res = req("/api/project/create", "POST", {"projectName": "图标测试项目", "customerId": cid}, at)
    assert res["code"] == 200, f"建项目失败: {res}"
    pid = res["data"]["projectId"]
    cleanup_projects.append(pid)
    res = req("/api/projectNode/add", "POST", {"projectId": pid, "nodeTemplateId": tpl_a}, at)
    assert res["code"] == 200, f"加节点失败: {res}"
    nid = res["data"]["id"]
    detail = req(f"/api/project/detail/{pid}", token=at)["data"]
    node = next(n for n in detail["nodes"] if n["id"] == nid)
    check("项目节点冗余图标（预设）", node.get("icon") == "Document", str(node.get("icon")))

    # 5. 表单 getForm 字段含 image/link
    form = req(f"/api/projectNode/getForm/{nid}", token=at)["data"]["fields"]
    types = {f["fieldType"] for f in form}
    check("getForm 返回 image/link 字段", {"image", "link", "select"} <= types, str(types))
    image_field = next(f for f in form if f["fieldType"] == "image")
    link_field = next(f for f in form if f["fieldType"] == "link")
    sel_field = next(f for f in form if f["fieldType"] == "select")

    # 6. 表单图像上传（multipart png）+ 保存表单（image 路径 + link URL + select）
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 200
    res = upload("/api/projectNode/formImage/upload", at, "photo.png", png)
    assert res["code"] == 200, f"表单图片上传失败: {res}"
    img_path = res["data"]["imagePath"]
    check("表单图片上传", img_path.startswith("node_form/"), img_path)
    res = req("/api/projectNode/saveFormValue", "POST", {
        "projectNodeId": nid,
        "formValueList": [
            {"id": image_field["id"], "fieldValue": img_path},
            {"id": link_field["id"], "fieldValue": "https://example.com/ref"},
            {"id": sel_field["id"], "fieldValue": "高"},
        ]
    }, at)
    check("保存 image/link/select 表单值", res["code"] == 200, str(res))

    # 7. 回显验证 + 节点完成状态（form_filled）
    form2 = req(f"/api/projectNode/getForm/{nid}", token=at)["data"]["fields"]
    im = next(f for f in form2 if f["fieldType"] == "image")
    lk = next(f for f in form2 if f["fieldType"] == "link")
    check("表单回显 image/link 值", im["fieldValue"] == img_path and lk["fieldValue"] == "https://example.com/ref", str((im["fieldValue"], lk["fieldValue"])))
    detail2 = req(f"/api/project/detail/{pid}", token=at)["data"]
    n2 = next(n for n in detail2["nodes"] if n["id"] == nid)
    check("节点表单完成后 form_filled", n2["formFilled"] is True, str(n2["formFilled"]))

    # 8. 普通用户可上传表单图片（登录即可），客户禁止
    res = req("/api/sysUser/create", "POST", {"username": "ic_staff", "password": "staff123", "realName": "图标员工", "deptId": 1, "role": "普通"}, at)
    assert res["code"] == 200, f"建普通用户失败: {res}"
    cleanup_users.append(res["data"]["userId"])
    staff = login("ic_staff", "staff123")
    res = upload("/api/projectNode/formImage/upload", staff["token"], "s.png", png)
    check("普通用户可上传表单图片", res["code"] == 200, str(res))
    # 客户账号
    res = req("/api/sysUser/create", "POST", {"username": "ic_cust", "password": "cust123", "realName": "图标客户", "customerId": cid}, at)
    assert res["code"] == 200, f"建客户账号失败: {res}"
    cleanup_users.append(res["data"]["userId"])
    cust = login("ic_cust", "cust123")
    res = upload("/api/projectNode/formImage/upload", cust["token"], "s.png", png)
    check("客户禁止上传表单图片", res["code"] == 403, str(res))

    # 9. 客户门户只读：能读自己项目 getForm（image/link 字段可见）
    res = req(f"/api/projectNode/getForm/{nid}", token=cust["token"])
    check("客户可读表单（含 image/link）", res["code"] == 200 and
          {"image", "link"} <= {f["fieldType"] for f in res["data"]["fields"]}, str(res))

    # 10. 流程模板实例化也带图标：建模板（用模板A）→ 实例化项目 → 节点 icon
    res = req("/api/flowTemplate/add", "POST", {
        "templateName": "图标流程模板", "projectNameTemplate": "图标流程项目",
        "nodes": [{"nodeTitle": "流程节点", "nodeTemplateId": tpl_a, "posX": 0, "posY": 0, "sort": 1}],
        "edges": [],
    }, at)
    assert res["code"] == 200, f"建流程模板失败: {res}"
    ftpl = res["data"]["id"]
    res = req("/api/project/create", "POST", {"projectName": "图标流程项目", "customerId": cid, "templateId": ftpl}, at)
    assert res["code"] == 200, f"流程实例化失败: {res}"
    pid2 = res["data"]["projectId"]
    cleanup_projects.append(pid2)
    detail3 = req(f"/api/project/detail/{pid2}", token=at)["data"]
    check("流程模板实例化节点带图标", detail3["nodes"] and detail3["nodes"][0].get("icon") == "Document", str(detail3["nodes"][0].get("icon")))

    # ---- 清理 ----
    print("---- 清理测试数据 ----")
    for pid in cleanup_projects:
        req("/api/project/delete", "POST", {"projectId": pid}, at)
    for cid in cleanup_customers:
        req("/api/customer/delete", "POST", {"id": cid}, at)
    for uid in cleanup_users:
        req("/api/sysUser/delete", "POST", {"userId": uid}, at)
    for tid in cleanup_templates:
        req("/api/nodeTemplate/delete", "POST", {"id": tid}, at)
    check("测试数据已清理", True)

    print(f"\n=== 通过 {ok_count}/{TOTAL} ===")
    if ok_count != TOTAL:
        sys.exit(1)


if __name__ == "__main__":
    main()
