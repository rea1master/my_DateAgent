import os
from openai import OpenAI
from dotenv import load_dotenv
from dataclasses import dataclass

load_dotenv()

@dataclass
class LLMConfig:
    model: str = os.getenv("model_name")
    temperature:float=0.0
    max_tokens: int = 1000
    timeout: int = 20
    max_retries: int = 3

class llm:
    def __init__(self, config: LLMConfig):
        self.config = config
        self.client = OpenAI(
            api_key=os.getenv("ds_api"),
            base_url=os.getenv("ds_url"),
            timeout=config.timeout,
            max_retries=config.max_retries,
        )

    def chat(self, messages) -> str:
        """普通对话:发消息列表,拿纯文本回复"""
        resp = self.client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )
        return resp.choices[0].message.content

    def chat_with_tools(self, messages, tools):
        """Agent 模式:让模型决定要不要调工具。

        成功返回 message;失败直接抛异常,由 run_agent 最外层兜底。
        (模型 API 出错,模型自己修不了,不该回传给它。)
        """
        resp = self.client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            tools=tools,
            tool_choice="auto",
        )
        return resp.choices[0].message