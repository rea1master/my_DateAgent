"""程序入口:python main.py "你的问题" """
import sys
from agent import run_agent,ChatSession

# Windows 控制台默认 GBK,强制 UTF-8 输出,避免中文乱码
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def main():
    session = ChatSession()
    turn=1
    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:]).strip()
        print(f"\n问题:{question}")
        print(f"\n【最终回答】 {session.ask(question)}")
        return
    while True:
        print(f"shish\n========== 第 {turn} 次提问 ==========\n")
        question=input("请输入本轮问题\n")
        if(question=="exit"):
            break
        print(f"\n问题:{question}")
        print(f"\n【最终回答】 {session.ask(question)}")
        turn+=1

if __name__ == "__main__":
    main()