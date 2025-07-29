# import os
# import subprocess
# import json
# import re
# import tempfile
# import platform
# import shutil
# from typing import List, Dict, Optional
# from utils import logger, call_api, load_excluded_papers
#
#
# class ArxivSearcher:
#     def __init__(self, config):
#         self.config = config
#         self.excluded_papers = load_excluded_papers(
#             config.EXCLUDE_CSV,
#             config.EXCLUDE_COLUMN
#         )
#
#     def expand_keywords(self, initial_keyword: str) -> List[str]:
#         """使用大模型扩充计算病理学相关关键词"""
#         prompt = f"""
#         请根据输入的关键词，扩充生成计算病理学和深度学习医学图像分析相关的英文学术检索关键词。
#         输入关键词：{initial_keyword}
#         要求：
#         1. 生成3-8个相关的学术关键词
#         2. 重点关注以下领域：
#            - 计算病理学 (computational pathology)
#            - 数字病理学 (digital pathology)
#            - 全切片图像分析 (whole slide image analysis)
#            - 深度学习在病理学中的应用
#            - 医学图像处理和分析
#            - 病理图像分割、分类、检测
#            - 癌症诊断和预后预测
#            - 组织学图像分析
#         3. 包含相关的技术术语、方法名称、应用场景
#         4. 适合在医学和计算机科学学术论文搜索中使用
#         5. 用逗号分隔，不要编号
#         6. 只返回关键词列表，不要其他说明
#         示例相关关键词：computational pathology, digital pathology, whole slide image, histopathology, deep learning, convolutional neural networks, image segmentation, cancer detection, tissue classification, pathology AI
#         请基于输入关键词生成相关扩展：
#         """
#         response = call_api(self.config.SEARCH_MODEL, [
#             {"role": "user", "content": prompt}
#         ], self.config)
#         if not response:
#             logger.warning("关键词扩充失败，使用计算病理学默认关键词")
#             # 提供计算病理学领域的默认关键词
#             default_keywords = [
#                 initial_keyword,
#                 "computational pathology",
#                 "digital pathology",
#                 "whole slide image",
#                 "histopathology",
#                 "deep learning pathology",
#                 "medical image analysis",
#                 "cancer detection",
#                 "tissue segmentation"
#             ]
#             return default_keywords
#         keywords = [kw.strip() for kw in response.split(',')]
#         keywords = [kw for kw in keywords if kw and len(kw) > 2]  # 移除空字符串和过短的词
#         if initial_keyword not in keywords:
#             keywords.insert(0, initial_keyword)
#         core_keywords = [
#             "computational pathology",
#             "digital pathology",
#             "whole slide image",
#             "histopathology deep learning"
#         ]
#
#         for core_kw in core_keywords:
#             if not any(core_kw.lower() in kw.lower() for kw in keywords):
#                 keywords.append(core_kw)
#         keywords = keywords[:10]
#         logger.info(f"计算病理关键词扩充: {len(keywords)} 个关键词")
#         return keywords
#
#     def search_arxiv_with_mcp(self, keywords: List[str], max_results: int = 20) -> List[Dict]:
#         """使用arxiv-mcp-server搜索论文"""
#         # 首先检查conda环境是否存在
#         if not self._check_conda_env():
#             logger.warning("conda环境不可用，使用直接搜索")
#             return self.search_arxiv_direct(keywords, max_results)
#
#         all_papers = []
#
#         for keyword in keywords[:]:  # 限制使用前3个关键词
#             logger.info(f"使用MCP搜索关键词: {keyword}")
#
#             try:
#                 # 修复：使用正确的脚本格式
#                 search_script = f"""import sys
# import json
# try:
#     import arxiv
#
#     search = arxiv.Search(
#         query="{keyword}",
#         max_results={max_results // len(keywords[:3])},
#         sort_by=arxiv.SortCriterion.SubmittedDate
#     )
#
#     papers = []
#     for result in search.results():
#         paper = {{
#             "id": result.get_short_id(),
#             "title": result.title,
#             "summary": result.summary,
#             "authors": [author.name for author in result.authors],
#             "published": result.published.isoformat() if result.published else "",
#             "pdf_url": result.pdf_url,
#             "arxiv_url": result.entry_id
#         }}
#         papers.append(paper)
#
#     print(json.dumps(papers, ensure_ascii=False))
# except Exception as e:
#     print(json.dumps([], ensure_ascii=False))
#     sys.stderr.write(f"Error: {{str(e)}}")
# """
#
#                 # 写入临时脚本文件
#                 with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
#                     f.write(search_script)
#                     script_path = f.name
#
#                 try:
#                     # 使用绝对路径和正确的命令格式
#                     conda_executable = self._get_conda_executable()
#                     cmd = [conda_executable, "run", "-n", self.config.ARXIV_CONDA_ENV, "python", script_path]
#
#                     result = subprocess.run(
#                         cmd,
#                         capture_output=True,
#                         text=True,
#                         timeout=60,
#                         cwd=os.getcwd()  # 确保在正确的工作目录
#                     )
#
#                     if result.returncode == 0:
#                         try:
#                             papers = json.loads(result.stdout)
#                             all_papers.extend(papers)
#                             logger.info(f"MCP搜索找到 {len(papers)} 篇论文")
#                         except json.JSONDecodeError as e:
#                             logger.error(f"解析MCP搜索结果失败: {e}")
#                     else:
#                         logger.error(f"MCP搜索失败: {result.stderr}")
#
#                 finally:
#                     # 清理临时文件
#                     try:
#                         os.unlink(script_path)
#                     except:
#                         pass
#
#             except Exception as e:
#                 logger.error(f"MCP搜索关键词 {keyword} 时出错: {e}")
#
#         # 如果MCP搜索没有结果，回退到直接搜索
#         if not all_papers:
#             logger.info("MCP搜索无结果，使用直接搜索")
#             return self.search_arxiv_direct(keywords, max_results)
#
#         return all_papers
#
#     def _check_conda_env(self) -> bool:
#         """检查conda环境是否存在"""
#         try:
#             conda_executable = self._get_conda_executable()
#             result = subprocess.run(
#                 [conda_executable, "env", "list"],
#                 capture_output=True,
#                 text=True,
#                 timeout=10
#             )
#
#             if result.returncode == 0:
#                 return self.config.ARXIV_CONDA_ENV in result.stdout
#             else:
#                 logger.error(f"检查conda环境失败: {result.stderr}")
#                 return False
#
#         except Exception as e:
#             logger.error(f"检查conda环境时出错: {e}")
#             return False
#
#     def _get_conda_executable(self) -> str:
#         """获取conda可执行文件路径"""
#         conda_executable = "conda"
#
#         if platform.system() == "Windows":
#             # 在Windows上尝试找到conda
#             possible_paths = [
#                 "conda",
#                 "C:\\ProgramData\\Anaconda3\\Scripts\\conda.exe",
#                 "C:\\Users\\%USERNAME%\\Anaconda3\\Scripts\\conda.exe",
#                 "C:\\Users\\%USERNAME%\\Miniconda3\\Scripts\\conda.exe",
#                 os.path.expanduser("~/Anaconda3/Scripts/conda.exe"),
#                 os.path.expanduser("~/Miniconda3/Scripts/conda.exe")
#             ]
#
#             for path in possible_paths:
#                 try:
#                     expanded_path = os.path.expandvars(path)
#                     if os.path.exists(expanded_path):
#                         conda_executable = expanded_path
#                         break
#                 except:
#                     continue
#
#         return conda_executable
#
#     def search_arxiv_direct(self, keywords: List[str], max_results: int = 20) -> List[Dict]:
#         """直接使用arxiv包搜索（备用方案）"""
#         try:
#             import arxiv
#         except ImportError:
#             logger.error("请安装arxiv包: pip install arxiv")
#             return []
#
#         all_papers = []
#
#         for keyword in keywords[:]:  # 限制使用前3个关键词
#             logger.info(f"直接搜索关键词: {keyword}")
#
#             try:
#                 search = arxiv.Search(
#                     query=keyword,
#                     max_results=max_results // len(keywords[:3]),
#                     sort_by=arxiv.SortCriterion.SubmittedDate
#                 )
#
#                 papers = []
#                 for result in search.results():
#                     paper = {
#                         "id": result.get_short_id(),
#                         "title": result.title,
#                         "summary": result.summary,
#                         "authors": [author.name for author in result.authors],
#                         "published": result.published.isoformat() if result.published else "",
#                         "pdf_url": result.pdf_url,
#                         "arxiv_url": result.entry_id
#                     }
#                     papers.append(paper)
#
#                 all_papers.extend(papers)
#                 logger.info(f"直接搜索找到 {len(papers)} 篇论文")
#
#             except Exception as e:
#                 logger.error(f"直接搜索关键词 {keyword} 时出错: {e}")
#
#         return all_papers
#
#     def search_arxiv(self, keywords: List[str], max_results: int = 20) -> List[Dict]:
#         """主搜索方法：优先使用MCP，失败时使用直接搜索"""
#         # 先尝试MCP搜索
#         papers = self.search_arxiv_with_mcp(keywords, max_results)
#
#         # 如果MCP搜索失败，使用直接搜索
#         if not papers:
#             logger.info("MCP搜索失败，使用直接搜索")
#             papers = self.search_arxiv_direct(keywords, max_results)
#
#         # 去重
#         unique_papers = {}
#         for paper in papers:
#             paper_id = paper.get('id', paper.get('arxiv_id', ''))
#             if paper_id not in unique_papers:
#                 unique_papers[paper_id] = paper
#
#         papers_list = list(unique_papers.values())
#         logger.info(f"去重后共 {len(papers_list)} 篇论文")
#
#         return papers_list
#
#     def filter_papers(self, papers: List[Dict]) -> List[Dict]:
#         """过滤已处理的论文"""
#         filtered_papers = []
#
#         for paper in papers:
#             title = paper.get('title', '').strip()
#             if title not in self.excluded_papers:
#                 filtered_papers.append(paper)
#
#         logger.info(f"过滤后剩余 {len(filtered_papers)} 篇论文")
#         return filtered_papers
#
#     def intelligent_screening(self, papers: List[Dict], user_query: str) -> List[Dict]:
#         """智能筛选最相关的论文"""
#         if len(papers) <= self.config.MAX_SELECTED:
#             return papers
#
#         # 构建论文信息摘要
#         papers_info = []
#         for i, paper in enumerate(papers):
#             info = f"{i + 1}. 标题: {paper.get('title', 'N/A')}\n"
#             info += f"   摘要: {paper.get('summary', 'N/A')[:200]}...\n"
#             info += f"   作者: {', '.join(paper.get('authors', [])[:3])}\n"
#             papers_info.append(info)
#
#         papers_text = '\n'.join(papers_info)
#
#         prompt = f"""
#         用户查询: {user_query}
#
#         以下是搜索到的论文列表：
#         {papers_text}
#
#         请根据用户查询，选择最相关的{self.config.MAX_SELECTED}篇论文。
#
#         要求：
#         1. 分析每篇论文摘要与用户查询的相关性
#         2. 选择最符合需求的论文，用户研究领域为深度学习、医学图像、计算病理学领域
#         3. 只返回选中论文的编号（如：1,3,5,7,9）
#         4. 不要其他说明文字
#         """
#
#         response = call_api(self.config.SEARCH_MODEL, [
#             {"role": "user", "content": prompt}
#         ], self.config)
#
#         if not response:
#             logger.warning("智能筛选失败，返回前几篇论文")
#             return papers[:self.config.MAX_SELECTED]
#
#         # 解析选中的论文编号
#         try:
#             selected_indices = [int(x.strip()) - 1 for x in response.split(',')]
#             selected_papers = [papers[i] for i in selected_indices if 0 <= i < len(papers)]
#
#             if not selected_papers:
#                 logger.warning("未能解析筛选结果，返回前几篇论文")
#                 return papers[:self.config.MAX_SELECTED]
#
#             logger.info(f"智能筛选完成，选中 {len(selected_papers)} 篇论文")
#             return selected_papers
#
#         except Exception as e:
#             logger.error(f"解析筛选结果时出错: {e}")
#             return papers[:self.config.MAX_SELECTED]
#
#     def search_and_select(self, user_query: str) -> List[Dict]:
#         """完整的搜索和筛选流程"""
#         logger.info(f"开始搜索: {user_query}")
#
#         # 1. 扩充关键词
#         keywords = self.expand_keywords(user_query)
#
#         # 2. 搜索论文（优先使用MCP）
#         papers = self.search_arxiv(keywords, self.config.MAX_RESULTS)
#
#         # 3. 过滤已处理的论文
#         papers = self.filter_papers(papers)
#
#         # 4. 智能筛选
#         if papers:
#             selected_papers = self.intelligent_screening(papers, user_query)
#             return selected_papers
#         else:
#             logger.warning("未找到新的论文")
#             return []
#
#     def display_papers(self, papers: List[Dict]) -> None:
#         """展示论文列表供用户确认"""
#         print("\n" + "=" * 80)
#         print("搜索结果 - 推荐论文列表")
#         print("=" * 80)
#
#         for i, paper in enumerate(papers, 1):
#             print(f"\n{i}. {paper.get('title', 'N/A')}")
#             print(f"   作者: {', '.join(paper.get('authors', [])[:3])}")
#             print(f"   发表时间: {paper.get('published', 'N/A')}")
#             print(f"   摘要: {paper.get('summary', 'N/A')[:200]}...")
#             print(f"   链接: {paper.get('arxiv_url', 'N/A')}")
#
#         print("\n" + "=" * 80)


