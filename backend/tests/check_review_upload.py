# -*- coding: utf-8 -*-
"""V1.4.21 客户审核反馈图片上传自检（TestClient + 临时库副本，不污染真实数据）

回归点：`POST /api/review/upload` 的 multipart 字段名必须与前端 el-upload 的
`:data="{projectNodeId: currentNode.id}"` 一致（camelCase），也与其它上传接口
（attachment / customer cover / project cover）保持一致。

历史缺陷：V1.4.19/20 首版后端把该字段声明为 `project_node_id`，而前端发的是
`projectNodeId` → FastAPI 422 → 全局处理器包成 **HTTP 200 + body.code=400
「请求参数错误」**；又因为 el-upload 只按 HTTP 状态判定成败（200 即 on-success），
前端读不到 res.data.path 就静默丢弃，客户点「上传图片」后画面毫无反应。

本脚本用真实的客户账号走完整链路：建单位/客户/客户账号/审核节点模板/项目/节点
→ 客户登录 → 按前端报文上传图片 → 提交审核 → 校验图片反馈已落库。
全程只写临时库副本与临时 uploads 目录，结束后整体删除。

运行：.venv/Scripts/python backend/tests/check_review_upload.py
"""
import base64
import io
import os
import shutil
import sys
import tempfile

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # backend/
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
SRC_DB = os.path.join(PROJECT_ROOT, "data", "linkoa.db")

# ---- 先隔离数据环境，再 import app（config 在导入期读环境变量）----
TMP_DIR = tempfile.mkdtemp(prefix="linkoa_review_check_")
TMP_DB = os.path.join(TMP_DIR, "linkoa_check.db")
if os.path.isfile(SRC_DB):
    shutil.copy(SRC_DB, TMP_DB)          # 复制真实库：保留 admin 账号与全部表结构
os.environ["DB_URL"] = "sqlite:///" + TMP_DB.replace("\\", "/")
os.environ["UPLOAD_DIR"] = os.path.join(TMP_DIR, "uploads")
os.environ["JWT_SECRET"] = "linkoa-review-check-secret-0123456789"

sys.path.insert(0, BACKEND_DIR)

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402

PNG_1PX = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)

ok_count = 0
TOTAL = 13
PREFIX = "审核上传自检"


def check(name, cond, extra=""):
    global ok_count
    assert cond, f"FAIL: {name} {extra}"
    ok_count += 1
    print(f"  [{ok_count}/{TOTAL}] OK  {name}")


def api(client, path, body, token=None):
    h = {"Authorization": f"Bearer {token}"} if token else {}
    return client.post(path, json=body, headers=h).json()


def get(client, path, token=None):
    h = {"Authorization": f"Bearer {token}"} if token else {}
    return client.get(path, headers=h).json()


def upload(client, path, token, filename, content, fields=None):
    """multipart 上传：fields 为额外的表单字段（字段名与前端完全一致）"""
    h = {"Authorization": f"Bearer {token}"} if token else {}
    data = {k: str(v) for k, v in (fields or {}).items()}
    return client.post(path, headers=h, data=data,
                       files={"file": (filename, io.BytesIO(content), "image/png")}).json()


