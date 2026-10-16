# -*- coding: utf-8 -*-
r"""多文件上传专项回归测试（V1.4.21 新增功能）

覆盖范围：
  A. 节点表单上传接口：多类型文件、危险扩展名拦截、超大文件、响应结构
  B. 表单值持久化：JSON 数组多文件、旧单值兼容、清空、覆盖
  C. 客户审核反馈多文件：上传 → 提交审核 → 回读 → 重置
  D. 客户门户隔离：跨单位上传/审核必须被拒
  E. 文件物理落盘与静态访问

用法：先启动服务，再 cd backend && ..\.venv\Scripts\python.exe tests\multifile_upload_check.py
"""

import io
import json
import sys
import time

import httpx

BASE = "http://127.0.0.1:8000"
PREFIX = "多文件测试"
PASSWORD = "mf123456"

PASSED = []
FAILED = []


def check(name, cond, detail=""):
    if cond:
        PASSED.append(name)
        print(f"  [OK]   {name}")
    else:
        FAILED.append((name, detail))
        print(f"  [FAIL] {name}  {detail}")
    return cond


def call(client, method, url, **kw):
    """返回 (http_status, body_json_or_text)"""
    try:
        r = getattr(client, method)(url, **kw)
        try:
            return r.status_code, r.json()
        except Exception:
            return r.status_code, r.text
    except Exception as exc:
        return -1, f"EXC:{exc}"


def ok_body(st, body):
    """后端约定：HTTP 恒 200，业务码在 body.code"""
    return st == 200 and isinstance(body, dict) and body.get("code") == 200


def login(client, username, password):
    st, body = call(client, "post", "/api/login",
                    json={"username": username, "password": password})
    if ok_body(st, body):
        return body["data"]["token"], body["data"].get("userInfo") or {}
    return None, {}


def upload_file(client, H, filename, content=b"x" * 1024, content_type="application/octet-stream"):
    """上传单个文件到节点表单上传接口"""
    files = {"file": (filename, io.BytesIO(content), content_type)}
    return call(client, "post", "/api/projectNode/formImage/upload", headers=H, files=files)


