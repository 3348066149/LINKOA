"""数据库切换脚本：在 SQLite 和 MySQL 之间一键切换（V1.4 双数据库支持）

用法：
  python switch_db.py sqlite   # 切到 SQLite（便携/单机）
  python switch_db.py mysql    # 切到 MySQL（多用户并发协作）

会修改 backend/.env 的 DB_URL，切换后需重启后端。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")

# MySQL 连接串：可用环境变量 LINKOA_MYSQL_URL 覆盖（换机器后无需改代码）
# 默认值仅适合本机开发（root/123456），生产/协作部署请通过环境变量传入实际账号密码。
MYSQL_URL = os.environ.get(
    "LINKOA_MYSQL_URL",
    "mysql+pymysql://root:123456@localhost:3306/linkoa?charset=utf8mb4",
)
DB_URLS = {
    # V1.4.4：SQLite 用相对路径，config.py 会自动规范化到 backend/ 目录下，随项目文件夹走
    "sqlite": "sqlite:///./linkoa.db",
    "mysql": MYSQL_URL,
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in DB_URLS:
        print("用法: python switch_db.py sqlite|mysql")
        sys.exit(1)
    target = sys.argv[1]
    url = DB_URLS[target]

    with open(ENV_PATH, "r", encoding="utf-8") as f:
        lines = f.readlines()

    found = False
    for i, line in enumerate(lines):
        if line.strip().startswith("DB_URL="):
            lines[i] = f"DB_URL={url}\n"
            found = True
            break
    if not found:
        lines.insert(0, f"DB_URL={url}\n")

    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print(f"已切换到 {target.upper()}：{url}")
    print("提示：切换后需重启后端；如需同步数据，先跑对应迁移脚本：")
    print("  - MySQL→SQLite : python migrate_mysql_to_sqlite.py")
    print("  - SQLite→MySQL : python migrate_sqlite_to_mysql.py")


if __name__ == "__main__":
    main()
