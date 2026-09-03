"""第6步路由层检查点脚本（FastAPI TestClient + SQLite 内存库，HTTP 级端到端）

运行：cd backend && python tests/check_step6_api.py
覆盖：鉴权 401/403、登录、全模块接口连通、消息未读数、归档拦截、报表导出
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.dependencies import get_db
from app.main import app
from app.models import SysUser

engine = create_engine(
    "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
)
Session = sessionmaker(bind=engine)

# SQLite 索引名需全库唯一，加表名前缀
for _t in Base.metadata.tables.values():
    for _i in _t.indexes:
        _i.name = f"{_t.name}_{_i.name}"
Base.metadata.create_all(engine)

db = Session()
db.add(SysUser(username="admin", password="admin123", real_name="管理员", role="管理员", is_enable=1))
db.commit()
db.close()


def override_get_db():
    session = Session()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

PASSED = 0


def check(name, cond):
    global PASSED
    assert cond, f"FAILED: {name}"
    PASSED += 1
    print(f"  PASS {name}")


def body(resp):
    assert resp.status_code == 200, f"HTTP {resp.status_code}: {resp.text[:300]}"
    return resp.json()


print("== 1. 鉴权 ==")
r = body(client.get("/api/project/list"))
check("无 token 返回 401", r["code"] == 401 and r["data"] is None)

r = body(client.post("/api/login", json={"username": "admin", "password": "wrong"}))
check("密码错误返回 400", r["code"] == 400 and r["msg"] == "账号或密码错误")

r = body(client.post("/api/login", json={"username": "admin", "password": "admin123"}))
check("登录成功返回 token + userInfo(camelCase)",
      r["code"] == 200 and r["data"]["token"] and r["data"]["userInfo"]["realName"] == "管理员")
AH = {"Authorization": f"Bearer {r['data']['token']}"}

print("== 2. 用户管理 ==")
r = body(client.post("/api/sysUser/create", json={
    "username": "zhangsan", "password": "123456", "realName": "张三", "role": "设计师"}, headers=AH))
check("管理员创建设计师", r["code"] == 200 and r["data"]["userId"] == 2)
r = body(client.post("/api/login", json={"username": "zhangsan", "password": "123456"}))
DH = {"Authorization": f"Bearer {r['data']['token']}"}
r = body(client.get("/api/sysUser/list", headers=DH))
check("设计师访问用户管理 403", r["code"] == 403)
r = body(client.get("/api/sysUser/list", headers=AH))
check("管理员查看用户列表含明文密码", r["code"] == 200 and r["data"][0]["password"] == "admin123")

print("== 3. 客户分类 + 客户 ==")
r = body(client.post("/api/customerCategory/add", json={"categoryName": "政府客户"}, headers=AH))
cat_id = r["data"]["id"]
r = body(client.post("/api/customer/add", json={
    "categoryId": cat_id, "customerName": "青岛博物馆", "remark": "李主任"}, headers=AH))
cus_id = r["data"]["id"]
r = body(client.post("/api/customerCategory/delete", json={"id": cat_id}, headers=AH))
check("分类下有客户删除 400", r["code"] == 400 and "该分类下存在客户" in r["msg"])
r = body(client.get("/api/customer/list?pageNum=1&pageSize=10&customerName=博物馆", headers=AH))
check("客户分页+模糊搜索", r["data"]["total"] == 1 and r["data"]["items"][0]["categoryName"] == "政府客户")

print("== 4. 节点模板 + 流程模板 ==")
r = body(client.post("/api/nodeTemplate/add", json={
    "nodeTitle": "需求对齐", "nodeRemark": "确认需求", "sort": 1,
    "formFields": [{"fieldLabel": "需求描述", "fieldType": "text_multi", "sort": 1}]}, headers=AH))
nt_req_id = r["data"]["id"]
r = body(client.post("/api/nodeTemplate/add", json={
    "nodeTitle": "IP设计输出", "nodeRemark": "输出设计稿", "sort": 2, "formFields": []}, headers=AH))
nt_design_id = r["data"]["id"]
check("管理员创建 2 个节点模板", r["code"] == 200)

r = body(client.post("/api/flowTemplate/add", json={
    "templateName": "标准IP设计流程",
    "nodes": [
        {"nodeTemplateId": nt_req_id, "nodeTitle": "需求对齐", "sort": 1, "posX": 100, "posY": 200},
        {"nodeTemplateId": nt_design_id, "nodeTitle": "IP设计输出", "sort": 2, "posX": 400, "posY": 200},
    ],
    "edges": [{"sourceNodeId": 1, "targetNodeId": 2, "label": ""}]}, headers=AH))
tpl_id = r["data"]["id"]
check("整图提交创建模板", r["code"] == 200 and tpl_id == 1)
r = body(client.get(f"/api/flowTemplate/detail/{tpl_id}", headers=DH))
check("设计师可查模板详情", len(r["data"]["nodes"]) == 2 and len(r["data"]["edges"]) == 1)
r = body(client.post("/api/flowTemplate/delete", json={"id": tpl_id}, headers=DH))
check("设计师删除模板 403", r["code"] == 403)

print("== 5. 项目 ==")
r = body(client.post("/api/project/create", json={
    "projectName": "熊猫IP设计项目", "customerId": cus_id,
    "designerRelUserIdList": [2], "templateId": tpl_id}, headers=DH))
check("设计师新建项目 403", r["code"] == 403)
r = body(client.post("/api/project/create", json={
    "projectName": "熊猫IP设计项目", "customerId": cus_id,
    "designerRelUserIdList": [2], "templateId": tpl_id}, headers=AH))
pid = r["data"]["projectId"]
check("管理员用模板创建项目", r["code"] == 200 and pid == 1)
r = body(client.get(f"/api/project/detail/{pid}", headers=DH))
d = r["data"]
check("项目详情：节点2+连线1+设计师1+状态进行中",
      len(d["nodes"]) == 2 and len(d["edges"]) == 1 and len(d["designerList"]) == 1 and d["projectStatus"] == "进行中")
check("模板实例化节点 hasForm=true", d["nodes"][0]["hasForm"] is True and d["nodes"][1]["hasForm"] is False)
node1, node2 = d["nodes"][0]["id"], d["nodes"][1]["id"]

print("== 6. 节点 + 表单 + 消息 ==")
r = body(client.post("/api/nodeTemplate/add", json={
    "nodeTitle": "打样制作", "nodeRemark": "制作实物样品", "sort": 1, "formFields": []}, headers=AH))
check("管理员新增节点模板", r["code"] == 200)
node_tpl_id = r["data"]["id"]
r = body(client.post("/api/projectNode/add", json={
    "projectId": pid, "nodeTemplateId": node_tpl_id, "posX": 300, "posY": 300}, headers=DH))
check("设计师从节点库新增节点", r["code"] == 200)
node3 = r["data"]["id"]
r = body(client.get("/api/message/unreadCount", headers=AH))
check("admin 未读数=1（排除操作人张三）", r["data"]["count"] == 1)
r = body(client.get("/api/message/myList?pageNum=1&pageSize=10", headers=AH))
msg_id = r["data"]["items"][0]["id"]
check("消息文案+类型正确", r["data"]["items"][0]["msgType"] == "node_create"
      and "新增了节点：打样制作" in r["data"]["items"][0]["msgContent"])
r = body(client.post("/api/message/read", json={"messageId": msg_id}, headers=AH))
r = body(client.get("/api/message/unreadCount", headers=AH))
check("标记已读后未读数=0", r["data"]["count"] == 0)

r = body(client.get(f"/api/projectNode/getForm/{node1}", headers=DH))
check("getForm 返回表单定义", len(r["data"]["fields"]) == 1 and r["data"]["fields"][0]["fieldLabel"] == "需求描述")
fid = r["data"]["fields"][0]["id"]
r = body(client.post("/api/projectNode/saveFormValue", json={
    "projectNodeId": node1, "formValueList": [{"id": fid, "fieldValue": "要一只抱竹子的熊猫"}]}, headers=DH))
check("保存表单值", r["code"] == 200)
r = body(client.get(f"/api/projectNode/getForm/{node1}", headers=DH))
check("表单值已保存", r["data"]["fields"][0]["fieldValue"] == "要一只抱竹子的熊猫")
r = body(client.get(f"/api/projectNode/getForm/{node3}", headers=DH))
check("临时新增节点无表单返回空数组", r["data"]["fields"] == [])

r = body(client.post("/api/projectNode/batchUpdatePositions", json={
    "projectId": pid, "positions": [{"id": node1, "posX": 150.5, "posY": 220}]}, headers=DH))
check("批量更新坐标", r["code"] == 200)
r = body(client.post("/api/projectNodeEdge/add", json={
    "projectId": pid, "sourceNodeId": node2, "targetNodeId": node3, "label": ""}, headers=DH))
edge_id = r["data"]["id"]
r = body(client.post("/api/projectNode/delete", json={"nodeId": node3}, headers=DH))
r = body(client.get(f"/api/project/detail/{pid}", headers=DH))
check("删除节点后连线级联删除", all(e["id"] != edge_id for e in r["data"]["edges"]))

print("== 7. 评论 ==")
r = body(client.post("/api/comment/add", json={"projectId": pid, "content": "这个方案不错"}, headers=DH))
cid = r["data"]["id"]
r = body(client.post("/api/comment/delete", json={"commentId": cid}, headers=AH))
check("非本人删除评论 403", r["code"] == 403 and "无权删除他人评论" in r["msg"])
r = body(client.post("/api/comment/delete", json={"commentId": cid}, headers=DH))
check("本人删除评论", r["code"] == 200)

print("== 8. 归档拦截（API 级） ==")
body(client.post("/api/project/archive", json={"projectId": pid}, headers=AH))
r = body(client.post("/api/projectNode/add", json={"projectId": pid, "nodeTemplateId": node_tpl_id}, headers=DH))
check("归档后新增节点 400", r["code"] == 400 and "项目已归档" in r["msg"])
r = body(client.post("/api/project/delete", json={"projectId": pid}, headers=AH))
check("归档项目删除 400", r["code"] == 400 and "已归档项目请先取消归档" in r["msg"])
body(client.post("/api/project/unArchive", json={"projectId": pid}, headers=AH))

print("== 9. 日志 + 报表 ==")
r = body(client.get("/api/sysOperationLog/globalList?pageNum=1&pageSize=50", headers=AH))
check("全局日志有记录且含操作人姓名", r["data"]["total"] > 0 and r["data"]["items"][0]["operUserName"])
r = body(client.get("/api/sysOperationLog/globalList", headers=DH))
check("设计师查全局日志 403", r["code"] == 403)
r = body(client.get(f"/api/sysOperationLog/projectLog?projectId={pid}", headers=DH))
check("设计师可查项目内日志", r["code"] == 200 and len(r["data"]) > 0)
r = body(client.get("/api/report/exportProject", headers=DH))
check("设计师导出报表 403", r["code"] == 403)
resp = client.get("/api/report/exportProject", headers=AH)
check("导出 Excel 200 + xlsx 类型 + 中文文件名",
      resp.status_code == 200
      and resp.headers["content-type"].startswith("application/vnd.openxmlformats")
      and "%E9%A1%B9%E7%9B%AE%E5%88%97%E8%A1%A8" in resp.headers["content-disposition"]
      and len(resp.content) > 1000)

print(f"\n全部 API 检查点通过：{PASSED} 项")
