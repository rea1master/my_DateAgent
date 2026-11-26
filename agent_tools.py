"""工具层:定义工具、实现工具、按名字分发。"""
import json
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # 无界面后端:只存图,不开窗口
import matplotlib.pyplot as plt

from db import query

# 只允许这些开头的语句(读操作)
_ALLOWED_PREFIXES = ("select", "with", "explain")

# 图表输出目录
CHART_DIR = Path(__file__).parent / "charts"

# 中文字体:matplotlib 默认不支持中文,不设标题会变方块
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False


# ---------- 工具实现 ----------
def run_sql(sql: str) -> str:
    """执行一条只读 SQL,返回表格化文本。
    出错直接抛异常,统一由 execute_tool 兜住 —— 不在这一层自己吞。
    """
    s = sql.strip().lower()
    if not s.startswith(_ALLOWED_PREFIXES):
        raise ValueError("只允许只读查询(SELECT/WITH/EXPLAIN)")
    cols, rows = query(sql)  # 出错自然往上抛
    return _format_table(cols, rows)

def plot_chart(sql: str, x_col: str, y_col: str, title: str,
               chart_type: str = "bar") -> str:
    """执行一条 SELECT,把结果画成图并保存为 PNG,返回文件路径。

    出错直接抛异常,统一由 execute_tool 兜住(和 run_sql 一致)。
    """
    cols, rows = query(sql)  # 复用只读查询,自动享受只读保护
    if not rows:
        raise ValueError("查询没有返回数据,无法画图")
    if x_col not in cols or y_col not in cols:
        raise ValueError(f"列名不存在。查询返回的列是:{cols}")

    xi, yi = cols.index(x_col), cols.index(y_col)
    xs = [r[xi] for r in rows]
    ys = [r[yi] for r in rows]

    fig, ax = plt.subplots(figsize=(9, 5))
    if chart_type == "line":
        ax.plot(xs, ys, marker="o")
    elif chart_type == "pie":
        ax.pie(ys, labels=xs, autopct="%1.1f%%")
    else:  # bar(默认)
        ax.bar(xs, ys)

    if chart_type != "pie":
        ax.set_title(title)
        ax.set_xlabel(x_col)
        ax.set_ylabel(y_col)
        ax.tick_params(axis="x", rotation=45)
    else:
        ax.set_title(title)

    fig.tight_layout()
    CHART_DIR.mkdir(parents=True, exist_ok=True)
    out = CHART_DIR / f"chart_{datetime.now():%Y%m%d_%H%M%S_%f}.png"
    fig.savefig(out, dpi=130)
    plt.close(fig)
    return f"图表已保存:{out}"

def _format_table(cols, rows) -> str:
    """把查询结果排成对齐的文本表格"""
    if not cols:
        return "(执行成功,无返回列)"
    if not rows:
        return "(查询成功,但没有返回数据行)"

    srows = [[str(v) for v in r] for r in rows]
    widths = [len(c) for c in cols]
    for r in srows:
        for j, v in enumerate(r):
            widths[j] = max(widths[j], len(v))

    header = " | ".join(c.ljust(widths[i]) for i, c in enumerate(cols))
    sep = "-+-".join("-" * w for w in widths)
    body = [" | ".join(v.ljust(widths[i]) for i, v in enumerate(r)) for r in srows]
    return "\n".join([header, sep, *body])


# ---------- 工具说明书(发给模型) ----------
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "run_sql",
            "description": (
                "在电商数据库(SQLite)上执行一条只读 SQL 查询,返回结果表格。"
                "只允许 SELECT / WITH。表结构见系统提示。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": "要执行的 SQL 查询语句,必须是 SELECT",
                    }
                },
                "required": ["sql"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "plot_chart",
            "description": (
                "把一条 SELECT 查询的结果画成图并保存为 PNG。"
                "适合趋势(line)、对比(bar)、占比(pie)。"
                "SQL 需返回 x_col、y_col 两列。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "sql": {"type": "string", "description": "返回绘图数据的 SELECT 查询"},
                    "x_col": {"type": "string", "description": "作为 X 轴的列名"},
                    "y_col": {"type": "string", "description": "作为数值的列名"},
                    "title": {"type": "string", "description": "图表标题"},
                    "chart_type": {
                        "type": "string",
                        "enum": ["bar", "line", "pie"],
                        "description": "图表类型,默认 bar",
                    },
                },
                "required": ["sql", "x_col", "y_col", "title"],
            },
        },
    },
]



# ---------- 工具注册与分发 ----------
_REGISTRY = {
    "run_sql": run_sql,
    "plot_chart":plot_chart
}



def execute_tool(name: str, arguments: str) -> tuple[bool, str]:
    """唯一兜底点。成功 (True, 结果);失败 (False, 错误文本)。

    失败也返回字符串而不是抛异常 —— 因为模型需要看到错误,自己改正。
    """
    try:
        args = json.loads(arguments) if arguments else {}
        fn = _REGISTRY.get(name)
        if fn is None:
            return False, f"不存在名为 {name} 的工具"
        return True, str(fn(**args))
    except Exception as e:
        return False, f"工具 {name} 执行失败:{type(e).__name__}: {e}"

    