def main():
    client = TestClient(app)
    with client:  # 触发 lifespan：建表 + 初始管理员 + 存量迁移（都只作用于临时库）
        # 0. 管理员登录 + 造数
        res = api(client, "/api/login", {"username": "admin", "password": "admin123"})
        assert res["code"] == 200, f"管理员登录失败: {res}"
        at = res["data"]["token"]
        print("0. 管理员登录 OK")

        res = api(client, "/api/customerCategory/add", {"categoryName": PREFIX + "单位"}, at)
        assert res["code"] == 200, f"建客户单位失败: {res}"
        cat_id = res["data"]["id"] if isinstance(res["data"], dict) else res["data"]

        res = api(client, "/api/customer/add", {
            "categoryId": cat_id, "customerName": PREFIX + "对接人", "contact": "000"}, at)
        assert res["code"] == 200, f"建客户失败: {res}"
        cid = res["data"]["id"]

        res = api(client, "/api/sysUser/create", {
            "username": PREFIX + "账号", "password": "check123456",
            "realName": PREFIX + "客户", "categoryId": cat_id}, at)
        assert res["code"] == 200, f"建客户账号失败: {res}"

        res = api(client, "/api/nodeTemplate/add", {
            "nodeTitle": PREFIX + "节点", "sort": 99, "isReview": True,
            "reviewOptions": ["通过", "不通过"],
            "formFields": [{"fieldLabel": "设计稿", "fieldType": "image", "sort": 1}],
            "clientReviewFields": [
                {"fieldLabel": "反馈图", "fieldType": "image", "sort": 1},
                {"fieldLabel": "备注", "fieldType": "text_multi", "sort": 2},
            ]}, at)
        assert res["code"] == 200, f"建审核节点模板失败: {res}"
        tpl_id = res["data"]["id"]

        res = api(client, "/api/project/create", {
            "projectName": PREFIX + "项目", "categoryId": cat_id,
            "contactCustomerIds": [cid]}, at)
        assert res["code"] == 200, f"建项目失败: {res}"
        pid = res["data"]["projectId"]

        res = api(client, "/api/projectNode/add", {"projectId": pid, "nodeTemplateId": tpl_id}, at)
        assert res["code"] == 200, f"加审核节点失败: {res}"
        nid = res["data"]["id"]
        check("造数完成：审核节点 isReview=true", True)

        # 1. 客户登录
        res = api(client, "/api/login", {"username": PREFIX + "账号", "password": "check123456"})
        assert res["code"] == 200, f"客户登录失败: {res}"
        ct = res["data"]["token"]
        check("客户账号登录成功且 role=客户", res["data"]["userInfo"]["role"] == "客户", res)

        # 2. 待审列表能看到该节点
        pending = get(client, "/api/review/pending", ct)
        node = next((x for x in pending["data"] if x["nodeId"] == nid), None)
        check("客户待审列表含该审核节点", node is not None, pending["data"])
        check("待审节点回传客户反馈字段（含 image）",
              any(f["fieldType"] == "image" for f in (node or {}).get("clientReviewFields", [])), node)

        # 3. 前端报文上传（关键回归点：字段名 projectNodeId）
        res = upload(client, "/api/review/upload", ct, "反馈图.png", PNG_1PX,
                     {"projectNodeId": nid})
        check("上传图片返回 code=200（前端报文 projectNodeId）", res["code"] == 200, res)
        path = (res.get("data") or {}).get("path")
        check("返回 uploads 相对路径", bool(path) and "/" in path, res)

        # 4. 图片可直接访问
        raw = client.get("/uploads/" + (path or "none"))
        check("图片可通过 /uploads 静态访问", raw.status_code == 200 and len(raw.content) > 0,
              raw.status_code)

        # 5. 字段名契约：漏传/传错字段名必须被入参校验拦下（历史缺陷就是这个 400）
        bad = upload(client, "/api/review/upload", ct, "x.png", PNG_1PX, {})
        check("不传 projectNodeId 时返回 400（不会被静默忽略）", bad["code"] == 400, bad)

        # 6. 提交审核（图片反馈按前端 feedbackFields 报文）
        res = api(client, "/api/review/submit", {
            "projectNodeId": nid, "option": "通过", "comment": "自检批注",
            "feedbackFields": [
                {"fieldLabel": "备注", "fieldType": "text_multi", "fieldValue": "自检备注"},
                {"fieldLabel": "反馈图", "fieldType": "image", "fieldValue": path},
            ]}, ct)
        check("客户提交审核成功", res["code"] == 200, res)

        # 7. 落库校验：客户侧图标字段值 = 刚上传的路径
        form = get(client, f"/api/projectNode/getForm/{nid}", ct)
        client_img = next((f for f in form["data"]["fields"]
                           if f["side"] == "client" and f["fieldType"] == "image"), None)
        check("客户图片反馈已落库且路径一致",
              client_img is not None and client_img["fieldValue"] == path, form["data"]["fields"])

        # 8. 待审列表已移除该节点（提交后锁定）
        pending = get(client, "/api/review/pending", ct)
        check("提交后该节点从待审列表移除",
              all(x["nodeId"] != nid for x in pending["data"]), pending["data"])

        # 9. 权限边界：非客户角色仍禁止走该上传接口
        forbidden = upload(client, "/api/review/upload", at, "x.png", PNG_1PX, {"projectNodeId": nid})
        check("管理员调用该接口返回 403（仅客户可上传）", forbidden["code"] == 403, forbidden)

        # 10. 已审节点重复上传被业务拦截
        reupload = upload(client, "/api/review/upload", ct, "x.png", PNG_1PX, {"projectNodeId": nid})
        check("已审节点再次上传被拦截（已完成审核）", reupload["code"] == 400, reupload)

    print(f"\n=== 通过 {ok_count}/{TOTAL} ===")
    return 0 if ok_count == TOTAL else 1


if __name__ == "__main__":
    try:
        code = main()
    finally:
        shutil.rmtree(TMP_DIR, ignore_errors=True)
        print(f"临时数据已清理：{TMP_DIR}")
    sys.exit(code)
