# -*- coding: utf-8 -*-
"""补执行 TC-CRUD-009：客户评价 submit/reflection/get"""
import json
import uuid
import httpx

BASE = "http://localhost:8000"
PREFIX = "QA_" + uuid.uuid4().hex[:6]
c = httpx.Client(base_url=BASE, timeout=30)
tok = c.post("/api/login", json={"username": "admin", "password": "admin123"}).json()["data"]["token"]
H = {"Authorization": f"Bearer {tok}"}

# 准备：单位→对接人→客户账号→项目→归档
u = c.post("/api/customerCategory/add", headers=H, json={"categoryName": f"{PREFIX}评价单位"}).json()["data"]["id"]
cu = c.post("/api/customer/add", headers=H, json={"categoryId": u, "customerName": f"{PREFIX}评价对接人"}).json()["data"]["id"]
su = c.post("/api/sysUser/create", headers=H, json={"username": f"{PREFIX}client", "password": "qa123456", "realName": "评价客户", "categoryId": u}).json()
if su.get("code") != 200:
    raise SystemExit(f"建客户失败 {su}")
tk = c.post("/api/login", json={"username": f"{PREFIX}client", "password": "qa123456"}).json()["data"]["token"]
TH = {"Authorization": f"Bearer {tk}"}
pj = c.post("/api/project/create", headers=H, json={"projectName": f"{PREFIX}评价项目", "categoryId": u, "contactCustomerIds": [cu]}).json()
pid = pj["data"]["projectId"]
c.post("/api/project/archive", headers=H, json={"projectId": pid})

# 1) 客户 submit（已归档 → 应成功）
sub = c.post("/api/evaluation/submit", headers=TH, json={"projectId": pid, "designScore": 5, "serviceScore": 4, "productScore": 5, "customerRemark": "QA 评价"})
# 2) 重复 submit（应 400）
sub2 = c.post("/api/evaluation/submit", headers=TH, json={"projectId": pid, "designScore": 5, "serviceScore": 5, "productScore": 5, "customerRemark": "重复"})
# 3) get（管理员 / 客户）
g1 = c.get(f"/api/evaluation/{pid}", headers=H)
g2 = c.get(f"/api/evaluation/{pid}", headers=TH)
# 4) reflection（内部员工 → 应成功）
tk_staff = c.post("/api/login", json={"username": "admin", "password": "admin123"}).json()["data"]["token"]
rf = c.post("/api/evaluation/reflection", headers=H, json={"projectId": pid, "reflection": "QA 内部反思"})

result = {
    "case_id": "TC-CRUD-009",
    "status": "passed" if (sub.json().get("code") == 200 and sub2.json().get("code") == 400 and g1.json().get("code") == 200 and g2.json().get("code") == 200 and rf.json().get("code") == 200) else "failed",
    "actual": f"submit={sub.json().get('code')} dup={sub2.json().get('code')} get_admin={g1.json().get('code')} get_client={g2.json().get('code')} reflection={rf.json().get('code')}",
}
print(json.dumps(result, ensure_ascii=False))

# 清理
c.post("/api/project/unArchive", headers=H, json={"projectId": pid})
c.post("/api/project/delete", headers=H, json={"projectId": pid})
c.post("/api/sysUser/delete", headers=H, json={"userId": su["data"]["userId"]})
c.post("/api/customer/delete", headers=H, json={"id": cu})
c.post("/api/customerCategory/delete", headers=H, json={"id": u})
print("cleaned")
