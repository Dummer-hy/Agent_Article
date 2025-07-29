import os
import json
import csv
import logging
import requests
from typing import List, Dict, Optional, Any
from pathlib import Path
import pandas as pd

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def setup_directories(config):
    """创建必要的目录"""
    directories = [
        config.DATA_DIR,

    ]

    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)

    logger.info(f"目录结构创建完成")


def load_excluded_papers(csv_path: str, column_name: str) -> List[str]:
    """从CSV文件加载已处理的论文标题"""
    if not os.path.exists(csv_path):
        logger.info(f"排除文件 {csv_path} 不存在，将处理所有论文")
        return []

    try:
        df = pd.read_csv(csv_path)
        if column_name not in df.columns:
            logger.warning(f"列 {column_name} 不存在于CSV文件中")
            return []

        excluded = df[column_name].dropna().astype(str).tolist()
        logger.info(f"从 {csv_path} 加载了 {len(excluded)} 个已处理论文")
        return excluded
    except Exception as e:
        logger.error(f"加载排除文件时出错: {e}")
        return []


def save_excluded_papers(csv_path: str, column_name: str, papers: List[str]):
    """保存已处理的论文标题到CSV文件"""
    try:
        df = pd.DataFrame({column_name: papers})
        df.to_csv(csv_path, index=False)
        logger.info(f"保存了 {len(papers)} 个论文标题到 {csv_path}")
    except Exception as e:
        logger.error(f"保存排除文件时出错: {e}")


def call_api(model_name: str, messages: List[Dict], config, **kwargs) -> Optional[str]:
    """调用指定模型的API"""
    from config import AVAILABLE_MODELS

    if model_name not in AVAILABLE_MODELS:
        logger.error(f"不支持的模型: {model_name}")
        return None

    model_config = AVAILABLE_MODELS[model_name]
    api_key = getattr(config, model_config["api_key"])

    if not api_key:
        logger.error(f"API密钥未配置: {model_config['api_key']}")
        return None

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    data = {
        "model": model_name,
        "messages": messages,
        "temperature": kwargs.get("temperature", 0.7),
        "max_tokens": kwargs.get("max_tokens", 4000),
        "stream": False  # 添加stream参数
    }

    try:
        logger.info(f"调用API: {model_name} - {model_config['endpoint']}")
        response = requests.post(
            model_config["endpoint"],
            headers=headers,
            json=data,
            timeout=60
        )

        logger.info(f"API响应状态: {response.status_code}")
        if response.status_code != 200:
            logger.error(f"API调用失败: {response.status_code} - {response.text}")
            return None

        response.raise_for_status()

        result = response.json()
        return result["choices"][0]["message"]["content"]

    except Exception as e:
        logger.error(f"API调用失败 ({model_name}): {e}")
        return None


def read_question_file(file_path: str) -> List[Dict[str, str]]:
    """读取问题文件，解析为问题列表"""
    if not os.path.exists(file_path):
        logger.error(f"问题文件 {file_path} 不存在")
        return []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 按===分割问题
        questions = content.split('===')
        parsed_questions = []

        for question in questions:
            question = question.strip()
            if not question:
                continue

            # 提取问题标题（第一行）
            lines = question.split('\n')
            title = lines[0].strip().rstrip('：:')
            content = '\n'.join(lines[1:]).strip()

            parsed_questions.append({
                "title": title,
                "content": content
            })

        logger.info(f"解析了 {len(parsed_questions)} 个问题")
        return parsed_questions

    except Exception as e:
        logger.error(f"读取问题文件时出错: {e}")
        return []


def save_analysis_result(paper_id: str, results: Dict[str, Any], config):
    """保存分析结果到文件"""
    output_file = os.path.join(config.REPORTS_DIR, f"{paper_id}_analysis.txt")

    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"论文分析报告: {paper_id}\n")
            f.write("=" * 50 + "\n\n")

            # 基本信息
            if 'basic_info' in results:
                f.write("基本信息:\n")
                f.write(f"标题: {results['basic_info'].get('title', 'N/A')}\n")
                f.write(f"作者: {results['basic_info'].get('authors', 'N/A')}\n")
                f.write(f"时间: {results['basic_info'].get('published', 'N/A')}\n\n")

            # 问题解答
            if 'qa_results' in results:
                for qa in results['qa_results']:
                    f.write(f"{qa['question']}:\n")
                    f.write(f"{qa['answer']}\n\n")

            # 数据集信息
            if 'datasets' in results:
                f.write("数据集信息:\n")
                for dataset in results['datasets']:
                    f.write(f"- {dataset}\n")
                f.write("\n")

        logger.info(f"分析结果已保存到: {output_file}")

    except Exception as e:
        logger.error(f"保存分析结果时出错: {e}")


def clean_filename(filename: str) -> str:
    """清理文件名，移除非法字符"""
    import re
    # 移除或替换非法字符
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # 限制长度
    if len(filename) > 100:
        filename = filename[:100]
    return filename
