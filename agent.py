"""Agent 主循环:think(模型决定) → act(代码执行工具) → observe(结果回填),如此往复"""
from datetime import datetime
from pathlib import Path

from llm import llm, LLMConfig
from agent_tools import TOOL_SCHEMAS, execute_tool
from db import get_schema_text

MAX_STEPS = 10        # 最大循环轮数,防止死循环
MAX_TOOL_FAILS = 3    # 连续工具失败多少次就熔断
MAX_HISTORY = 30          # 最多保留的消息条数(不含 system)
MAX_CONTEXT_CHARS = 8000  # 上下文字符数预算

LOG_FILE = Path(__file__).parent / "logs" / "agent.log"

SYSTEM_PROMPT = f"""你是"DataAgent",一个电商数据分析助手。
你可以调用 run_sql 工具,在 SQLite 数据库上执行只读 SQL 查询。

数据库表结构:
{get_schema_text()}

工作方式:
- 先理解用户问题,判断需要查哪些表;
- 需要数据时,调用 run_sql 写 SQL;
- 需要展示趋势 / 对比 / 占比时,调用 plot_chart 画图(SQL 返回 x、y 两列);
- 拿到结果后,判断是否还需要继续查询;
- 信息足够时,直接用中文给出结论,不要再调用工具。

注意:
- 只写 SELECT 查询;
- 时间列是 TEXT,格式 'YYYY-MM-DD HH:MM:SS';取年份用 strftime('%Y', created_at),按月用 strftime('%Y-%m', created_at);
- 金额是 DECIMAL,聚合后注意单位。"""


class ChatSession:
    
    def __init__(self):
        self.messages=[{"role":"system","content":SYSTEM_PROMPT}]

    def _to_dict(self,msg):
        d={"role":"assistant","content":msg.content}
        if msg.tool_calls:
            d["tool_calls"]=[
                {"id":tc.id,
                 "type":"function",
                 "function":{"name":tc.function.name,"arguments":tc.function.arguments}} 
                for tc in msg.tool_calls]
        return d

    def _trim(self):
        total=0
        for m in self.messages:
            total+=len(str(m.get("content") or ""))
            for tc in m.get("tool_calls") or []:
                total+=len(str(tc["function"]["arguments"]) or "")
            
        if len(self.messages)<=MAX_HISTORY+1 and total<=MAX_CONTEXT_CHARS:
            return 
        start=max(1,len(self.messages)-MAX_HISTORY)
        while start<len(self.messages) and self.messages[start].get("role")=="tool":
            start+=1
        self.messages=[self.messages[0]]+self.messages[start:]
            
    
    def ask(self,question:str)->str:
        client = llm(LLMConfig())
        self._trim()
        self.messages.append({"role":"user","content":question})
        fail_streak = 0  # 连续工具失败计数
        
        
        for step in range(MAX_STEPS):
                print(f"\n========== 第 {step + 1} 轮 ==========")
                log(f"第 {step + 1} 轮开始")
        
                # 1) 问模型:下一步做什么? (模型层错误交给最外层兜底)
                try:
                    msg = client.chat_with_tools(self.messages, TOOL_SCHEMAS)
                except Exception as e:
                    log(f"模型调用失败:{type(e).__name__}: {e}")
                    return f"[第 {step + 1} 轮] 模型调用失败:{type(e).__name__}: {e}"
                self.messages.append(self._to_dict(msg))  # 模型的决定(含 tool_calls)必须进历史
        
                # 2) 没有工具调用 = 模型给出最终答案,结束
                if not msg.tool_calls:
                    log(f"最终答案:{msg.content}")
                    return msg.content
        
                # 3) 有工具调用:执行,把结果回填给模型
                for tc in msg.tool_calls:
                    ok, result = execute_tool(tc.function.name, tc.function.arguments)
                    fail_streak = 0 if ok else fail_streak + 1
                    print(f"  → {tc.function.name}({tc.function.arguments})")
                    print(f"  ← {'成功' if ok else '失败'}: {result}")
                    log(f"工具 {tc.function.name} {'成功' if ok else '失败'}: {result[:200]}")
                    self.messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
        
                    # 连续失败达到阈值 → 熔断,不再白跑
                    if fail_streak >= MAX_TOOL_FAILS:
                        log(f"连续 {MAX_TOOL_FAILS} 次失败,熔断")
                        return f"连续 {MAX_TOOL_FAILS} 次工具调用失败,已熔断。最后错误:{result}"
        
        return f"[已达最大步数 {MAX_STEPS},任务未完成]"
        


def log(text: str) -> None:
    """把运行过程追加写入 logs/agent.log,便于复盘"""
    LOG_FILE.parent.mkdir(exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {text}\n")

# 兼容包装
def run_agent(user_question: str) -> str:
    return ChatSession().ask(user_question)