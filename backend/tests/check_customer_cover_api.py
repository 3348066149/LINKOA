# -*- coding: utf-8 -*-
"""客户模块自检：列表 contact/coverImage 字段 / 新增客户带联系方式 / 封面上传 / 静态访问 / 移除 / 格式拦截"""
import base64
import json
import sys
import urllib.request

BASE = "http://localhost:8000"
PNG_1PX = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)


def post_json(path, body, token=None):
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode())


def get(path, token=None):
    req = urllib.request.Request(BASE + path)
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode())


def raw_get(path):
    req = urllib.request.Request(BASE + path)
    with urllib.request.urlopen(req) as r:
        return r.status, r.read()


def multipart(path, fields, files, token):
    boundary = "----lkoa-test-boundary"
    parts = []
    for k, v in fields.items():
        parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode())
    for name, (fname, ctype, data) in files.items():
        parts.append(
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"; filename=\"{fname}\"\r\n"
            f"Content-Type: {ctype}\r\n\r\n".encode() + data + b"\r\n"
        )
    parts.append(f"--{boundary}--\r\n".encode())
    body = b"".join(parts)
    req = urllib.request.Request(BASE + path, data=body,
                                 headers={"Content-Type": f"multipart/form-data; boundary={boundary}",
                                          "Authorization": "Bearer " + token})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode())


def main():
    ok = 0
    total = 9

    # 0. 登录
    res = post_json("/api/login", {"username": "admin", "password": "admin123"})
    assert res["code"] == 200, f"登录失败: {res}"
    token = res["data"]["token"]
    print("0. 登录 OK")
    ok += 1

    # 1. 客户列表返回 contact / coverImage 字段
    res = get("/api/customer/list?pageNum=1&pageSize=10", token)
    items = res["data"]["items"]
    assert items, "客户列表为空，无法校验字段"
    first = items[0]
    assert "contact" in first and "coverImage" in first, f"缺少新字段: {first}"
    print(f"1. 列表新字段 OK（共 {res['data']['total']} 条，首条 contact={first.get('contact')}）")
    ok += 1
    cid = first["id"]
    # 记录原始值，测试结束后还原，避免污染真实数据
    origin = {
        "categoryId": first["categoryId"],
        "customerName": first["customerName"],
        "contact": first.get("contact"),
        "remark": first.get("remark") or ""
    }

    # 2. 更新联系方式
    res = post_json("/api/customer/update", {
        "id": cid, "categoryId": first["categoryId"],
        "customerName": first["customerName"],
        "contact": "138-0000-1234 / 微信 lk_test",
        "remark": first.get("remark") or ""
    }, token)
    assert res["code"] == 200, f"更新失败: {res}"
    detail = get(f"/api/customer/detail/{cid}", token)
    assert detail["data"]["contact"] == "138-0000-1234 / 微信 lk_test", f"联系方式未保存: {detail}"
    print("2. 联系方式保存 OK")
    ok += 1

    # 3. 上传封面图
    res = multipart("/api/customer/cover/upload", {"customerId": str(cid)},
                    {"file": ("cover_test.png", "image/png", PNG_1PX)}, token)
    assert res["code"] == 200, f"上传失败: {res}"
    cover_path = res["data"]["coverImage"]
    assert cover_path.startswith("cover/"), f"路径异常: {cover_path}"
    print(f"3. 封面上传 OK（{cover_path}）")
    ok += 1

    # 4. 静态访问封面图
    status, data = raw_get("/uploads/" + cover_path)
    assert status == 200 and len(data) > 0, f"静态访问失败: {status}"
    print(f"4. 封面静态访问 OK（HTTP {status}, {len(data)} bytes）")
    ok += 1

    # 5. 列表回传 coverImage
    res = get("/api/customer/list?pageNum=1&pageSize=10", token)
    row = next(i for i in res["data"]["items"] if i["id"] == cid)
    assert row["coverImage"] == cover_path, f"列表未回传: {row}"
    print("5. 列表回传 coverImage OK")
    ok += 1

    # 6. 非法格式拦截（约定：HTTP 200 + body.code=400）
    res = multipart("/api/customer/cover/upload", {"customerId": str(cid)},
                    {"file": ("bad.txt", "text/plain", b"not an image")}, token)
    assert res["code"] == 400 and "格式" in res["msg"], f"未拦截非法格式: {res}"
    print(f"6. 非法格式拦截 OK（{res['msg']}）")
    ok += 1

    # 7. 移除封面
    res = post_json("/api/customer/cover/remove", {"customerId": cid}, token)
    assert res["code"] == 200, f"移除失败: {res}"
    detail = get(f"/api/customer/detail/{cid}", token)
    assert detail["data"]["coverImage"] is None, f"封面未清空: {detail}"
    print("7. 移除封面 OK")
    ok += 1

    # 8. 数据还原：把联系方式恢复为测试前的值
    post_json("/api/customer/update", {"id": cid, **origin}, token)
    after = get(f"/api/customer/detail/{cid}", token)["data"]
    assert after["contact"] == origin["contact"] and after["coverImage"] is None, f"数据未还原: {after}"
    print("8. 测试数据已还原 OK")
    ok += 1

    print(f"\n=== 通过 {ok}/{total} ===")
    if ok != total:
        sys.exit(1)


if __name__ == "__main__":
    main()
