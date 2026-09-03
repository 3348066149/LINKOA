# -*- coding: utf-8 -*-
"""自定义角色自检：角色增删 / 重名与内置名拦截 / 占用拦截 / 自定义角色用户登录权限 / 数据清理"""
import json
import sys
import urllib.request
import urllib.error

BASE = "http://localhost:8000"


def post_json(path, body, token=None):
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    if token:
        req.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return json.loads(e.read().decode())


def get(path, token=None):
    req = urllib.request.Request(BASE + path)
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode())


def main():
    ok = 0
    total = 11
    rd_user_id = None
    role_id = None

    # 0. 登录 admin
    res = post_json("/api/login", {"username": "admin", "password": "admin123"})
    assert res["code"] == 200, f"登录失败: {res}"
    token = res["data"]["token"]
    print("0. 管理员登录 OK")
    ok += 1

    # 1. 角色列表初始为空（若已有残留先清理同名）
    for r in get("/api/sysRole/list", token)["data"]:
        if r["roleName"] == "研发人员" or r["roleName"] == "研发测试":
            post_json("/api/sysRole/delete", {"id": r["id"]}, token)
    res = get("/api/sysRole/list", token)["data"]
    assert isinstance(res, list), f"列表格式异常: {res}"
    print(f"1. 角色列表 OK（当前 {len(res)} 个）")
    ok += 1

    # 2. 添加自定义角色「研发人员」
    res = post_json("/api/sysRole/add", {"roleName": "研发人员"}, token)
    assert res["code"] == 200, f"添加失败: {res}"
    role_id = res["data"]["roleId"]
    print(f"2. 添加角色 OK（id={role_id}）")
    ok += 1

    # 3. 重复添加拦截
    res = post_json("/api/sysRole/add", {"roleName": "研发人员"}, token)
    assert res["code"] == 400 and "已存在" in res["msg"], f"重复添加未拦截: {res}"
    print(f"3. 重名拦截 OK（{res['msg']}）")
    ok += 1

    # 4. 内置角色名拦截
    res = post_json("/api/sysRole/add", {"roleName": "设计师"}, token)
    assert res["code"] == 400 and "内置角色" in res["msg"], f"内置名未拦截: {res}"
    print(f"4. 内置角色名拦截 OK（{res['msg']}）")
    ok += 1

    # 5. 创建使用自定义角色的用户
    res = post_json("/api/sysUser/create", {
        "username": "rd_test", "password": "rd123456",
        "realName": "研发小李", "role": "研发人员"
    }, token)
    assert res["code"] == 200, f"建用户失败: {res}"
    rd_user_id = res["data"]["userId"]
    print(f"5. 用自定义角色建用户 OK（userId={rd_user_id}）")
    ok += 1

    # 6. 使用不存在的角色建用户 → 拦截
    res = post_json("/api/sysUser/create", {
        "username": "ghost_user", "password": "x123456",
        "realName": "幽灵", "role": "不存在的角色"
    }, token)
    assert res["code"] == 400 and "不存在" in res["msg"], f"非法角色未拦截: {res}"
    print(f"6. 非法角色建用户拦截 OK（{res['msg']}）")
    ok += 1

    # 7. 自定义角色用户登录 + 权限验证（等同设计师：能查项目列表、能写节点表单等登录即可操作）
    login = post_json("/api/login", {"username": "rd_test", "password": "rd123456"})
    assert login["code"] == 200, f"自定义角色登录失败: {login}"
    rd_token = login["data"]["token"]
    assert login["data"]["userInfo"]["role"] == "研发人员"
    proj = get("/api/project/list?pageNum=1&pageSize=5", rd_token)
    assert proj["code"] == 200, f"自定义角色查询项目失败: {proj}"
    print(f"7. 自定义角色登录+查询 OK（角色={login['data']['userInfo']['role']}，项目总数={proj['data']['total']}）")
    ok += 1

    # 8. 角色被占用时删除 → 拦截
    res = post_json("/api/sysRole/delete", {"id": role_id}, token)
    assert res["code"] == 400 and "正在被" in res["msg"], f"占用删除未拦截: {res}"
    print(f"8. 占用删除拦截 OK（{res['msg']}）")
    ok += 1

    # 9. 列表返回使用人数
    roles = get("/api/sysRole/list", token)["data"]
    mine = next(r for r in roles if r["roleName"] == "研发人员")
    assert mine["userCount"] == 1, f"使用人数异常: {mine}"
    print(f"9. 使用人数统计 OK（{mine['roleName']}={mine['userCount']} 人）")
    ok += 1

    # 10. 清理：删除测试用户 → 删除角色 → 确认空
    post_json("/api/sysUser/delete", {"userId": rd_user_id}, token)
    post_json("/api/sysRole/delete", {"id": role_id}, token)
    roles = get("/api/sysRole/list", token)["data"]
    assert all(r["roleName"] != "研发人员" for r in roles), f"清理失败: {roles}"
    print("10. 测试数据清理 OK")
    ok += 1

    print(f"\n=== 通过 {ok}/{total} ===")
    if ok != total:
        sys.exit(1)


if __name__ == "__main__":
    main()
