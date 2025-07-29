import os
import json
import base64
import requests
import mimetypes
from PIL import Image
from io import BytesIO
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

# 假设utils.py中包含logger和其他辅助函数
from utils import logger
from config import AVAILABLE_MODELS,Config

class PaperAnalyzer:
    def __init__(self, config):
        """
        初始化论文分析器

        Args:
            config: 配置对象，包含API密钥和模型设置
        """
        self.config = Config
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {Config.DEEPSEEK_API_KEY}"
        }

        # 将AVAILABLE_MODELS引入类中
        self.available_models = AVAILABLE_MODELS

        # 支持的图片格式
        self.supported_image_formats = ['.jpg', '.jpeg', '.png', '.webp']
        # 最大图片大小 (MB)
        self.max_image_size_mb = 20

    def _get_api_endpoint(self, model_name: str) -> str:
        """
        根据模型名称获取API端点

        Args:
            model_name: 模型名称

        Returns:
            str: API端点URL
        """
        # 从available_models获取端点
        if model_name in self.available_models and "endpoint" in self.available_models[model_name]:
            return self.available_models[model_name]["endpoint"]

        # 默认使用DeepSeek的端点
        return "https://api.deepseek.com/v1/chat/completions"

    def _make_api_call(self, model_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        集中的API调用逻辑

        Args:
            model_name: 模型名称
            data: 请求数据

        Returns:
            Dict: API响应的JSON数据

        Raises:
            Exception: 当API调用失败时
        """
        try:
            endpoint = self._get_api_endpoint(model_name)

            # 检查API密钥是否存在于配置中
            if not hasattr(self.config, 'DEEPSEEK_API_KEY') or not self.config.DEEPSEEK_API_KEY:
                raise Exception("DeepSeek API密钥未配置")

            # 尝试发起请求
            response = requests.post(
                endpoint,
                headers=self.headers,
                json=data,
                timeout=60
            )

            if response.status_code == 200:
                return response.json()
            else:
                error_text = response.text if response.text else f"状态码: {response.status_code}"
                logger.error(f"API调用失败 ({model_name}): {error_text}")
                raise Exception(f"API调用失败: {response.status_code} - {error_text}")
        except requests.exceptions.RequestException as e:
            logger.error(f"API请求异常 ({model_name}): {e}")
            raise Exception(f"API请求异常: {str(e)}")
        except Exception as e:
            logger.error(f"API调用出错 ({model_name}): {e}")
            raise Exception(f"API调用出错: {str(e)}")

    def read_question_file(self, file_path: str) -> List[Dict[str, str]]:
        """
        读取问题文件，解析为问题列表

        问题文件格式：问题之间使用===分隔
        每个问题的第一行作为问题标题，其余内容作为问题详情

        Args:
            file_path: 问题文件路径

        Returns:
            List[Dict]: 解析后的问题列表
        """
        if not os.path.exists(file_path):
            logger.error(f"问题文件 {file_path} 不存在")
            return []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 按===分割问题
            question_blocks = content.split('===')
            parsed_questions = []

            for block in question_blocks:
                block = block.strip()
                if not block:
                    continue

                # 提取问题标题（第一行）和内容（剩余行）
                lines = block.split('\n')
                title = lines[0].strip().rstrip('：:')

                # 剩余行作为问题内容
                content = '\n'.join(lines[1:]).strip() if len(lines) > 1 else ""

                parsed_questions.append({
                    "title": title,
                    "content": content
                })

            logger.info(f"解析了 {len(parsed_questions)} 个问题")
            return parsed_questions

        except Exception as e:
            logger.error(f"读取问题文件时出错: {e}")
            return []

    def read_markdown_content(self, md_file_path: str) -> str:
        """
        读取markdown文件内容

        Args:
            md_file_path: Markdown文件路径

        Returns:
            str: 文件内容
        """
        try:
            with open(md_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            logger.info(f"成功读取markdown文件: {os.path.basename(md_file_path)}")
            return content
        except Exception as e:
            logger.error(f"读取markdown文件失败 {md_file_path}: {e}")
            return ""

    def get_image_files(self, paper_dir: str) -> List[str]:
        """
        获取论文目录下的所有图片文件

        Args:
            paper_dir: 论文目录

        Returns:
            List[str]: 图片文件路径列表
        """
        image_extensions = self.supported_image_formats
        image_files = []

        # 搜索整个论文目录下的图片
        for root, dirs, files in os.walk(paper_dir):
            for file in files:
                if any(file.lower().endswith(ext) for ext in image_extensions):
                    image_files.append(os.path.join(root, file))

        logger.info(f"在 {paper_dir} 中找到 {len(image_files)} 个图片文件")
        return image_files

    def is_compatible_image(self, image_path: str) -> Tuple[bool, str]:
        """
        检查图片是否兼容DeepSeek API

        Args:
            image_path: 图片路径

        Returns:
            Tuple[bool, str]: (是否兼容, 原因)
        """
        try:
            # 检查文件扩展名
            ext = os.path.splitext(image_path)[1].lower()
            if ext not in self.supported_image_formats:
                return False, f"不支持的图片格式: {ext}，仅支持 {', '.join(self.supported_image_formats)}"

            # 检查文件大小 (限制为20MB)
            file_size = os.path.getsize(image_path) / (1024 * 1024)  # 转换为MB
            if file_size > self.max_image_size_mb:
                return False, f"图片过大 ({file_size:.2f}MB)，最大支持 {self.max_image_size_mb}MB"

            # 尝试打开图片以验证完整性
            try:
                with Image.open(image_path) as img:
                    # 检查图片是否过大
                    width, height = img.size
                    if width > 4096 or height > 4096:
                        return False, f"图片尺寸过大 ({width}x{height})，建议裁剪至4096x4096以内"

                    # 检查图片是否过小
                    if width < 16 or height < 16:
                        return False, f"图片尺寸过小 ({width}x{height})，应大于16x16"
            except Exception as e:
                return False, f"图片无法打开: {str(e)}"

            return True, "兼容"
        except Exception as e:
            return False, f"图片验证失败: {str(e)}"

    def prepare_image_for_api(self, image_path: str) -> Tuple[bool, str, str]:
        """
        准备用于API调用的图片数据

        Args:
            image_path: 图片路径

        Returns:
            Tuple[bool, str, str]: (是否成功, 图片base64数据, 错误信息)
        """
        try:
            # 首先检查图片兼容性
            is_compatible, reason = self.is_compatible_image(image_path)
            if not is_compatible:
                return False, "", reason

            # 获取MIME类型
            mime_type, _ = mimetypes.guess_type(image_path)
            if not mime_type:
                mime_type = "images/jpeg"  # 默认MIME类型

            # 读取并编码图片
            with open(image_path, "rb") as image_file:
                image_data = image_file.read()

            # 尝试压缩图片如果需要
            img_size_mb = len(image_data) / (1024 * 1024)
            if img_size_mb > 5:  # 如果大于5MB尝试压缩
                try:
                    with Image.open(BytesIO(image_data)) as img:
                        output = BytesIO()
                        # 转换为RGB模式（如果是RGBA）
                        if img.mode == 'RGBA':
                            img = img.convert('RGB')
                        # 压缩质量
                        img.save(output, format='JPEG', quality=85)
                        image_data = output.getvalue()
                except Exception as e:
                    logger.warning(f"图片压缩失败: {str(e)}，使用原始图片")

            # Base64编码
            base64_image = base64.b64encode(image_data).decode('utf-8')
            return True, f"data:{mime_type};base64,{base64_image}", ""

        except Exception as e:
            return False, "", f"准备图片数据失败: {str(e)}"

    def call_text_model(self, content: str, question: str) -> str:
        """
        调用文本模型进行问答

        Args:
            content: 文献内容
            question: 问题

        Returns:
            str: 模型回答
        """
        try:
            # 使用配置中的文本模型
            model_name = self.config.TEXT_MODEL

            # 设置提示词
            prompt = f"""请基于以下文献内容回答问题：

文献内容：
{content}

问题：{question}

请提供详细和准确的回答。如果文献中没有相关信息，请明确说明。"""

            data = {
                "model": model_name,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.1,
                "max_tokens": 2000
            }

            # 使用集中的API调用方法
            result = self._make_api_call(model_name, data)

            # 处理DeepSeek Reasoner模型的特殊返回
            if "choices" in result and "message" in result["choices"][0]:
                message = result["choices"][0]["message"]
                # 如果是推理模型，可能会返回reasoning_content
                if "reasoning_content" in message:
                    logger.info(f"模型推理过程: {message['reasoning_content'][:100]}...")

                return message["content"].strip()
            else:
                logger.error(f"API返回格式异常: {result}")
                return "API返回格式异常"

        except Exception as e:
            logger.error(f"调用文本模型时出错: {e}")
            return f"调用出错: {str(e)}"

    def call_vision_model(self, image_path: str) -> str:
        """
        调用视觉模型分析图片

        Args:
            image_path: 图片文件路径

        Returns:
            str: 图片分析结果
        """
        try:
            # 准备图片数据
            success, image_data, error_msg = self.prepare_image_for_api(image_path)
            if not success:
                return f"图片处理失败: {error_msg}"

            # 使用配置中的图像模型
            model_name = self.config.IMAGE_MODEL

            # 检查模型是否支持视觉
            model_supports_vision = False
            if model_name in self.available_models:
                model_supports_vision = self.available_models[model_name].get("supports_vision", False)

            if not model_supports_vision:
                return f"模型 {model_name} 不支持图像分析"

            question = """请详细分析这张图片，包括：
1. 图片类型（图表、流程图、架构图、实验结果等）
2. 主要内容和关键信息
3. 数据或结果的重要发现
4. 与研究方法或结论的关系"""

            # 使用正确的多模态格式
            data = {
                "model": model_name,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": question},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": image_data
                                }
                            }
                        ]
                    }
                ],
                "temperature": 0.1,
                "max_tokens": 1500
            }

            # 日志记录请求（不包含图片数据）
            logger.info(f"发送图片分析请求: 模型={model_name}, 文件={os.path.basename(image_path)}")

            try:
                # 直接使用请求而不是_make_api_call，以便更好地处理错误
                response = requests.post(
                    self._get_api_endpoint(model_name),
                    headers=self.headers,
                    json=data,
                    timeout=90  # 增加超时时间，图片分析可能需要更长时间
                )

                if response.status_code == 200:
                    result = response.json()
                    return result['choices'][0]['message']['content'].strip()
                else:
                    error_text = response.text if response.text else f"状态码: {response.status_code}"
                    logger.error(f"视觉模型API调用失败: {response.status_code} - {error_text}")

                    # 提供更具体的错误信息
                    if response.status_code == 422:
                        return f"图片格式不兼容或请求结构有误 (422): {error_text}"
                    else:
                        return f"API调用失败: {response.status_code} - {error_text}"

            except Exception as e:
                logger.error(f"发送视觉模型请求时出错: {str(e)}")
                return f"请求出错: {str(e)}"

        except Exception as e:
            logger.error(f"调用视觉模型时出错 {image_path}: {e}")
            return f"分析出错: {str(e)}"

    def extract_dataset_info(self, content: str) -> Dict[str, Any]:
        """
        从文献内容中提取数据集信息

        Args:
            content: 文献内容

        Returns:
            Dict: 数据集信息
        """
        try:
            # 使用配置中的文本模型
            model_name = self.config.TEXT_MODEL

            prompt = f"""请从以下文献内容中提取数据集相关信息，以JSON格式返回：

文献内容：
{content}

请提取以下信息（如果文献中没有相关信息，对应字段返回null）：
{{
    "datasets_used": ["数据集名称列表"],
    "dataset_sources": ["数据集来源或链接"],
    "dataset_sizes": ["数据集大小描述"],
    "data_preprocessing": "数据预处理方法描述",
    "evaluation_metrics": ["评估指标列表"],
    "experimental_setup": "实验设置描述"
}}

只返回JSON格式的结果，不要其他解释。"""

            data = {
                "model": model_name,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.1,
                "max_tokens": 1000
            }

            # 使用集中的API调用方法
            result = self._make_api_call(model_name, data)
            content = result['choices'][0]['message']['content'].strip()

            # 尝试解析JSON
            try:
                # 清理可能的markdown代码块标记
                if content.startswith('```'):
                    content = content.split('\n', 1)[1]
                if content.endswith('```'):
                    content = content.rsplit('\n', 1)[0]

                # 移除可能的json前缀
                if content.startswith('json'):
                    content = content[4:].strip()

                dataset_info = json.loads(content)
                return dataset_info
            except json.JSONDecodeError as e:
                logger.warning(f"解析数据集信息JSON失败: {e}")
                return {"raw_response": content}

        except Exception as e:
            logger.error(f"提取数据集信息时出错: {e}")
            return {"error": str(e)}

    def analyze_single_paper(self, paper_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析单篇论文

        Args:
            paper_info: 论文信息，包含paper_id, paper_dir, main_md_file等

        Returns:
            Dict: 分析结果
        """
        paper_id = paper_info.get('paper_id', 'unknown')
        paper_dir = paper_info.get('paper_dir', '')
        main_md_file = paper_info.get('main_md_file', '')

        logger.info(f"开始分析论文: {paper_id}")

        result = {
            "paper_id": paper_id,
            "title": paper_info.get('title', ''),
            "analysis_status": "processing",
            "qa_results": {},
            "dataset_info": {},
            "image_analysis": {},
            "summary": ""
        }

        try:
            # 1. 读取markdown文件内容
            if not main_md_file or not os.path.exists(main_md_file):
                logger.error(f"Markdown文件不存在: {main_md_file}")
                result["analysis_status"] = "failed"
                result["error"] = "Markdown文件不存在"
                return result

            md_content = self.read_markdown_content(main_md_file)
            if not md_content:
                logger.error(f"无法读取markdown内容: {main_md_file}")
                result["analysis_status"] = "failed"
                result["error"] = "无法读取markdown内容"
                return result

            # 2. 加载问题列表
            questions = self.read_question_file(self.config.QUESTION_FILE)
            if not questions:
                logger.warning("没有加载到问题，跳过问答分析")
            else:
                # 3. 对每个问题进行问答
                logger.info(f"开始问答分析，共 {len(questions)} 个问题")
                for i, question_data in enumerate(questions, 1):
                    question_title = question_data["title"]
                    question_content = question_data.get("content", "")

                    # 组合完整问题
                    full_question = question_title
                    if question_content:
                        full_question += "\n" + question_content

                    logger.info(f"处理问题 {i}/{len(questions)}: {question_title[:50]}...")

                    answer = self.call_text_model(md_content, full_question)
                    result["qa_results"][f"question_{i}"] = {
                        "title": question_title,
                        "content": question_content,
                        "answer": answer
                    }

            # 4. 提取数据集信息
            logger.info("提取数据集信息")
            result["dataset_info"] = self.extract_dataset_info(md_content)

            # 5. 分析图片
            image_files = self.get_image_files(paper_dir)
            if image_files:
                logger.info(f"开始分析 {len(image_files)} 张图片")
                for i, image_path in enumerate(image_files, 1):
                    logger.info(f"分析图片 {i}/{len(image_files)}: {os.path.basename(image_path)}")

                    # 先检查图片是否兼容
                    is_compatible, reason = self.is_compatible_image(image_path)
                    if not is_compatible:
                        logger.warning(f"图片 {os.path.basename(image_path)} 不兼容: {reason}")
                        result["image_analysis"][f"image_{i}"] = {
                            "file_path": image_path,
                            "file_name": os.path.basename(image_path),
                            "analysis": f"图片不兼容，无法处理: {reason}"
                        }
                        continue

                    # 调用视觉模型分析图片
                    image_analysis = self.call_vision_model(image_path)
                    result["image_analysis"][f"image_{i}"] = {
                        "file_path": image_path,
                        "file_name": os.path.basename(image_path),
                        "analysis": image_analysis
                    }

            # 6. 生成总结
            logger.info("生成论文分析总结")
            result["summary"] = self.generate_paper_summary(result)
            result["analysis_status"] = "completed"

            logger.info(f"论文分析完成: {paper_id}")

        except Exception as e:
            logger.error(f"分析论文 {paper_id} 时出错: {e}")
            result["analysis_status"] = "failed"
            result["error"] = str(e)

        return result

    def generate_paper_summary(self, analysis_result: Dict[str, Any]) -> str:
        """
        生成论文分析总结

        Args:
            analysis_result: 分析结果

        Returns:
            str: 总结文本
        """
        try:
            qa_count = len(analysis_result.get("qa_results", {}))
            image_count = len(analysis_result.get("image_analysis", {}))
            dataset_info = analysis_result.get("dataset_info", {})

            summary_parts = []
            summary_parts.append(f"论文ID: {analysis_result.get('paper_id', 'unknown')}")
            summary_parts.append(f"标题: {analysis_result.get('title', 'unknown')}")
            summary_parts.append(f"问答分析: 完成 {qa_count} 个问题的回答")

            # 统计成功分析的图片数量
            successful_images = 0
            for img_key, img_data in analysis_result.get("image_analysis", {}).items():
                if not img_data.get("analysis", "").startswith("图片不兼容") and not img_data.get("analysis",
                                                                                                  "").startswith(
                        "API调用失败"):
                    successful_images += 1

            summary_parts.append(f"图片分析: 尝试分析 {image_count} 张图片，成功 {successful_images} 张")

            # 数据集信息总结
            if isinstance(dataset_info, dict) and "datasets_used" in dataset_info:
                datasets = dataset_info.get("datasets_used", [])
                if datasets and datasets != [None]:
                    dataset_names = ', '.join(datasets) if isinstance(datasets, list) else str(datasets)
                    summary_parts.append(f"使用数据集: {dataset_names}")

            return "\n".join(summary_parts)

        except Exception as e:
            logger.error(f"生成总结时出错: {e}")
            return f"总结生成失败: {str(e)}"

    def save_analysis_result(self, paper_info: Dict[str, Any], analysis_result: Dict[str, Any]):
        """
        保存分析结果到文件

        Args:
            paper_info: 论文信息
            analysis_result: 分析结果
        """
        try:
            result_dir = paper_info.get('result_dir', '')
            if not result_dir:
                result_dir = os.path.join(paper_info.get('paper_dir', ''), 'result')

            os.makedirs(result_dir, exist_ok=True)

            # 保存完整分析结果
            result_file = os.path.join(result_dir, 'analysis_result.json')
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(analysis_result, f, ensure_ascii=False, indent=2)

            # 保存问答结果
            if analysis_result.get("qa_results"):
                qa_file = os.path.join(result_dir, 'qa_results.json')
                with open(qa_file, 'w', encoding='utf-8') as f:
                    json.dump(analysis_result["qa_results"], f, ensure_ascii=False, indent=2)

            # 保存数据集信息
            if analysis_result.get("dataset_info"):
                dataset_file = os.path.join(result_dir, 'dataset_info.json')
                with open(dataset_file, 'w', encoding='utf-8') as f:
                    json.dump(analysis_result["dataset_info"], f, ensure_ascii=False, indent=2)

            # 保存图片分析结果
            if analysis_result.get("image_analysis"):
                image_file = os.path.join(result_dir, 'image_analysis.json')
                with open(image_file, 'w', encoding='utf-8') as f:
                    json.dump(analysis_result["image_analysis"], f, ensure_ascii=False, indent=2)

            # 保存总结
            summary_file = os.path.join(result_dir, 'summary.txt')
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write(analysis_result.get("summary", ""))

            logger.info(f"分析结果已保存到: {result_dir}")

        except Exception as e:
            logger.error(f"保存分析结果失败: {e}")

    def analyze_papers(self, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        分析论文列表

        Args:
            papers: 论文信息列表

        Returns:
            List[Dict]: 分析结果列表
        """
        logger.info(f"开始分析 {len(papers)} 篇论文")

        results = []
        for i, paper_info in enumerate(papers, 1):
            logger.info(f"处理第 {i}/{len(papers)} 篇论文")

            try:
                # 分析单篇论文
                analysis_result = self.analyze_single_paper(paper_info)

                # 保存结果
                self.save_analysis_result(paper_info, analysis_result)

                results.append(analysis_result)

            except Exception as e:
                logger.error(f"处理第 {i} 篇论文时出错: {e}")
                results.append({
                    "paper_id": paper_info.get('paper_id', f'paper_{i}'),
                    "analysis_status": "failed",
                    "error": str(e)
                })

        logger.info(f"论文分析完成，成功分析 {len([r for r in results if r.get('analysis_status') == 'completed'])} 篇")
        return results
