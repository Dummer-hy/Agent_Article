# import os
# import sys
# from pathlib import Path
# from typing import List, Dict
#
# from config import config
# from utils import setup_directories, logger, save_excluded_papers
# from searcher import ArxivSearcher
# from processor import PaperProcessor
# from analyzer import PaperAnalyzer
#
#
# class LiteratureProcessor:
#     def __init__(self):
#         self.config = config
#         self.searcher = ArxivSearcher(self.config)
#         self.processor = PaperProcessor(self.config)
#         self.analyzer = PaperAnalyzer(self.config)
#
#     def initialize(self):
#         """初始化项目"""
#         setup_directories(self.config)
#
#         # 检查必要文件
#         if not os.path.exists(self.config.QUESTION_FILE):
#             logger.error(f"问题文件不存在: {self.config.QUESTION_FILE}")
#             logger.error("请确保question.txt文件存在并包含分析问题")
#             return False
#
#         # 检查API密钥
#         if not self.config.DEEPSEEK_API_KEY:
#             logger.error("DeepSeek API密钥未配置")
#             return False
#
#         return True
#
#     def display_menu(self):
#         """显示主菜单"""
#         print("\n" + "=" * 60)
#         print("文献处理系统")
#         print("=" * 60)
#         print("1. 搜索并处理文献")
#         print("2. 处理已下载的文献")
#         print("3. 重新分析已处理的文献")
#         print("4. 查看配置")
#         print("5. 查看论文目录结构")
#         print("6. 退出")
#         print("=" * 60)
#
#         choice = input("请选择操作 (1-6): ").strip()
#         return choice
#
#     def show_config(self):
#         """显示当前配置"""
#         print("\n当前配置:")
#         print(f"搜索模型: {self.config.SEARCH_MODEL}")
#         print(f"文本分析模型: {self.config.TEXT_MODEL}")
#         print(f"图像分析模型: {self.config.IMAGE_MODEL}")
#         print(f"最大搜索结果: {self.config.MAX_RESULTS}")
#         print(f"最大选择数量: {self.config.MAX_SELECTED}")
#         print(f"数据目录: {self.config.DATA_DIR}")
#         print(f"问题文件: {self.config.QUESTION_FILE}")
#         print(f"排除文件: {self.config.EXCLUDE_CSV}")
#         print(f"MinerU conda环境: {self.config.MINERU_CONDA_ENV}")
#         print(f"Arxiv conda环境: {self.config.ARXIV_CONDA_ENV}")
#
#     def show_paper_structure(self):
#         """显示论文目录结构"""
#         structure = self.processor.get_paper_directory_structure()
#
#         if not structure:
#             print("\n暂无已处理的论文")
#             return
#
#         print(f"\n已处理的论文目录结构 (共 {len(structure)} 篇):")
#         print("=" * 80)
#
#         for paper_name, subdirs in structure.items():
#             print(f"\n📁 {paper_name}")
#             for subdir in subdirs:
#                 if subdir == 'pdf':
#                     print(f"   ├── 📄 {subdir}/ (PDF文件)")
#                 elif subdir == 'MinerU_process':
#                     print(f"   ├── 📝 {subdir}/ (转换结果)")
#                 elif subdir == 'result':
#                     print(f"   └── 📊 {subdir}/ (分析结果)")
#
#     def search_and_process(self):
#         """搜索并处理文献的完整流程"""
#         # 1. 获取用户查询
#         query = input("\n请输入搜索关键词或描述: ").strip()
#         if not query:
#             logger.warning("搜索关键词不能为空")
#             return
#
#         # 2. 搜索文献
#         logger.info("开始搜索文献...")
#         papers = self.searcher.search_and_select(query)
#
#         if not papers:
#             logger.warning("未找到合适的文献")
#             return
#
#         # 3. 展示搜索结果
#         self.searcher.display_papers(papers)
#
#         # 4. 用户确认
#         confirm = input(f"\n是否处理这 {len(papers)} 篇文献? (y/n): ").strip().lower()
#         if confirm != 'y':
#             logger.info("用户取消操作")
#             return
#
#         # 5. 处理文献
#         logger.info("开始处理文献...")
#         processed_papers = self.processor.process_papers(papers)
#
#         if not processed_papers:
#             logger.warning("没有成功处理的文献")
#             return
#
#         # 6. 分析文献
#         logger.info("开始分析文献...")
#         successful_papers = [p for p in processed_papers if p['success']]
#
#         if successful_papers:
#             analysis_results = self.analyzer.analyze_papers(successful_papers)
#         else:
#             analysis_results = []
#
#         # 7. 更新排除列表
#         processed_titles = [paper.get('title', '') for paper in papers]
#         current_excluded = self.searcher.excluded_papers
#         updated_excluded = list(set(current_excluded + processed_titles))
#         save_excluded_papers(
#             self.config.EXCLUDE_CSV,
#             self.config.EXCLUDE_COLUMN,
#             updated_excluded
#         )
#
#         # 8. 显示结果
#         print(f"\n处理完成!")
#         print(f"成功处理: {len(successful_papers)} 篇文献")
#         print(f"分析完成: {len(analysis_results)} 篇文献")
#         print(f"结果保存在: {self.config.DATA_DIR}")
#
#     def process_existing(self):
#         """处理已下载的文献"""
#         # 检查data目录下是否有已存在的论文目录
#         if not os.path.exists(self.config.DATA_DIR):
#             logger.warning("数据目录不存在")
#             return
#
#         # 查找包含PDF的论文目录
#         existing_papers = []
#         for item in os.listdir(self.config.DATA_DIR):
#             item_path = os.path.join(self.config.DATA_DIR, item)
#             if os.path.isdir(item_path):
#                 pdf_dir = os.path.join(item_path, 'pdf')
#                 if os.path.exists(pdf_dir):
#                     pdf_files = list(Path(pdf_dir).glob("*.pdf"))
#                     if pdf_files:
#                         # 检查是否已经处理过
#                         mineru_dir = os.path.join(item_path, 'MinerU_process')
#                         if not os.path.exists(mineru_dir) or not os.listdir(mineru_dir):
#                             existing_papers.append({
#                                 'paper_dir': item_path,
#                                 'pdf_path': str(pdf_files[0]),
#                                 'paper_name': item
#                             })
#
#         if not existing_papers:
#             logger.warning("未找到需要处理的PDF文件")
#             return
#
#         print(f"\n找到 {len(existing_papers)} 个未处理的论文")
#         for i, paper in enumerate(existing_papers, 1):
#             print(f"{i}. {paper['paper_name']}")
#
#         confirm = input(f"\n是否处理这 {len(existing_papers)} 篇文献? (y/n): ").strip().lower()
#         if confirm != 'y':
#             logger.info("用户取消操作")
#             return
#
#         # 处理现有论文
#         processed_papers = []
#         for paper_info in existing_papers:
#             try:
#                 # 使用现有的PDF文件进行转换
#                 mineru_path = self.processor.convert_pdf_to_markdown(
#                     paper_info['pdf_path'],
#                     paper_info['paper_dir']
#                 )
#
#                 if mineru_path:
#                     # 构造处理结果
#                     result = {
#                         "paper_id": paper_info['paper_name'],
#                         "title": paper_info['paper_name'],
#                         "authors": [],
#                         "published": "",
#                         "success": True,
#                         "paper_dir": paper_info['paper_dir'],
#                         "pdf_path": paper_info['pdf_path'],
#                         "mineru_path": mineru_path,
#                         "main_md_file": self.processor._find_main_markdown_file(mineru_path),
#                         "result_dir": os.path.join(paper_info['paper_dir'], 'result')
#                     }
#
#                     # 分析图片
#                     image_analysis_results = self.processor.batch_analyze_images(paper_info['paper_dir'])
#                     if image_analysis_results:
#                         self.processor.save_image_analysis_results(paper_info['paper_dir'], image_analysis_results)
#                         result['image_analysis_completed'] = True
#                         result['total_images_analyzed'] = len(image_analysis_results)
#
#                     processed_papers.append(result)
#                     logger.info(f"处理完成: {paper_info['paper_name']}")
#                 else:
#                     logger.error(f"转换失败: {paper_info['paper_name']}")
#
#             except Exception as e:
#                 logger.error(f"处理 {paper_info['paper_name']} 时出错: {e}")
#
#         if processed_papers:
#             logger.info("开始分析文献...")
#             analysis_results = self.analyzer.analyze_papers(processed_papers)
#             print(f"处理完成: {len(analysis_results)} 篇文献")
#
#     def reanalyze_existing(self):
#         """重新分析已处理的文献"""
#         # 查找已处理的论文
#         if not os.path.exists(self.config.DATA_DIR):
#             logger.warning("数据目录不存在")
#             return
#
#         processed_papers = []
#         for item in os.listdir(self.config.DATA_DIR):
#             item_path = os.path.join(self.config.DATA_DIR, item)
#             if os.path.isdir(item_path):
#                 mineru_dir = os.path.join(item_path, 'MinerU_process')
#                 result_dir = os.path.join(item_path, 'result')
#
#                 # 检查是否有MinerU处理结果
#                 if os.path.exists(mineru_dir):
#                     main_md = self.processor._find_main_markdown_file(mineru_dir)
#                     if main_md:
#                         result = {
#                             "paper_id": item,
#                             "title": item,
#                             "authors": [],
#                             "published": "",
#                             "success": True,
#                             "paper_dir": item_path,
#                             "pdf_path": "",
#                             "mineru_path": mineru_dir,
#                             "main_md_file": main_md,
#                             "result_dir": result_dir
#                         }
#                         processed_papers.append(result)
#
#         if not processed_papers:
#             logger.warning("未找到已处理的文献")
#             return
#
#         print(f"\n找到 {len(processed_papers)} 个已处理的文献")
#         for i, paper in enumerate(processed_papers, 1):
#             print(f"{i}. {paper['paper_id']}")
#
#         confirm = input(f"\n是否重新分析这 {len(processed_papers)} 篇文献? (y/n): ").strip().lower()
#         if confirm != 'y':
#             logger.info("用户取消操作")
#             return
#
#         logger.info("开始重新分析文献...")
#         analysis_results = self.analyzer.analyze_papers(processed_papers)
#         print(f"重新分析完成: {len(analysis_results)} 篇文献")
#
#     def run(self):
#         """运行主程序"""
#         if not self.initialize():
#             logger.error("初始化失败")
#             return
#
#         logger.info("文献处理系统已启动")
#
#         while True:
#             choice = self.display_menu()
#
#             if choice == '1':
#                 self.search_and_process()
#             elif choice == '2':
#                 self.process_existing()
#             elif choice == '3':
#                 self.reanalyze_existing()
#             elif choice == '4':
#                 self.show_config()
#             elif choice == '5':
#                 self.show_paper_structure()
#             elif choice == '6':
#                 logger.info("退出系统")
#                 break
#             else:
#                 print("无效选择，请重新输入")
#
#             input("\n按Enter键继续...")
#
#
# if __name__ == "__main__":
#     processor = LiteratureProcessor()
#     processor.run()