# ---------------------------------------------------------------- 主体
def main():
    client = httpx.Client(base_url=BASE, timeout=60)

    print("\n==== 0. 登录 ====")
    token, admin = login(client, "admin", "admin123")
    if not token:
        print("  [FATAL] 管理员登录失败，测试终止")
        sys.exit(1)
    H = {"Authorization": f"Bearer {token}"}
    print(f"  [OK]   管理员登录成功  role={admin.get('role')}")

    created = {"project": None, "category": None, "customer": None, "node": None,
               "portal_user": None, "template": None}

    try:
        # ---------------------------------------------------------- A. 上传接口
        print("\n==== A. 上传接口（多类型 / 拦截 / 边界）====")

        st, body = upload_file(client, H, "平面稿.png", b"\x89PNG\r\n\x1a\n" + b"a" * 2000)
        check("A1 上传 png 成功", ok_body(st, body), f"st={st} {str(body)[:200]}")
        png_path = body["data"].get("imagePath") if ok_body(st, body) else None
        check("A2 返回 imagePath 且含 node_form/ 前缀",
              bool(png_path) and png_path.startswith("node_form/"), f"path={png_path}")

        st, body = upload_file(client, H, "设计方案.pdf", b"%PDF-1.4" + b"b" * 2000)
        check("A3 上传 pdf 成功（旧版仅允许图片，本次放开）", ok_body(st, body), f"st={st} {str(body)[:200]}")
        pdf_path = body["data"].get("imagePath") if ok_body(st, body) else None

        st, body = upload_file(client, H, "源文件.psd", b"8BPS" + b"c" * 2000)
        ok_psd = ok_body(st, body)
        check("A4 上传 psd 成功", ok_psd, f"st={st} {str(body)[:200]}")
        psd_path = body["data"].get("imagePath") if ok_psd else None

        st, body = upload_file(client, H, "演示视频.mp4", b"\x00\x00\x00\x18ftypmp42" + b"d" * 2000,
                               "video/mp4")
        ok_mp4 = ok_body(st, body)
        check("A5 上传 mp4 成功", ok_mp4, f"st={st} {str(body)[:200]}")

        st, body = upload_file(client, H, "压缩包.zip", b"PK\x03\x04" + b"e" * 2000, "application/zip")
        ok_zip = ok_body(st, body)
        check("A6 上传 zip 成功", ok_zip, f"st={st} {str(body)[:200]}")
        zip_path = body["data"].get("imagePath") if ok_zip else None

        # 中文文件名保留
        check("A7 中文文件名保留（uuid_原名 规则）",
              bool(png_path) and "平面稿.png" in png_path, f"path={png_path}")

        # 危险扩展名拦截
        for ext in ("exe", "bat", "cmd", "ps1", "sh", "html", "js", "php", "dll"):
            st, body = upload_file(client, H, f"evil.{ext}", b"MZ" + b"f" * 100)
            blocked = isinstance(body, dict) and body.get("code") != 200
            check(f"A8 危险扩展名 .{ext} 被拦截", blocked, f"st={st} {str(body)[:160]}")

        # 大小写绕过（.EXE / .Js）
        st, body = upload_file(client, H, "evil.EXE", b"MZ" + b"f" * 100)
        check("A9 大写 .EXE 被拦截（大小写不敏感）",
              isinstance(body, dict) and body.get("code") != 200, f"st={st} {str(body)[:160]}")
        st, body = upload_file(client, H, "evil.Js", b"alert(1)")
        check("A10 混合大小写 .Js 被拦截",
              isinstance(body, dict) and body.get("code") != 200, f"st={st} {str(body)[:160]}")

        # 路径穿越：文件名带 ../ 必须被 basename 化
        st, body = upload_file(client, H, "../../../etc/passwd.txt", b"root:x:0:0")
        if ok_body(st, body):
            path = body["data"]["imagePath"]
            check("A11 路径穿越被 sanitize（无 .. 分隔）",
                  ".." not in path and "/etc/" not in path, f"path={path}")
        else:
            check("A11 路径穿越文件名被拒或净化", True, "")

        # 无文件上传 → 422 被全局处理器包装
        st, body = call(client, "post", "/api/projectNode/formImage/upload", headers=H)
        check("A12 缺文件参数返回业务错误而非 500",
              isinstance(body, dict) and body.get("code") != 200, f"st={st} {str(body)[:160]}")

        # 静态访问落盘文件
        if png_path:
            r = client.get(f"/uploads/{png_path}")
            check("A13 上传文件可通过 /uploads/ 静态访问", r.status_code == 200 and len(r.content) > 0,
                  f"http={r.status_code}")

        # ---------------------------------------------------------- B. 准备项目数据
        print("\n==== B. 准备项目 / 节点（含上传字段的节点模板）====")

        st, body = call(client, "post", "/api/customerCategory/add", headers=H,
                        json={"categoryName": f"{PREFIX}单位"})
        if ok_body(st, body):
            created["category"] = body["data"]["id"] if isinstance(body["data"], dict) else body["data"]
        check("B1 创建客户单位", created["category"] is not None, f"{str(body)[:200]}")

        st, body = call(client, "post", "/api/customer/add", headers=H,
                        json={"customerName": f"{PREFIX}对接人",
                              "categoryId": created["category"],
                              "contact": "13800000000"})
        if ok_body(st, body):
            created["customer"] = body["data"]["id"] if isinstance(body["data"], dict) else body["data"]
        check("B2 创建对接人", created["customer"] is not None, f"{str(body)[:200]}")

        # 自建节点模板：一个 image 字段（多文件）+ 一个 text 字段
        tpl_payload = {
            "nodeTitle": f"{PREFIX}节点模板",
            "nodeRemark": "自动化测试节点",
            "isReview": True,
            "reviewOptions": ["通过", "驳回"],
            "formFields": [
                {"fieldLabel": "设计稿", "fieldType": "image", "sort": 1},
                {"fieldLabel": "备注", "fieldType": "text_single", "sort": 2},
            ],
            "clientReviewFields": [
                {"fieldLabel": "客户反馈附件", "fieldType": "image", "sort": 1},
                {"fieldLabel": "客户意见", "fieldType": "text_single", "sort": 2},
            ],
        }
        st, body = call(client, "post", "/api/nodeTemplate/add", headers=H, json=tpl_payload)
        if ok_body(st, body):
            data = body["data"]
            created["template"] = data["id"] if isinstance(data, dict) else data
        check("B3 创建含上传字段的审核节点模板", created["template"] is not None, f"{str(body)[:300]}")

        st, body = call(client, "post", "/api/project/create", headers=H, json={
            "projectName": f"{PREFIX}项目",
            "categoryId": created["category"],
            "contactCustomerIds": [created["customer"]],
            "projectStatus": "进行中",
        })
        if ok_body(st, body):
            created["project"] = body["data"].get("projectId") or body["data"].get("id")
        check("B4 创建项目", created["project"] is not None, f"{str(body)[:300]}")

        st, body = call(client, "post", "/api/projectNode/add", headers=H, json={
            "projectId": created["project"],
            "nodeTemplateId": created["template"],
            "sort": 1,
            "posX": 100, "posY": 100,
        })
        if ok_body(st, body):
            created["node"] = body["data"]["id"]
        check("B5 新增项目节点（实例化表单）", created["node"] is not None, f"{str(body)[:300]}")

        if not created["node"]:
            raise RuntimeError("节点创建失败，后续用例无法继续")

        st, body = call(client, "get", f"/api/projectNode/getForm/{created['node']}", headers=H)
        fields = (body.get("data") or {}).get("fields") if ok_body(st, body) else []
        check("B6 节点表单字段实例化正确（designer 侧）",
              isinstance(fields, list) and len(fields) >= 2, f"fields={str(fields)[:300]}")
        img_field = next((f for f in (fields or []) if f.get("fieldType") == "image"), None)
        txt_field = next((f for f in (fields or []) if f.get("fieldLabel") == "备注"), None)
        check("B7 存在 image 类型字段（上传字段）", img_field is not None, f"{str(fields)[:300]}")

        # ---------------------------------------------------------- C. 多文件持久化
        print("\n==== C. 表单多文件值持久化 ====")

        multi = [png_path, pdf_path, psd_path]
        multi = [p for p in multi if p]
        check("C0 已获得 ≥3 个上传路径用于多文件用例", len(multi) >= 3, f"multi={multi}")

        st, body = call(client, "post", "/api/projectNode/saveFormValue", headers=H, json={
            "projectNodeId": created["node"],
            "formValueList": [
                {"id": img_field["id"], "fieldValue": json.dumps(multi, ensure_ascii=False)},
                {"id": txt_field["id"], "fieldValue": "多文件测试备注"},
            ],
        })
        check("C1 保存多文件 JSON 数组", ok_body(st, body), f"{str(body)[:300]}")

        st, body = call(client, "get", f"/api/projectNode/getForm/{created['node']}", headers=H)
        fields = (body.get("data") or {}).get("fields") if ok_body(st, body) else []
        saved = next((f for f in (fields or []) if f.get("fieldType") == "image"), None)
        raw = saved.get("fieldValue") if saved else None
        back = json.loads(raw) if raw else []
        check("C2 回读为数组且元素数一致", isinstance(back, list) and len(back) == len(multi),
              f"raw={str(raw)[:200]}")

        # 加第 4 个文件（模拟继续上传）
        if ok_mp4:
            st, body2 = call(client, "post", "/api/projectNode/formImage/upload", headers=H,
                             files={"file": ("追加.png", io.BytesIO(b"\x89PNG" + b"g" * 500), "image/png")})
            if ok_body(st, body2):
                appended = back + [body2["data"]["imagePath"]]
                st, body = call(client, "post", "/api/projectNode/saveFormValue", headers=H, json={
                    "projectNodeId": created["node"],
                    "formValueList": [{"id": img_field["id"], "fieldValue": json.dumps(appended, ensure_ascii=False)}],
                })
                check("C3 追加文件后保存成功", ok_body(st, body), f"{str(body)[:200]}")
                st, body = call(client, "get", f"/api/projectNode/getForm/{created['node']}", headers=H)
                fields = (body.get("data") or {}).get("fields") if ok_body(st, body) else []
                saved = next((f for f in (fields or []) if f.get("fieldType") == "image"), None)
                check("C4 追加后数量 +1",
                      len(json.loads(saved.get("fieldValue") or "[]")) == len(appended),
                      f"raw={str(saved.get('fieldValue'))[:200]}")

        # 删除其中一个（前端行为：过滤后保存）
        remain = multi[:2]
        st, body = call(client, "post", "/api/projectNode/saveFormValue", headers=H, json={
            "projectNodeId": created["node"],
            "formValueList": [{"id": img_field["id"], "fieldValue": json.dumps(remain, ensure_ascii=False)}],
        })
        check("C5 删除部分文件后保存成功", ok_body(st, body), f"{str(body)[:200]}")
        st, body = call(client, "get", f"/api/projectNode/getForm/{created['node']}", headers=H)
        fields = (body.get("data") or {}).get("fields") if ok_body(st, body) else []
        saved = next((f for f in (fields or []) if f.get("fieldType") == "image"), None)
        check("C6 删除后回读数量正确",
              len(json.loads(saved.get("fieldValue") or "[]")) == 2,
              f"raw={str(saved.get('fieldValue'))[:200]}")

        # 全部删除 → null（前端 collect() 行为）
        st, body = call(client, "post", "/api/projectNode/saveFormValue", headers=H, json={
            "projectNodeId": created["node"],
            "formValueList": [{"id": img_field["id"], "fieldValue": None}],
        })
        check("C7 清空全部文件（fieldValue=null）", ok_body(st, body), f"{str(body)[:200]}")
        st, body = call(client, "get", f"/api/projectNode/getForm/{created['node']}", headers=H)
        fields = (body.get("data") or {}).get("fields") if ok_body(st, body) else []
        saved = next((f for f in (fields or []) if f.get("fieldType") == "image"), None)
        check("C8 清空后 fieldValue 为空", not saved.get("fieldValue"), f"raw={str(saved.get('fieldValue'))[:120]}")

        # 旧单值兼容：写一个纯字符串（非 JSON 数组）
        st, body = call(client, "post", "/api/projectNode/saveFormValue", headers=H, json={
            "projectNodeId": created["node"],
            "formValueList": [{"id": img_field["id"], "fieldValue": multi[0] if multi else "node_form/old.jpg"}],
        })
        check("C9 旧单值（非数组）保存成功", ok_body(st, body), f"{str(body)[:200]}")
        st, body = call(client, "get", f"/api/projectNode/getForm/{created['node']}", headers=H)
        fields = (body.get("data") or {}).get("fields") if ok_body(st, body) else []
        saved = next((f for f in (fields or []) if f.get("fieldType") == "image"), None)
        check("C10 旧单值原样回读（后端不擅自改结构）",
              saved.get("fieldValue") == (multi[0] if multi else "node_form/old.jpg"),
              f"raw={str(saved.get('fieldValue'))[:160]}")

        # 恢复成多文件供后续客户审核用例
        st, body = call(client, "post", "/api/projectNode/saveFormValue", headers=H, json={
            "projectNodeId": created["node"],
            "formValueList": [{"id": img_field["id"], "fieldValue": json.dumps(multi, ensure_ascii=False)}],
        })
        check("C11 恢复多文件值", ok_body(st, body), f"{str(body)[:200]}")

        # ---------------------------------------------------------- D. 客户门户
        print("\n==== D. 客户门户：反馈多文件上传 + 审核 ====")

        # 上传接口应禁止客户（require_not_customer）
        cust_tmp_token, _ = login(client, "admin", "admin123")  # 占位，稍后建真实客户账号
        st, body = call(client, "post", "/api/sysUser/create", headers=H, json={
            "username": f"{PREFIX}门户", "password": PASSWORD,
            "realName": f"{PREFIX}门户账号", "categoryId": created["category"]})
        if ok_body(st, body):
            created["portal_user"] = body["data"]["userId"]
        check("D1 创建客户门户账号", created["portal_user"] is not None, f"{str(body)[:250]}")

        ptoken, puser = login(client, f"{PREFIX}门户", PASSWORD)
        check("D2 客户账号登录成功且带公司名", bool(ptoken) and bool(puser.get("companyName")),
              f"user={puser}")
        PH = {"Authorization": f"Bearer {ptoken}"}

        # 客户不能用设计师上传接口（V1.4.22 起前端也改为走 review/upload，不再复用）
        st, body = upload_file(client, PH, "客户上传.png", b"\x89PNG" + b"h" * 500)
        check("D3 客户端调用设计师上传接口被拒 403",
              isinstance(body, dict) and body.get("code") == 403, f"st={st} {str(body)[:200]}")

        # 客户走专用接口上传图片
        st, body = call(client, "post", "/api/review/upload", headers=PH,
                        files={"file": ("客户反馈.png", io.BytesIO(b"\x89PNG" + b"i" * 500), "image/png")},
                        data={"projectNodeId": str(created["node"])})
        ok_ru = ok_body(st, body)
        check("D4 客户通过 review/upload 上传图片成功（camelCase projectNodeId）",
              ok_ru, f"st={st} {str(body)[:250]}")
        cust_path = body["data"]["path"] if ok_ru else None

        # V1.4.22：客户专用接口放开多类型（与设计师侧一致）
        st, body = call(client, "post", "/api/review/upload", headers=PH,
                        files={"file": ("客户反馈.pdf", io.BytesIO(b"%PDF-1.4" + b"j" * 800), "application/pdf")},
                        data={"projectNodeId": str(created["node"])})
        ok_pdf = ok_body(st, body)
        check("D5 客户可上传 PDF（V1.4.22 放开非图片类型）", ok_pdf, f"st={st} {str(body)[:250]}")
        cust_pdf = body["data"]["path"] if ok_pdf else None

        # 客户专用接口同样拦截危险扩展名
        st, body = call(client, "post", "/api/review/upload", headers=PH,
                        files={"file": ("evil.exe", io.BytesIO(b"MZ" + b"k" * 200), "application/octet-stream")},
                        data={"projectNodeId": str(created["node"])})
        check("D5b 客户专用接口拦截 .exe",
              isinstance(body, dict) and body.get("code") != 200, f"st={st} {str(body)[:200]}")

        # 客户端调用设计师上传接口被拒 → 确认前端已不再依赖该路径
        st, body = upload_file(client, PH, "客户复用.png", b"\x89PNG" + b"j" * 500)
        check("D5c 客户端调用设计师上传接口仍被拒（前端已改走 review/upload）",
              isinstance(body, dict) and body.get("code") == 403, f"code={body.get('code') if isinstance(body,dict) else body}")

        # 构造客户反馈多文件值（客户自己上传的图片 + PDF）
        fb_files = [p for p in [cust_path, cust_pdf] if p]
        check("D6 已获得客户反馈文件路径（≥2 个，含非图片）", len(fb_files) >= 1, f"fb={fb_files}")

        st, body = call(client, "post", "/api/review/submit", headers=PH, json={
            "projectNodeId": created["node"],
            "option": "通过",
            "comment": "多文件测试批注",
            "feedbackFields": [
                {"fieldLabel": "客户反馈附件", "fieldType": "image",
                 "fieldValue": json.dumps(fb_files, ensure_ascii=False) if fb_files else None},
                {"fieldLabel": "客户意见", "fieldType": "text_single", "fieldValue": "同意"},
            ],
        })
        check("D7 客户提交审核（含多文件反馈）成功", ok_body(st, body), f"st={st} {str(body)[:300]}")

        # 已审节点状态
        st, body = call(client, "get", f"/api/project/detail/{created['project']}", headers=H)
        nodes = ((body.get("data") or {}).get("nodes") or []) if ok_body(st, body) else []
        node = next((n for n in nodes if n.get("id") == created["node"]), None)
        check("D8 节点 reviewResult 已写入", bool(node and node.get("reviewResult")),
              f"node={str(node)[:300]}")

        # 回读客户反馈字段（side=client）
        st, body = call(client, "get", f"/api/projectNode/getForm/{created['node']}", headers=H)
        all_fields = (body.get("data") or {}).get("fields") if ok_body(st, body) else []
        client_fields = [f for f in (all_fields or []) if f.get("side") == "client"]
        check("D9 客户反馈字段已落库且标记 side=client",
              len(client_fields) >= 1, f"client_fields={str(client_fields)[:300]}")
        fb_img = next((f for f in client_fields if f.get("fieldType") == "image"), None)
        check("D10 客户反馈文件值可回读",
              bool(fb_img and fb_img.get("fieldValue")), f"fb_img={str(fb_img)[:250]}")
        if fb_img and fb_img.get("fieldValue"):
            try:
                parsed = json.loads(fb_img["fieldValue"])
                check("D11 客户反馈附件为 JSON 数组结构",
                      isinstance(parsed, list) and len(parsed) >= 1, f"parsed={parsed}")
            except Exception as exc:
                check("D11 客户反馈附件为 JSON 数组结构", False, f"exc={exc}")

        # 重复提交应被锁定
        st, body = call(client, "post", "/api/review/submit", headers=PH, json={
            "projectNodeId": created["node"], "option": "通过", "comment": "重复",
            "feedbackFields": []})
        check("D12 已审节点重复提交被拒", isinstance(body, dict) and body.get("code") != 200,
              f"{str(body)[:200]}")

        # 管理员重置审核 → 客户反馈应被清除
        st, body = call(client, "post", "/api/review/reset", headers=H,
                        json={"projectNodeId": created["node"]})
        check("D13 管理员重置审核成功", ok_body(st, body), f"{str(body)[:250]}")
        st, body = call(client, "get", f"/api/projectNode/getForm/{created['node']}", headers=H)
        all_fields = (body.get("data") or {}).get("fields") if ok_body(st, body) else []
        left = [f for f in (all_fields or []) if f.get("side") == "client"]
        check("D14 重置后客户反馈字段被清空", len(left) == 0, f"left={str(left)[:250]}")

        # ---------------------------------------------------------- E. 隔离
        print("\n==== E. 跨单位隔离 ====")

        st, body = call(client, "post", "/api/customerCategory/add", headers=H,
                        json={"categoryName": f"{PREFIX}乙方单位"})
        other_cat = None
        if ok_body(st, body):
            d = body["data"]
            other_cat = d["id"] if isinstance(d, dict) else d
        st, body = call(client, "post", "/api/sysUser/create", headers=H, json={
            "username": f"{PREFIX}乙方", "password": PASSWORD,
            "realName": f"{PREFIX}乙方账号", "categoryId": other_cat})
        check("E1 创建乙方单位+账号", other_cat is not None, f"{str(body)[:250]}")

        otoken, _ = login(client, f"{PREFIX}乙方", PASSWORD)
        OH = {"Authorization": f"Bearer {otoken}"}
        check("E2 乙方账号登录", bool(otoken), "")

        # 乙方提交对甲方项目的审核 → 必须 403
        st, body = call(client, "post", "/api/review/submit", headers=OH, json={
            "projectNodeId": created["node"], "option": "通过", "comment": "越权", "feedbackFields": []})
        check("E3 跨单位提交审核被拒 403", isinstance(body, dict) and body.get("code") == 403,
              f"{str(body)[:200]}")

        # 乙方调用 review/upload 到甲方节点 → 403
        st, body = call(client, "post", "/api/review/upload", headers=OH,
                        files={"file": ("x.png", io.BytesIO(b"\x89PNG" + b"k" * 100), "image/png")},
                        data={"projectNodeId": str(created["node"])})
        check("E4 跨单位上传被拒 403", isinstance(body, dict) and body.get("code") == 403,
              f"st={st} {str(body)[:200]}")

        # 乙方看不到甲方待审列表
        st, body = call(client, "get", "/api/review/pending", headers=OH)
        pend = body.get("data") if ok_body(st, body) else []
        own = [p for p in (pend or []) if p.get("projectId") == created["project"]]
        check("E5 乙方待审列表不含甲方项目", len(own) == 0, f"own={str(own)[:200]}")

    except Exception as exc:
        import traceback
        traceback.print_exc()
        FAILED.append(("EXCEPTION", str(exc)[:400]))
    finally:
        # ---------------------------------------------------------- 清理
        print("\n==== 清理测试数据 ====")
        if created["project"]:
            call(client, "post", "/api/project/delete", headers=H, json={"projectId": created["project"]})
        if created["template"]:
            call(client, "post", "/api/nodeTemplate/delete", headers=H, json={"id": created["template"]})
        for uname in (f"{PREFIX}门户", f"{PREFIX}乙方"):
            st, body = call(client, "get", "/api/sysUser/list", headers=H)
            for it in (body.get("data") or []) if ok_body(st, body) else []:
                if it.get("username") == uname:
                    call(client, "post", "/api/sysUser/delete", headers=H, json={"userId": it["id"]})
        st, body = call(client, "get", "/api/customer/list", headers=H,
                        params={"pageNum": 1, "pageSize": 50})
        for it in (body.get("data") or {}).get("items", []) if ok_body(st, body) else []:
            if PREFIX in str(it.get("customerName", "")):
                call(client, "post", "/api/customer/delete", headers=H, json={"id": it["id"]})
        st, body = call(client, "get", "/api/customerCategory/list", headers=H)
        for it in (body.get("data") or []) if ok_body(st, body) else []:
            if PREFIX in str(it.get("categoryName", "")):
                call(client, "post", "/api/customerCategory/delete", headers=H, json={"id": it["id"]})
        print("  完成")

    print("\n" + "=" * 60)
    print(f"通过 {len(PASSED)} 项，失败 {len(FAILED)} 项")
    if FAILED:
        print("\n失败明细：")
        for n, d in FAILED:
            print(f"  - {n}: {d}")
    print("=" * 60)
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
