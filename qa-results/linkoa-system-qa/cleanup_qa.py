# -*- coding: utf-8 -*-
"""清理 QA_ 前缀残留测试数据"""
import httpx

BASE = "http://localhost:8000"
c = httpx.Client(base_url=BASE, timeout=30)
r = c.post("/api/login", json={"username": "admin", "password": "admin123"})
token = r.json()["data"]["token"]
H = {"Authorization": f"Bearer {token}"}

# 用户（先删，避免部门占用）
users = c.get("/api/sysUser/list", headers=H).json()["data"]
deleted_users = 0
for u in users:
    if u["username"].startswith("QA_"):
        c.post("/api/sysUser/delete", headers=H, json={"userId": u["id"]})
        deleted_users += 1

# 对接人
custs = c.get("/api/customer/list", headers=H, params={"pageNum": 1, "pageSize": 200}).json()["data"]["items"]
deleted_custs = 0
for cu in custs:
    if cu["customerName"].startswith("QA_"):
        rr = c.post("/api/customer/delete", headers=H, json={"id": cu["id"]})
        deleted_custs += 1

# 客户单位
cats = c.get("/api/customerCategory/list", headers=H).json()["data"]
deleted_cats = 0
for ca in cats:
    if ca["categoryName"].startswith("QA_"):
        rr = c.post("/api/customerCategory/delete", headers=H, json={"id": ca["id"]})
        if rr.json().get("code") == 200:
            deleted_cats += 1

# 项目（先取消归档再删）
projs = c.get('/api/project/list', headers=H, params={'pageNum':1,'pageSize':200}).json()['data']['items']
deleted_projs = 0
for pj in projs:
    if pj['projectName'].startswith('QA_'):
        if pj['projectStatus'] == '已归档':
            c.post('/api/project/unArchive', headers=H, json={'projectId': pj['id']})
        rr = c.post('/api/project/delete', headers=H, json={'projectId': pj['id']})
        if rr.json().get('code') == 200:
            deleted_projs += 1
print(f'cleanup done: projects={deleted_projs} users={deleted_users} customers={deleted_custs} categories={deleted_cats}')

