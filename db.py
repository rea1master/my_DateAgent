"""数据层:只负责"怎么连库、怎么查",不掺杂任何工具/ Agent 逻辑。"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "data" / "dataagent.db"


def _read_only_uri() -> str:
    """只读 URI:从 SQLite 引擎层面禁止写操作"""
    return DB_PATH.resolve().as_uri() + "?mode=ro"


def query(sql: str):
    """执行 SQL,返回 (列名列表, 行列表)。出错直接抛异常,由上层处理。"""
    con = sqlite3.connect(_read_only_uri(), uri=True)
    try:
        cur = con.execute(sql)
        cols = [d[0] for d in cur.description] if cur.description else []
        return cols, cur.fetchall()
    finally:
        con.close()


def get_schema_text() -> str:
    """读出所有表/列,拼成给模型看的 schema 描述"""
    con = sqlite3.connect(_read_only_uri(), uri=True)
    try:
        tables = [
            r[0]
            for r in con.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            ).fetchall()
        ]
        lines = []
        for t in tables:
            cols = con.execute(f'PRAGMA table_info("{t}")').fetchall()
            lines.append(f"- {t}: " + ", ".join(f"{c[1]} {c[2]}" for c in cols))
        return "\n".join(lines)
    finally:
        con.close()
