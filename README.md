# DataAgent

用自然语言对电商数据库做数据分析的 Agent(Text-to-SQL)。
模型通过 `run_sql` 工具查询 SQLite,循环推理(think → act → observe)直到给出结论。

## 目录结构

```
DataAgent/
├── main.py               # 程序入口
├── agent.py              # Agent 主循环(think → act → observe)
├── agent_tools.py        # 工具层:工具定义 / 实现 / 分发
├── llm.py                # 模型层:LLM 客户端封装
├── db.py                 # 数据层:只负责连接与查询
├── requirements.txt
└── data/
    ├── schema.sql          # 数据库结构(SQLite,当前使用)
    ├── schema_postgres.sql # 最初的设计稿(PostgreSQL,仅参考)
    ├── init_db.py          # 建库 + 生成样例数据
    └── dataagent.db        # 样例库(可由 init_db.py 重建)
```

## 快速开始

```bash
pip install -r requirements.txt
python data/init_db.py                                  # 首次:建库并灌数据
python main.py "2023年订单实付金额最高的前3个省份是哪些?"
```

## 环境变量(`.env`)

```
ds_api=你的 API Key
ds_url=https://api.deepseek.com
model_name=你的模型名
```

> `.env` 已加入 `.gitignore`,不会被提交到仓库。