import os
import sys
from pathlib import Path
from typing import List, Dict

from config import config
from utils import setup_directories, logger, save_excluded_papers
from searcher import ArxivSearcher
from processor import PaperProcessor
from analyzer import PaperAnalyzer


class LiteratureProcessor:
    def __init__(self):
        self.config = config
        self.searcher = ArxivSearcher(self.config)
        self.processor = PaperProcessor(self.config)
        self.analyzer = PaperAnalyzer(self.config)

    def initialize(self):
        """初始化项目"""
        setup_directories(self.config)

        # 检查必要文件
        if not os.path.exists(self.config.QUESTION_FILE):
            logger.error(f"问题文件不存在: {self.config.QUESTION_FILE}")
            logger.error("请确保question.txt文件存在并包含分析问题")
            return False

        # 检查API密钥
        if not self.config.DEEPSEEK_API_KEY:
            logger.error("DeepSeek API密钥未配置")
            return False

        return True

    def display_menu(self):
        """显示主菜单"""
        print("\n" + "=" * 60)
        print("文献处理系统")
        print("=" * 60)
        print("1. 搜索并选择下载文献")
        print("2. 处理已下载的文献")
        print("3. 重新分析已处理的文献")
        print("4. 查看配置")
        print("5. 查看论文目录结构")
        print("6. 退出")
        print("=" * 60)

        choice = input("请选择操作 (1-6): ").strip()
        return choice

    def show_config(self):
        """显示当前配置"""
        print("\n当前配置:")
        print(f"搜索模型: {self.config.SEARCH_MODEL}")
        print(f"文本分析模型: {self.config.TEXT_MODEL}")
        print(f"图像分析模型: {self.config.IMAGE_MODEL}")
        print(f"最大搜索结果: {self.config.MAX_RESULTS}")
        print(f"最大选择数量: {self.config.MAX_SELECTED}")
        print(f"数据目录: {self.config.DATA_DIR}")
        print(f"问题文件: {self.config.QUESTION_FILE}")
        print(f"排除文件: {self.config.EXCLUDE_CSV}")
        print(f"MinerU conda环境: {self.config.MINERU_CONDA_ENV}")
        print(f"Arxiv conda环境: {self.config.ARXIV_CONDA_ENV}")

    def show_paper_structure(self):
        """显示论文目录结构"""
        structure = self.processor.get_paper_directory_structure()

        if not structure:
            print("\n暂无已处理的论文")
            return

        print(f"\n已处理的论文目录结构 (共 {len(structure)} 篇):")
        print("=" * 80)

        for paper_name, subdirs in structure.items():
            print(f"\n📁 {paper_name}")
            for subdir in subdirs:
                if subdir == 'pdf':
                    print(f"   ├── 📄 {subdir}/ (PDF文件)")
                elif subdir == 'MinerU_process':
                    print(f"   ├── 📝 {subdir}/ (转换结果)")
                elif subdir == 'result':
                    print(f"   └── 📊 {subdir}/ (分析结果)")

    def get_user_selection(self, papers: List[Dict]) -> List[Dict]:
        """让用户选择要下载的论文"""
        if not papers:
            return []

        print("\n请选择要下载的论文（可以多选）:")
        print("输入格式示例:")
        print("  单个: 3")
        print("  多个: 1,3,5")
        print("  范围: 1-5")
        print("  组合: 1,3-5,8")
        print("  全部: all")
        print("  取消: cancel")

        while True:
            user_input = input("\n请输入选择: ").strip().lower()

            if user_input == 'cancel':
                return []

            if user_input == 'all':
                return papers

            try:
                selected_indices = self._parse_selection(user_input, len(papers))
                if selected_indices:
                    selected_papers = [papers[i - 1] for i in selected_indices]  # 转换为0-based索引

                    # 显示选择的论文
                    print(f"\n您选择了以下 {len(selected_papers)} 篇论文:")
                    for i, paper in enumerate(selected_papers, 1):
                        title = paper.get('title', 'Unknown Title')[:60]
                        print(f"{i}. {title}...")

                    confirm = input(f"\n确认下载这 {len(selected_papers)} 篇论文? (y/n): ").strip().lower()
                    if confirm == 'y':
                        return selected_papers
                    else:
                        print("请重新选择:")
                        continue
                else:
                    print("无效选择，请重新输入")
                    continue
            except Exception as e:
                print(f"输入格式错误: {e}")
                continue

    def _parse_selection(self, user_input: str, max_count: int) -> List[int]:
        """解析用户选择的编号"""
        indices = set()

        # 按逗号分割
        parts = [part.strip() for part in user_input.split(',')]

        for part in parts:
            if '-' in part:
                # 处理范围 (如 1-5)
                try:
                    start, end = map(int, part.split('-'))
                    if 1 <= start <= max_count and 1 <= end <= max_count and start <= end:
                        indices.update(range(start, end + 1))
                    else:
                        raise ValueError(f"范围 {part} 超出有效范围 1-{max_count}")
                except ValueError as e:
                    raise ValueError(f"无效范围格式: {part}")
            else:
                # 处理单个数字
                try:
                    num = int(part)
                    if 1 <= num <= max_count:
                        indices.add(num)
                    else:
                        raise ValueError(f"编号 {num} 超出有效范围 1-{max_count}")
                except ValueError:
                    raise ValueError(f"无效编号: {part}")

        return sorted(list(indices))

    def search_and_process(self):
        """搜索并选择下载文献的完整流程"""
        # 1. 获取用户查询
        query = input("\n请输入搜索关键词或描述: ").strip()
        if not query:
            logger.warning("搜索关键词不能为空")
            return

        # 2. 搜索文献
        logger.info("开始搜索文献...")
        papers = self.searcher.search_and_select(query)

        if not papers:
            logger.warning("未找到合适的文献")
            return

        # 3. 展示搜索结果
        self.searcher.display_papers(papers)

        # 4. 用户选择要下载的论文
        selected_papers = self.get_user_selection(papers)

        if not selected_papers:
            logger.info("用户取消操作或未选择论文")
            return

        # 5. 处理选中的文献
        logger.info(f"开始处理选中的 {len(selected_papers)} 篇文献...")
        processed_papers = self.processor.process_papers(selected_papers)

        if not processed_papers:
            logger.warning("没有成功处理的文献")
            return

        # 6. 分析文献
        logger.info("开始分析文献...")
        successful_papers = [p for p in processed_papers if p['success']]

        if successful_papers:
            analysis_results = self.analyzer.analyze_papers(successful_papers)
        else:
            analysis_results = []

        # 7. 更新排除列表（只排除已处理的论文）
        processed_titles = [paper.get('title', '') for paper in selected_papers]
        current_excluded = self.searcher.excluded_papers
        updated_excluded = list(set(current_excluded + processed_titles))
        save_excluded_papers(
            self.config.EXCLUDE_CSV,
            self.config.EXCLUDE_COLUMN,
            updated_excluded
        )

        # 8. 显示结果
        print(f"\n处理完成!")
        print(f"选择下载: {len(selected_papers)} 篇文献")
        print(f"成功处理: {len(successful_papers)} 篇文献")
        print(f"分析完成: {len(analysis_results)} 篇文献")
        print(f"结果保存在: {self.config.DATA_DIR}")

        # 9. 显示未下载的论文
        unselected_count = len(papers) - len(selected_papers)
        if unselected_count > 0:
            print(f"未下载: {unselected_count} 篇文献")
            save_unselected = input("是否保存未下载的论文列表? (y/n): ").strip().lower()
            if save_unselected == 'y':
                self._save_unselected_papers(papers, selected_papers)

    def _save_unselected_papers(self, all_papers: List[Dict], selected_papers: List[Dict]):
        """保存未选择的论文列表"""
        selected_titles = {paper.get('title', '') for paper in selected_papers}
        unselected_papers = [paper for paper in all_papers if paper.get('title', '') not in selected_titles]

        unselected_file = os.path.join(self.config.DATA_DIR, 'unselected_papers.txt')

        try:
            with open(unselected_file, 'w', encoding='utf-8') as f:
                f.write("未下载的论文列表\n")
                f.write("=" * 50 + "\n\n")

                for i, paper in enumerate(unselected_papers, 1):
                    f.write(f"{i}. {paper.get('title', 'Unknown Title')}\n")
                    f.write(f"   作者: {', '.join(paper.get('authors', []))}\n")
                    f.write(f"   发表时间: {paper.get('published', 'Unknown')}\n")
                    f.write(f"   链接: {paper.get('entry_id', '')}\n")
                    f.write(f"   摘要: {paper.get('summary', '')[:200]}...\n")
                    f.write("-" * 50 + "\n")

            print(f"未下载论文列表已保存到: {unselected_file}")

        except Exception as e:
            logger.error(f"保存未下载论文列表失败: {e}")

    def process_existing(self):
        """处理已下载的文献"""
        # 检查data目录下是否有已存在的论文目录
        if not os.path.exists(self.config.DATA_DIR):
            logger.warning("数据目录不存在")
            return

        # 查找包含PDF的论文目录
        existing_papers = []
        for item in os.listdir(self.config.DATA_DIR):
            item_path = os.path.join(self.config.DATA_DIR, item)
            if os.path.isdir(item_path):
                pdf_dir = os.path.join(item_path, 'pdf')
                if os.path.exists(pdf_dir):
                    pdf_files = list(Path(pdf_dir).glob("*.pdf"))
                    if pdf_files:
                        # 检查是否已经处理过
                        mineru_dir = os.path.join(item_path, 'MinerU_process')
                        if not os.path.exists(mineru_dir) or not os.listdir(mineru_dir):
                            existing_papers.append({
                                'paper_dir': item_path,
                                'pdf_path': str(pdf_files[0]),
                                'paper_name': item
                            })

        if not existing_papers:
            logger.warning("未找到需要处理的PDF文件")
            return

        print(f"\n找到 {len(existing_papers)} 个未处理的论文:")
        for i, paper in enumerate(existing_papers, 1):
            print(f"{i}. {paper['paper_name']}")

        # 让用户选择要处理的论文
        selected_papers = self._select_existing_papers(existing_papers)

        if not selected_papers:
            logger.info("用户取消操作或未选择论文")
            return

        # 处理选中的论文
        processed_papers = []
        for paper_info in selected_papers:
            try:
                # 使用现有的PDF文件进行转换
                mineru_path = self.processor.convert_pdf_to_markdown(
                    paper_info['pdf_path'],
                    paper_info['paper_dir']
                )

                if mineru_path:
                    # 构造处理结果
                    result = {
                        "paper_id": paper_info['paper_name'],
                        "title": paper_info['paper_name'],
                        "authors": [],
                        "published": "",
                        "success": True,
                        "paper_dir": paper_info['paper_dir'],
                        "pdf_path": paper_info['pdf_path'],
                        "mineru_path": mineru_path,
                        "main_md_file": self.processor._find_main_markdown_file(mineru_path),
                        "result_dir": os.path.join(paper_info['paper_dir'], 'result')
                    }

                    # 分析图片
                    image_analysis_results = self.processor.batch_analyze_images(paper_info['paper_dir'])
                    if image_analysis_results:
                        self.processor.save_image_analysis_results(paper_info['paper_dir'], image_analysis_results)
                        result['image_analysis_completed'] = True
                        result['total_images_analyzed'] = len(image_analysis_results)

                    processed_papers.append(result)
                    logger.info(f"处理完成: {paper_info['paper_name']}")
                else:
                    logger.error(f"转换失败: {paper_info['paper_name']}")

            except Exception as e:
                logger.error(f"处理 {paper_info['paper_name']} 时出错: {e}")

        if processed_papers:
            logger.info("开始分析文献...")
            analysis_results = self.analyzer.analyze_papers(processed_papers)
            print(f"处理完成: {len(analysis_results)} 篇文献")

    def _select_existing_papers(self, existing_papers: List[Dict]) -> List[Dict]:
        """选择要处理的现有论文"""
        print("\n请选择要处理的论文（输入格式同搜索结果选择）:")

        while True:
            user_input = input("请输入选择 (或输入 'all' 处理全部, 'cancel' 取消): ").strip().lower()

            if user_input == 'cancel':
                return []

            if user_input == 'all':
                return existing_papers

            try:
                selected_indices = self._parse_selection(user_input, len(existing_papers))
                if selected_indices:
                    selected_papers = [existing_papers[i - 1] for i in selected_indices]

                    print(f"\n您选择了以下 {len(selected_papers)} 篇论文:")
                    for i, paper in enumerate(selected_papers, 1):
                        print(f"{i}. {paper['paper_name']}")

                    confirm = input(f"\n确认处理这 {len(selected_papers)} 篇论文? (y/n): ").strip().lower()
                    if confirm == 'y':
                        return selected_papers
                    else:
                        continue
                else:
                    print("无效选择，请重新输入")
                    continue
            except Exception as e:
                print(f"输入格式错误: {e}")
                continue

    def reanalyze_existing(self):
        """重新分析已处理的文献"""
        # 查找已处理的论文
        if not os.path.exists(self.config.DATA_DIR):
            logger.warning("数据目录不存在")
            return

        processed_papers = []
        for item in os.listdir(self.config.DATA_DIR):
            item_path = os.path.join(self.config.DATA_DIR, item)
            if os.path.isdir(item_path):
                mineru_dir = os.path.join(item_path, 'MinerU_process')
                result_dir = os.path.join(item_path, 'result')

                # 检查是否有MinerU处理结果
                if os.path.exists(mineru_dir):
                    main_md = self.processor._find_main_markdown_file(mineru_dir)
                    if main_md:
                        result = {
                            "paper_id": item,
                            "title": item,
                            "authors": [],
                            "published": "",
                            "success": True,
                            "paper_dir": item_path,
                            "pdf_path": "",
                            "mineru_path": mineru_dir,
                            "main_md_file": main_md,
                            "result_dir": result_dir
                        }
                        processed_papers.append(result)

        if not processed_papers:
            logger.warning("未找到已处理的文献")
            return

        print(f"\n找到 {len(processed_papers)} 个已处理的文献:")
        for i, paper in enumerate(processed_papers, 1):
            print(f"{i}. {paper['paper_id']}")

        # 让用户选择要重新分析的论文
        selected_papers = self._select_processed_papers(processed_papers)

        if not selected_papers:
            logger.info("用户取消操作或未选择论文")
            return

        logger.info(f"开始重新分析选中的 {len(selected_papers)} 篇文献...")
        analysis_results = self.analyzer.analyze_papers(selected_papers)
        print(f"重新分析完成: {len(analysis_results)} 篇文献")

    def _select_processed_papers(self, processed_papers: List[Dict]) -> List[Dict]:
        """选择要重新分析的论文"""
        print("\n请选择要重新分析的论文:")

        while True:
            user_input = input("请输入选择 (或输入 'all' 分析全部, 'cancel' 取消): ").strip().lower()

            if user_input == 'cancel':
                return []

            if user_input == 'all':
                return processed_papers

            try:
                selected_indices = self._parse_selection(user_input, len(processed_papers))
                if selected_indices:
                    selected_papers = [processed_papers[i - 1] for i in selected_indices]

                    print(f"\n您选择了以下 {len(selected_papers)} 篇论文:")
                    for i, paper in enumerate(selected_papers, 1):
                        print(f"{i}. {paper['paper_id']}")

                    confirm = input(f"\n确认重新分析这 {len(selected_papers)} 篇论文? (y/n): ").strip().lower()
                    if confirm == 'y':
                        return selected_papers
                    else:
                        continue
                else:
                    print("无效选择，请重新输入")
                    continue
            except Exception as e:
                print(f"输入格式错误: {e}")
                continue

    def run(self):
        """运行主程序"""
        if not self.initialize():
            logger.error("初始化失败")
            return

        logger.info("文献处理系统已启动")

        while True:
            choice = self.display_menu()

            if choice == '1':
                self.search_and_process()
            elif choice == '2':
                self.process_existing()
            elif choice == '3':
                self.reanalyze_existing()
            elif choice == '4':
                self.show_config()
            elif choice == '5':
                self.show_paper_structure()
            elif choice == '6':
                logger.info("退出系统")
                break
            else:
                print("无效选择，请重新输入")

            input("\n按Enter键继续...")


if __name__ == "__main__":
    processor = LiteratureProcessor()
    processor.run()