import os
import subprocess
import json
import re
import tempfile
import platform
import shutil
import hashlib
from typing import List, Dict, Optional
from utils import logger, call_api, load_excluded_papers
from collections import defaultdict
from config import config  # Import the config


class ArxivSearcher:
    def __init__(self, config):
        self.config = config
        self.excluded_papers = load_excluded_papers(
            config.EXCLUDE_CSV,
            config.EXCLUDE_COLUMN
        )

    def expand_keywords(self, initial_keyword: str) -> List[str]:
        """重新设计：生成MIL+医学图像领域的精确关键词"""

        # 领域特定术语库
        MIL_TERMS = {
            "core": ["multiple instance learning", "MIL", "weakly supervised learning", "instance-level learning"],
            "methods": ["attention-based MIL", "bag-level classification", "instance aggregation", "mil framework"],
            "variants": ["deep mil", "attention mil", "gated attention", "additive attention"]
        }

        MEDICAL_TERMS = {
            "imaging": ["whole slide image", "WSI", "histopathology", "computational pathology", "digital pathology"],
            "analysis": ["pathological image analysis", "medical image analysis", "histological analysis"],
            "applications": ["cancer detection", "tumor classification", "tissue classification", "lesion detection"]
        }

        # 智能关键词匹配和扩展
        user_input_lower = initial_keyword.lower()

        # 确定主关键词
        main_keyword = None
        if any(term in user_input_lower for term in ["mil", "多示例", "multiple instance"]):
            main_keyword = "multiple instance learning"
        elif any(term in user_input_lower for term in ["病理", "pathology", "histology"]):
            if "mil" in user_input_lower or "多示例" in user_input_lower:
                main_keyword = "multiple instance learning histopathology"
            else:
                main_keyword = "computational pathology"
        elif any(term in user_input_lower for term in ["wsi", "whole slide", "全切片"]):
            main_keyword = "whole slide image analysis"
        else:
            # 使用LLM理解用户意图
            main_keyword = self._generate_main_keyword_with_llm(initial_keyword)

        # 生成筛选关键词（针对MIL+医学图像的组合）
        filter_keywords = [
            "computational pathology",
            "whole slide image",
            "weakly supervised learning"
        ]

        # 如果主关键词已经包含某个筛选词，替换为更具体的术语
        final_filters = []
        for fk in filter_keywords:
            if fk.split()[0] not in main_keyword.lower():
                final_filters.append(fk)

        # 补充到3个筛选关键词
        additional_terms = ["histopathology analysis", "medical image classification", "deep learning pathology"]
        for term in additional_terms:
            if len(final_filters) < 3 and term not in final_filters:
                final_filters.append(term)

        result = [main_keyword] + final_filters[:3]
        logger.info(f"优化后的关键词组合: {result}")

        return result

    def _generate_main_keyword_with_llm(self, initial_keyword: str) -> str:
        """使用LLM生成主关键词"""
        prompt = f"""
    根据用户输入"{initial_keyword}"，生成一个最适合在学术数据库中搜索MIL+医学图像相关论文的主关键词。

    要求：
    1. 如果输入与多示例学习相关，优先生成包含"multiple instance learning"的组合
    2. 如果输入与医学图像相关，结合"pathology"或"medical image"
    3. 生成的关键词应该是2-4个单词的学术术语组合
    4. 优先使用英文术语

    只返回一个最佳的主关键词，不要解释。

    示例：
    - "mil病理" → "multiple instance learning pathology"
    - "弱监督WSI" → "weakly supervised whole slide image"
    - "组织分类" → "tissue classification pathology"
    """

        try:
            response = call_api(self.config.SEARCH_MODEL, [
                {"role": "user", "content": prompt}
            ], self.config)

            if response and len(response.strip()) > 0:
                return response.strip()
        except Exception as e:
            logger.error(f"LLM生成主关键词失败: {e}")

        # 备用方案
        return initial_keyword if len(initial_keyword.split()) <= 4 else "multiple instance learning"

    def search_arxiv_with_mcp(self, keywords: List[str], max_results: int = 200) -> List[Dict]:
        """重新设计的MIL+医学图像智能搜索系统"""

        MAX_RESULTS = self.config.MAX_RESULTS
        MAX_SELECTED = self.config.MAX_SELECTED

        # 1. 关键词预处理
        if len(keywords) < 4:
            user_input = keywords[0] if keywords else "multiple instance learning"
            search_keywords = self.expand_keywords(user_input)
        else:
            search_keywords = keywords[:4]

        main_keyword = search_keywords[0]
        constraint_keywords = search_keywords[1:4]

        logger.info(f"=== MIL+医学图像搜索开始 ===")
        logger.info(f"用户输入: {keywords[0] if keywords else '默认搜索'}")
        logger.info(f"主关键词: {main_keyword}")
        logger.info(f"约束关键词: {constraint_keywords}")

        # 2. 多策略精准搜索
        all_papers = self._precision_search_pipeline(main_keyword, constraint_keywords, max_results)

        if not all_papers:
            logger.error("所有搜索策略均未找到相关论文")
            return []

        # 3. 领域特定去重和预处理
        unique_papers = self._domain_aware_deduplicate(all_papers)
        logger.info(f"去重后共 {len(unique_papers)} 篇论文")

        # 4. 专业筛选管道
        final_papers = self._expert_filter_pipeline(unique_papers, main_keyword, constraint_keywords, MAX_SELECTED)
        logger.info(f"=== 最终筛选出 {len(final_papers)} 篇高相关性论文 ===")

        return final_papers

    def _precision_search_pipeline(self, main_keyword: str, constraint_keywords: List[str], max_results: int) -> List[
        Dict]:
        """精准搜索管道：专门针对MIL+医学图像"""

        all_papers = []

        # 策略1: 核心概念精确匹配
        logger.info("策略1: 核心概念精确搜索")
        core_queries = self._build_core_queries(main_keyword, constraint_keywords)

        for query in core_queries:
            logger.info(f"执行查询: {query}")
            papers = self.search_arxiv_direct([query], max_results // len(core_queries))
            if papers:
                # 快速相关性检查
                relevant_papers = [p for p in papers if self._quick_relevance_check(p, main_keyword)]
                logger.info(f"查询 '{query}' 返回 {len(papers)} 篇，相关 {len(relevant_papers)} 篇")
                all_papers.extend(relevant_papers)

        # 策略2: 如果结果不足，使用组合搜索
        if len(all_papers) < 30:
            logger.info("策略2: 组合概念搜索")
            combo_papers = self._combination_search_v2(main_keyword, constraint_keywords, max_results // 2)
            all_papers.extend(combo_papers)

        # 策略3: 如果仍然不足，使用语义扩展搜索
        if len(all_papers) < 20:
            logger.info("策略3: 语义扩展搜索")
            semantic_papers = self._semantic_expansion_search(main_keyword, constraint_keywords, max_results // 3)
            all_papers.extend(semantic_papers)

        return all_papers

    def _build_core_queries(self, main_keyword: str, constraint_keywords: List[str]) -> List[str]:
        """构建核心查询，针对MIL+医学图像优化"""

        queries = []

        # MIL相关的精确查询
        mil_terms = ["multiple instance learning", "MIL", "weakly supervised learning"]
        medical_terms = ["pathology", "histopathology", "whole slide image", "WSI", "medical image"]

        # 核心组合查询
        if any(mil_term in main_keyword.lower() for mil_term in ["mil", "multiple instance", "weakly supervised"]):
            # MIL为主的查询
            for mil_term in mil_terms:
                for med_term in medical_terms:
                    if mil_term.lower() in main_keyword.lower() or med_term in " ".join(constraint_keywords).lower():
                        queries.append(f'"{mil_term}" AND "{med_term}"')

            # 添加具体应用查询
            queries.extend([
                f'"{main_keyword}" AND "cancer detection"',
                f'"{main_keyword}" AND "tissue classification"',
                '"multiple instance learning" AND "computational pathology"'
            ])
        else:
            # 医学图像为主的查询
            queries.extend([
                f'"{main_keyword}" AND "deep learning"',
                f'"{main_keyword}" AND "classification"',
                main_keyword  # 直接搜索
            ])

        return list(set(queries))  # 去重

    def _quick_relevance_check(self, paper: Dict, main_keyword: str) -> bool:
        """快速相关性检查"""

        title = paper.get('title', '').lower()
        abstract = paper.get('summary', '')[:300].lower()
        content = title + ' ' + abstract

        # MIL+医学图像的关键指标
        mil_indicators = ['mil', 'multiple instance', 'weakly supervised', 'bag-level', 'instance-level']
        medical_indicators = ['pathology', 'histopathology', 'medical image', 'wsi', 'whole slide', 'tissue', 'cancer']

        has_mil = any(indicator in content for indicator in mil_indicators)
        has_medical = any(indicator in content for indicator in medical_indicators)

        # 主关键词匹配
        main_terms = main_keyword.lower().split()
        has_main_concept = any(term in content for term in main_terms if len(term) > 2)

        # 至少满足两个条件之一：(MIL+医学) 或 (主概念+其一)
        return (has_mil and has_medical) or (has_main_concept and (has_mil or has_medical))

    def _combination_search_v2(self, main_keyword: str, constraint_keywords: List[str], max_results: int) -> List[Dict]:
        """改进的组合搜索"""

        combo_papers = []

        # 主关键词与每个约束关键词的组合
        for constraint in constraint_keywords:
            # 智能组合策略
            if "learning" in main_keyword and "pathology" in constraint:
                combo_query = f'"{main_keyword}" AND "{constraint}"'
            elif "mil" in main_keyword.lower():
                combo_query = f'"multiple instance learning" AND "{constraint}"'
            else:
                combo_query = f"{main_keyword} {constraint}"

            logger.info(f"组合查询: {combo_query}")
            papers = self.search_arxiv_direct([combo_query], max_results // len(constraint_keywords))

            # 过滤相关论文
            relevant = [p for p in papers if self._quick_relevance_check(p, main_keyword)]
            combo_papers.extend(relevant)
            logger.info(f"组合查询返回 {len(papers)} 篇，相关 {len(relevant)} 篇")

        return combo_papers

    def _semantic_expansion_search(self, main_keyword: str, constraint_keywords: List[str], max_results: int) -> List[
        Dict]:
        """语义扩展搜索"""

        # 生成语义相关的搜索词
        semantic_terms = self._generate_semantic_terms(main_keyword, constraint_keywords)

        expansion_papers = []
        for term in semantic_terms:
            papers = self.search_arxiv_direct([term], max_results // len(semantic_terms))
            relevant = [p for p in papers if self._quick_relevance_check(p, main_keyword)]
            expansion_papers.extend(relevant)
            logger.info(f"语义扩展 '{term}' 返回 {len(relevant)} 篇相关论文")

        return expansion_papers

    def _generate_semantic_terms(self, main_keyword: str, constraint_keywords: List[str]) -> List[str]:
        """生成语义相关术语"""

        # 基于领域知识的语义扩展
        semantic_map = {
            "multiple instance learning": ["attention mechanism learning", "bag-of-instances", "mil framework"],
            "computational pathology": ["digital pathology", "pathology AI", "histological analysis"],
            "whole slide image": ["gigapixel image", "slide-level analysis", "WSI processing"],
            "weakly supervised": ["semi-supervised", "self-supervised", "label-efficient"]
        }

        expanded_terms = []

        # 根据主关键词和约束关键词扩展
        all_keywords = [main_keyword] + constraint_keywords

        for keyword in all_keywords:
            for key, values in semantic_map.items():
                if any(word in keyword.lower() for word in key.split()):
                    expanded_terms.extend(values)

        # 添加一些通用的组合
        expanded_terms.extend([
            "attention-based pathology",
            "weakly supervised histopathology",
            "deep learning medical imaging"
        ])

        return list(set(expanded_terms))[:5]  # 最多5个语义扩展词

    def _domain_aware_deduplicate(self, papers: List[Dict]) -> List[Dict]:
        """领域感知的去重"""

        seen_signatures = set()
        unique_papers = []

        for paper in papers:
            title = paper.get('title', '').strip()
            # 创建论文签名（标题+作者首字母+年份）
            authors = paper.get('authors', [])
            author_signature = ''.join([a.split()[-1][:2] if a.split() else '' for a in authors[:2]])
            year = paper.get('published', '')[:4] if paper.get('published') else ''

            signature = f"{title.lower()}_{author_signature}_{year}"

            if signature not in seen_signatures:
                seen_signatures.add(signature)
                unique_papers.append(paper)

        return unique_papers

    def _expert_filter_pipeline(self, papers: List[Dict], main_keyword: str, constraint_keywords: List[str],
                                max_count: int) -> List[Dict]:
        """专家级筛选管道"""

        if not papers:
            return []

        logger.info("开始专家级筛选")

        # 阶段1: 领域相关性评分
        scored_papers = []
        for paper in papers:
            score = self._calculate_domain_relevance_score(paper, main_keyword, constraint_keywords)
            if score >= 0.4:  # 提高阈值，确保质量
                paper['_relevance_score'] = score
                scored_papers.append(paper)

        logger.info(f"领域相关性筛选: {len(papers)} -> {len(scored_papers)} 篇")

        if not scored_papers:
            logger.warning("没有通过相关性筛选的论文")
            return []

        # 按分数排序
        scored_papers.sort(key=lambda x: x['_relevance_score'], reverse=True)

        # 阶段2: LLM专家验证
        if len(scored_papers) <= max_count:
            return scored_papers
        else:
            return self._llm_expert_validation_v2(scored_papers[:max_count * 2], main_keyword, constraint_keywords,
                                                  max_count)

    def _calculate_domain_relevance_score(self, paper: Dict, main_keyword: str,
                                          constraint_keywords: List[str]) -> float:
        """计算领域相关性得分"""

        title = paper.get('title', '').lower()
        abstract = paper.get('summary', '')[:400].lower()
        content = title + ' ' + abstract

        score = 0.0

        # MIL相关性检查 (权重0.4)
        mil_patterns = [
            r'\bmil\b', r'multiple instance learning', r'weakly supervised.*learning',
            r'bag.*level', r'instance.*level', r'attention.*mil', r'deep.*mil'
        ]
        mil_score = sum(2 if re.search(pattern, title) else 1
                        for pattern in mil_patterns if re.search(pattern, content))
        score += min(mil_score, 4) * 0.4

        # 医学图像相关性检查 (权重0.35)
        medical_patterns = [
            r'pathology', r'histopathology', r'whole slide image', r'\bwsi\b',
            r'computational pathology', r'digital pathology', r'medical image',
            r'histological', r'tissue.*analysis', r'cancer.*detection'
        ]
        medical_score = sum(2 if re.search(pattern, title) else 1
                            for pattern in medical_patterns if re.search(pattern, content))
        score += min(medical_score, 4) * 0.35

        # 主关键词匹配 (权重0.25)
        main_terms = [term for term in main_keyword.lower().split() if len(term) > 2]
        main_score = sum(3 if term in title else 1 for term in main_terms if term in content)
        score += min(main_score, 3) * 0.25

        # 奖励因子：标题中同时包含MIL和医学术语
        if (any(re.search(p, title) for p in mil_patterns) and
                any(re.search(p, title) for p in medical_patterns)):
            score += 1.0

        return min(score, 5.0) / 5.0  # 归一化

    def _llm_expert_validation_v2(self, papers: List[Dict], main_keyword: str, constraint_keywords: List[str],
                                  max_count: int) -> List[Dict]:
        """LLM专家验证V2"""

        papers_info = []
        for i, paper in enumerate(papers):
            title = paper.get('title', '')
            abstract = paper.get('summary', '')[:250]  # 限制长度
            score = paper.get('_relevance_score', 0)

            papers_info.append(f"""
    论文 {i + 1} (相关性: {score:.2f}):
    标题: {title}
    摘要: {abstract}...
    """)

        papers_text = '\n'.join(papers_info)

        prompt = f"""
    你是计算病理学和弱监督学习领域的顶级专家。请从以下论文中筛选出真正关于"{main_keyword}"的高质量研究。

    专业筛选标准:
    1. 论文必须真正使用多示例学习(MIL)方法，不是仅仅提及
    2. 必须应用于医学图像分析，特别是病理图像、组织学图像或WSI
    3. 有实际的方法创新或重要的实验验证
    4. 严格排除与MIL+医学图像主题不符的论文

    相关领域: {', '.join(constraint_keywords)}

    候选论文:
    {papers_text}

    请从 {len(papers)} 篇中选择最相关的 {max_count} 篇。如果高质量论文不足 {max_count} 篇，请只返回真正符合标准的论文。

    返回JSON格式:
    {{"selected": [论文编号], "reasons": ["选择理由"]}}

    要求: 宁可少选也不要选择主题不匹配的论文。每个选择理由需要说明为什么这篇论文符合MIL+医学图像的标准。
    """

        try:
            response = call_api(self.config.SEARCH_MODEL, [
                {"role": "user", "content": prompt}
            ], self.config)

            if response:
                import json, re
                json_match = re.search(r'\{.*?\}', response, re.DOTALL)

                if json_match:
                    try:
                        result = json.loads(json_match.group())
                        selected_indices = result.get('selected', [])
                        reasons = result.get('reasons', [])

                        selected_papers = []
                        for i, idx in enumerate(selected_indices):
                            if isinstance(idx, int) and 1 <= idx <= len(papers):
                                paper = papers[idx - 1]
                                paper['selection_reason'] = reasons[i] if i < len(reasons) else "专家推荐"
                                selected_papers.append(paper)

                        logger.info(f"LLM专家验证完成: 选中 {len(selected_papers)} 篇高质量论文")
                        return selected_papers

                    except json.JSONDecodeError as e:
                        logger.warning(f"JSON解析失败: {e}")

            logger.warning("LLM验证失败，使用高分论文作为备选")
            return papers[:max_count]

        except Exception as e:
            logger.error(f"LLM专家验证出错: {e}")
            return papers[:max_count]

    def _check_conda_env(self) -> bool:
        """检查conda环境是否存在"""
        try:
            conda_executable = self._get_conda_executable()
            result = subprocess.run(
                [conda_executable, "env", "list"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                return self.config.ARXIV_CONDA_ENV in result.stdout
            else:
                logger.error(f"检查conda环境失败: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"检查conda环境时出错: {e}")
            return False

    def _get_conda_executable(self) -> str:
        """获取conda可执行文件路径"""
        conda_executable = "conda"

        if platform.system() == "Windows":
            # 在Windows上尝试找到conda
            possible_paths = [
                "conda",
                "C:\\ProgramData\\Anaconda3\\Scripts\\conda.exe",
                "C:\\Users\\%USERNAME%\\Anaconda3\\Scripts\\conda.exe",
                "C:\\Users\\%USERNAME%\\Miniconda3\\Scripts\\conda.exe",
                os.path.expanduser("~/Anaconda3/Scripts/conda.exe"),
                os.path.expanduser("~/Miniconda3/Scripts/conda.exe")
            ]

            for path in possible_paths:
                try:
                    expanded_path = os.path.expandvars(path)
                    if os.path.exists(expanded_path):
                        conda_executable = expanded_path
                        break
                except:
                    continue

        return conda_executable

    def search_arxiv_direct(self, keywords: List[str], max_results: int = 20) -> List[Dict]:
        """直接使用arxiv包搜索（备用方案）"""
        try:
            import arxiv
        except ImportError:
            logger.error("请安装arxiv包: pip install arxiv")
            return []

        all_papers = []

        for keyword in keywords[:3]:  # 限制使用前3个关键词
            logger.info(f"直接搜索关键词: {keyword}")

            try:
                search = arxiv.Search(
                    query=keyword,
                    max_results=max_results // min(len(keywords), 3),
                    sort_by=arxiv.SortCriterion.SubmittedDate
                )

                papers = []
                for result in search.results():
                    paper = {
                        "id": result.get_short_id(),
                        "title": result.title,
                        "summary": result.summary,
                        "authors": [author.name for author in result.authors],
                        "published": result.published.isoformat() if result.published else "",
                        "pdf_url": result.pdf_url,
                        "arxiv_url": result.entry_id
                    }
                    papers.append(paper)

                all_papers.extend(papers)
                logger.info(f"直接搜索找到 {len(papers)} 篇论文")

            except Exception as e:
                logger.error(f"直接搜索关键词 {keyword} 时出错: {e}")

        return all_papers

    def search_arxiv(self, keywords: List[str], max_results: int = 20) -> List[Dict]:
        """主搜索方法：优先使用MCP，失败时使用直接搜索"""
        # 先尝试MCP搜索
        papers = self.search_arxiv_with_mcp(keywords, max_results)

        # 如果MCP搜索失败，使用直接搜索
        if not papers:
            logger.info("MCP搜索失败，使用直接搜索")
            papers = self.search_arxiv_direct(keywords, max_results)

        # 去重
        unique_papers = {}
        for paper in papers:
            paper_id = paper.get('id', paper.get('arxiv_id', ''))
            if paper_id not in unique_papers:
                unique_papers[paper_id] = paper

        papers_list = list(unique_papers.values())
        logger.info(f"去重后共 {len(papers_list)} 篇论文")

        return papers_list

    def filter_papers(self, papers: List[Dict]) -> List[Dict]:
        """过滤已处理的论文"""
        filtered_papers = []

        for paper in papers:
            title = paper.get('title', '').strip()
            if title not in self.excluded_papers:
                filtered_papers.append(paper)

        logger.info(f"过滤后剩余 {len(filtered_papers)} 篇论文")
        return filtered_papers

    def intelligent_screening(self, papers: List[Dict], user_query: str) -> List[Dict]:
        """智能筛选最相关的论文"""
        if len(papers) <= self.config.MAX_SELECTED:
            return papers

        # 构建论文信息摘要
        papers_info = []
        for i, paper in enumerate(papers):
            info = f"{i + 1}. 标题: {paper.get('title', 'N/A')}\n"
            info += f"   摘要: {paper.get('summary', 'N/A')[:200]}...\n"
            info += f"   作者: {', '.join(paper.get('authors', [])[:3])}\n"
            papers_info.append(info)

        papers_text = '\n'.join(papers_info)

        prompt = f"""
        用户查询: {user_query}

        以下是搜索到的论文列表：
        {papers_text}

        请根据用户查询，选择最相关的{self.config.MAX_SELECTED}篇论文。

        要求：
        1. 分析每篇论文摘要与用户查询的相关性
        2. 选择最符合需求的论文，用户研究领域为深度学习、医学图像、计算病理学领域
        3. 只返回选中论文的编号（如：1,3,5,7,9）
        4. 不要其他说明文字
        """

        response = call_api(self.config.SEARCH_MODEL, [
            {"role": "user", "content": prompt}
        ], self.config)

        if not response:
            logger.warning("智能筛选失败，返回前几篇论文")
            return papers[:self.config.MAX_SELECTED]

        # 解析选中的论文编号
        try:
            selected_indices = [int(x.strip()) - 1 for x in response.split(',')]
            selected_papers = [papers[i] for i in selected_indices if 0 <= i < len(papers)]

            if not selected_papers:
                logger.warning("未能解析筛选结果，返回前几篇论文")
                return papers[:self.config.MAX_SELECTED]

            logger.info(f"智能筛选完成，选中 {len(selected_papers)} 篇论文")
            return selected_papers

        except Exception as e:
            logger.error(f"解析筛选结果时出错: {e}")
            return papers[:self.config.MAX_SELECTED]

    def search_and_select(self, user_query: str) -> List[Dict]:
        """完整的搜索和筛选流程"""
        logger.info(f"开始搜索: {user_query}")

        # 1. 扩充关键词
        keywords = self.expand_keywords(user_query)

        # 2. 搜索论文（优先使用MCP）
        papers = self.search_arxiv(keywords, self.config.MAX_RESULTS)

        # 3. 过滤已处理的论文
        papers = self.filter_papers(papers)

        # 4. 智能筛选
        if papers:
            selected_papers = self.intelligent_screening(papers, user_query)
            return selected_papers
        else:
            logger.warning("未找到新的论文")
            return []

    def display_papers(self, papers: List[Dict]) -> None:
        """展示论文列表供用户确认"""
        print("\n" + "=" * 80)
        print("搜索结果 - 推荐论文列表")
        print("=" * 80)

        for i, paper in enumerate(papers, 1):
            print(f"\n{i}. {paper.get('title', 'N/A')}")
            print(f"   作者: {', '.join(paper.get('authors', [])[:3])}")
            print(f"   发表时间: {paper.get('published', 'N/A')}")
            print(f"   摘要: {paper.get('summary', 'N/A')[:200]}...")
            print(f"   链接: {paper.get('arxiv_url', 'N/A')}")

        print("\n" + "=" * 80)
