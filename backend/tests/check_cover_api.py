# -*- coding: utf-8 -*-
"""接口自检：列表新字段 / 封面上传 / 静态访问 / 移除 / 格式拦截 / 排序"""
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
    ok_count = 0

    # 登录
    token = post_json("/api/login", {"username": "admin", "password": "admin123"})["data"]["token"]
    print("登录 OK")

    # 1. 列表返回 expectTime + coverImage 字段
    data = get("/api/project/list?pageNum=1&pageSize=10", token)["data"]
    item = data["items"][0]
    assert "expectTime" in item and "coverImage" in item, "列表缺少新字段"
    print(f"1. 列表字段 OK（{data['total']} 个项目，expectTime={item['expectTime']}, coverImage={item['coverImage']}）")
    ok_count += 1
    pid = item["id"]

    # 2. 上传封面
    res = multipart("/api/project/cover/upload", {"projectId": str(pid)},
                     {"file": ("cover_test.png", "image/png", PNG_1PX)}, token)
    assert res["code"] == 200, f"上传失败: {res}"
    cover = res["data"]["coverImage"]
    assert cover and cover.startswith("cover/"), f"路径异常: {cover}"
    print(f"2. 封面上传 OK（{cover}）")
    ok_count += 1

    # 3. 静态访问封面
    req = urllib.request.Request(BASE + "/uploads/" + cover)
    with urllib.request.urlopen(req) as r:
        assert r.status == 200 and len(r.read()) == len(PNG_1PX)
    print("3. 封面静态访问 OK")
    ok_count += 1

    # 4. 列表/详情回传 coverImage
    item2 = get("/api/project/list?pageNum=1&pageSize=10", token)["data"]["items"][0]
    detail = get(f"/api/project/detail/{pid}", token)["data"]
    assert item2["coverImage"] == cover and detail["coverImage"] == cover, "coverImage 未回传"
    print("4. 列表+详情回传 coverImage OK")
    ok_count += 1

    # 5. 排序仍正常
    data3 = get("/api/project/list?pageNum=1&pageSize=10&sortField=expectTime&sortOrder=desc", token)["data"]
    print(f"5. 排序接口 OK（total={data3['total']}）")
    ok_count += 1

    # 6. 非图片格式拦截（业务码在 body.code，HTTP 固定 200）
    res_bad = multipart("/api/project/cover/upload", {"projectId": str(pid)},
                        {"file": ("bad.txt", "text/plain", b"not an image")}, token)
    assert res_bad["code"] == 400 and "格式" in res_bad["msg"], f"拦截异常: {res_bad}"
    print(f"6. 非法格式拦截 OK（{res_bad['msg']}）")
    ok_count += 1

    # 7. 移除封面
    post_json("/api/project/cover/remove", {"projectId": pid}, token)
    item3 = get("/api/project/list?pageNum=1&pageSize=10", token)["data"]["items"][0]
    assert item3["coverImage"] is None, "封面未移除"
    print("7. 封面移除 OK")
    ok_count += 1

    print(f"\n全部 {ok_count}/7 项通过")


if __name__ == "__main__":
    main()
