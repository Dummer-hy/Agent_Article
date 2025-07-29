import os
from dataclasses import dataclass
from typing import List, Dict, Optional


@dataclass
class Config:
    # API配置
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "XXXXXXXXXXXXXXXXXXXXXXX")
    KIMI_API_KEY: str = os.getenv("KIMI_API_KEY", "")

    # 模型选择
    SEARCH_MODEL: str = "deepseek-chat"
    TEXT_MODEL: str = "deepseek-reasoner"
    IMAGE_MODEL: str = "deepseek-chat"

    # 文献存储路径配置
    DATA_DIR: str = "data"

    # conda环境配置，必备的环境名
    ARXIV_CONDA_ENV: str = "mcp"
    MINERU_CONDA_ENV: str = "Agent"

    # 检索配置,最多返回20条文献搜索结果
    MAX_RESULTS: int = 200
    MAX_SELECTED: int = 20

    # 问题文件
    QUESTION_FILE: str = "data/question.txt"

    # 排除文件
    EXCLUDE_CSV: str = "data/exclude2025-7-1.csv"
    EXCLUDE_COLUMN: str = "文献标题"


AVAILABLE_MODELS = {
    "deepseek-chat": {
        "api_key": "DEEPSEEK_API_KEY",
        "endpoint": "https://api.deepseek.com/v1/chat/completions",
        "supports_vision": True
    },
    "deepseek-reasoner": {
        "api_key": "DEEPSEEK_API_KEY",
        "endpoint": "https://api.deepseek.com/v1/chat/completions",
        "supports_vision": False
    },
    "kimi": {
        "api_key": "KIMI_API_KEY",
        "endpoint": "https://api.moonshot.cn/v1/chat/completions",
        "supports_vision": False
    }
}

config = Config()
