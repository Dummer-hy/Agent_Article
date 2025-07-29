##mineru -p "D:\test\Academic_Agent\data\processed\pdfs\2507.13338v1_Training Transformers with Enforced Lipschitz Constants.pdf" -o "D:\test\Academic_Agent\data\processed\markdown\2507.13338v1_Training Transformers wit"
# mineru --help
# mineru -p <input_path> -o <output_path>
import os
import subprocess
import requests
import json
import tempfile
import platform
import shutil
from typing import List, Dict, Optional
from utils import logger



class PaperProcessor:
    def __init__(self, config):
        self.config = config
        self.ensure_directories()

    def ensure_directories(self):
        """确保data根目录存在"""
        if not os.path.exists(self.config.DATA_DIR):
            os.makedirs(self.config.DATA_DIR, exist_ok=True)
            logger.info(f"创建根目录: {self.config.DATA_DIR}")

    def create_paper_directory(self, paper: Dict) -> str:
        """为每篇论文创建独立的目录结构"""
        # 清理文件名中的特殊字符作为文件夹名
        title = paper.get('title', 'Untitled')
        paper_id = paper.get('id', 'unknown')

        # 创建更安全的文件夹名，避免路径过长
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_title = safe_title[:50]  # 进一步限制长度，避免路径过长
        folder_name = f"{paper_id}_{safe_title}" if safe_title else paper_id

        # 论文根目录
        paper_dir = os.path.join(self.config.DATA_DIR, folder_name)

        # 创建子目录：pdf、MinerU_process、result
        subdirs = ['pdf', 'MinerU_process', 'result']
        for subdir in subdirs:
            subdir_path = os.path.join(paper_dir, subdir)
            os.makedirs(subdir_path, exist_ok=True)

        logger.info(f"创建论文目录: {paper_dir}")
        return paper_dir

    def download_pdf(self, paper: Dict, paper_dir: str) -> Optional[str]:
        """下载PDF文件到论文的pdf目录"""
        pdf_url = paper.get('pdf_url', '')
        if not pdf_url:
            logger.error(f"论文 {paper.get('id', 'Unknown')} 没有PDF链接")
            return None

        # PDF保存路径
        paper_id = paper.get('id', 'unknown')
        filename = f"{paper_id}.pdf"
        pdf_dir = os.path.join(paper_dir, 'pdf')
        filepath = os.path.join(pdf_dir, filename)

        try:
            logger.info(f"开始下载: {pdf_url}")
            response = requests.get(pdf_url, stream=True, timeout=300)
            response.raise_for_status()

            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            logger.info(f"PDF下载完成: {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"下载PDF失败: {e}")
            return None

    def convert_pdf_to_markdown_with_mineru(self, pdf_path: str, paper_dir: str) -> Optional[str]:
        """使用MinerU将PDF转换，自动检测完成并关闭cmd窗口"""
        try:
            import threading
            import time
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler

            # MinerU输出目录 - 所有转换结果都在这里
            mineru_dir = os.path.join(paper_dir, 'MinerU_process')

            # 检查conda环境是否存在
            if not self._check_mineru_env():
                logger.error("MinerU环境不可用")
                return None

            # 确保输出目录存在
            os.makedirs(mineru_dir, exist_ok=True)

            # 用于跟踪转换完成状态
            conversion_status = {
                'completed': False,
                'success': False,
                'start_time': time.time(),
                'md_file': None,
                'images_dir': None
            }

            # 文件监控处理器
            class ConversionWatcher(FileSystemEventHandler):
                def __init__(self, status_dict, target_dir):
                    self.status = status_dict
                    self.target_dir = target_dir

                def on_created(self, event):
                    if not event.is_directory:
                        self._check_completion()

                def on_modified(self, event):
                    if not event.is_directory:
                        self._check_completion()

                def _check_completion(self):
                    """检查MinerU转换是否完成"""
                    try:
                        # 等待文件写入完成
                        time.sleep(1)

                        # 检查目录是否存在
                        if not os.path.exists(self.target_dir):
                            return

                        # 查找MinerU_process下的子文件夹
                        try:
                            subdirs = [d for d in os.listdir(self.target_dir)
                                       if os.path.isdir(os.path.join(self.target_dir, d))]
                        except (OSError, PermissionError):
                            return

                        if not subdirs:
                            return

                        # MinerU_process下只会有一个文件夹
                        subdir = subdirs[0]
                        auto_dir = os.path.join(self.target_dir, subdir, 'auto')

                        if not os.path.exists(auto_dir):
                            return

                        # 检查auto目录下的md文件和images文件夹
                        try:
                            md_files = [f for f in os.listdir(auto_dir)
                                        if f.lower().endswith('.md')]
                        except (OSError, PermissionError):
                            return

                        images_dir = os.path.join(auto_dir, 'images')

                        if md_files and os.path.exists(images_dir):
                            md_file = os.path.join(auto_dir, md_files[0])

                            # 检查md文件大小（确保写入完成）
                            try:
                                if os.path.getsize(md_file) > 1000:  # 至少1KB
                                    self.status['completed'] = True
                                    self.status['success'] = True
                                    self.status['md_file'] = md_file
                                    self.status['images_dir'] = images_dir

                                    logger.info(f"转换完成！")
                                    logger.info(f"Markdown文件: {md_file}")
                                    logger.info(f"图片目录: {images_dir}")
                            except OSError:
                                return

                    except Exception as e:
                        logger.error(f"检查转换状态时出错: {e}")

            # 构建批处理文件内容
            batch_file_content = f'''@echo off
            echo ============================================
            echo 正在使用MinerU转换PDF文件...
            echo 输入文件: {pdf_path}
            echo 输出目录: {mineru_dir}
            echo ============================================
            echo.

            call conda activate {self.config.MINERU_CONDA_ENV}
            if errorlevel 1 (
                echo 错误: 无法激活conda环境 {self.config.MINERU_CONDA_ENV}
                exit /b 1
            )

            echo 已激活环境: {self.config.MINERU_CONDA_ENV}
            echo 开始转换...
            echo.
            set HF_ENDPOINT=https://hf-mirror.com
            set HF_HUB_DISABLE_SYMLINKS_WARNING=1
            mineru -p "{pdf_path}" -o "{mineru_dir}"

            if errorlevel 1 (
                echo.
                echo 转换失败！
                exit /b 1
            ) else (
                echo.
                echo 转换完成！
                echo 结果保存在: {mineru_dir}
            )

            :: 自动关闭窗口
            exit /b 0
            '''
            # 创建临时批处理文件
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.bat', delete=False, encoding='gbk') as f:
                f.write(batch_file_content)
                batch_file = f.name

            logger.info(f"启动MinerU转换...")
            logger.info(f"输入文件: {pdf_path}")
            logger.info(f"输出目录: {mineru_dir}")

            # 设置文件监控
            event_handler = ConversionWatcher(conversion_status, mineru_dir)
            observer = Observer()
            observer.schedule(event_handler, mineru_dir, recursive=True)
            observer.start()

            try:
                # 启动转换进程
                import subprocess
                import platform

                if platform.system() == "Windows":
                    # 在后台启动cmd窗口
                    process = subprocess.Popen(
                        ['cmd', '/c', batch_file],
                        creationflags=subprocess.CREATE_NEW_CONSOLE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )

                    print(f"\n{'=' * 60}")
                    print("MinerU转换已启动...")
                    print("正在后台处理，请稍候...")
                    print(f"{'=' * 60}")

                    # 监控转换进度
                    timeout = 600  # 10分钟超时
                    check_interval = 2  # 每2秒检查一次

                    while not conversion_status['completed']:
                        time.sleep(check_interval)

                        # 检查超时
                        elapsed = time.time() - conversion_status['start_time']
                        if elapsed > timeout:
                            logger.error("转换超时")
                            process.terminate()
                            break

                        # 检查进程是否仍在运行
                        if process.poll() is not None:
                            # 进程已结束，再等待几秒检查结果
                            time.sleep(3)

                            # 手动检查转换结果
                            self._manual_check_conversion(mineru_dir, conversion_status)
                            break

                        # 显示进度
                        dots = '.' * (int(elapsed) % 4)
                        print(f"\r转换进行中{dots}   ", end='', flush=True)

                else:
                    # Linux/Mac系统的处理
                    result = subprocess.run(
                        ['bash', '-c', f'''
                        conda activate {self.config.MINERU_CONDA_ENV} && \
                        mineru -p "{pdf_path}" -o "{mineru_dir}"
                        '''],
                        capture_output=True,
                        text=True,
                        timeout=600
                    )

                    if result.returncode == 0:
                        self._manual_check_conversion(mineru_dir, conversion_status)
                    else:
                        logger.error(f"转换失败: {result.stderr}")

            finally:
                # 停止文件监控
                observer.stop()
                observer.join()

                # 清理临时文件
                try:
                    os.unlink(batch_file)
                except:
                    pass

            # 检查最终结果
            if conversion_status['success']:
                conversion_info = self._analyze_mineru_output(mineru_dir)
                logger.info(f"转换结果: {conversion_info}")
                print(f"\n✅ 转换完成！")
                print(f"📄 Markdown文件: {conversion_status['md_file']}")
                print(f"🖼️  图片目录: {conversion_status['images_dir']}")
                return mineru_dir
            else:
                logger.error("转换失败或输出目录为空")
                print("\n❌ 转换失败")
                return None

        except Exception as e:
            logger.error(f"PDF转换过程中出错: {e}")
            return None

    def _manual_check_conversion(self, mineru_dir: str, conversion_status: dict):
        """手动检查转换结果"""
        try:
            if not os.path.exists(mineru_dir):
                return

            # 查找MinerU_process下的子文件夹
            subdirs = [d for d in os.listdir(mineru_dir)
                       if os.path.isdir(os.path.join(mineru_dir, d))]

            if not subdirs:
                return

            # MinerU_process下只会有一个文件夹
            subdir = subdirs[0]
            auto_dir = os.path.join(mineru_dir, subdir, 'auto')

            if not os.path.exists(auto_dir):
                return

            # 检查auto目录下的md文件和images文件夹
            md_files = [f for f in os.listdir(auto_dir)
                        if f.lower().endswith('.md')]
            images_dir = os.path.join(auto_dir, 'images')

            if md_files and os.path.exists(images_dir):
                md_file = os.path.join(auto_dir, md_files[0])

                # 检查md文件大小
                if os.path.getsize(md_file) > 1000:  # 至少1KB
                    conversion_status['completed'] = True
                    conversion_status['success'] = True
                    conversion_status['md_file'] = md_file
                    conversion_status['images_dir'] = images_dir

                    logger.info(f"转换完成！找到文件: {md_file}")

        except Exception as e:
            logger.error(f"手动检查转换结果时出错: {e}")

    def get_mineru_images_dir(self, mineru_dir: str) -> Optional[str]:
        """获取MinerU输出的images目录路径"""
        try:
            if not os.path.exists(mineru_dir):
                return None

            # 查找子文件夹
            subdirs = [d for d in os.listdir(mineru_dir)
                       if os.path.isdir(os.path.join(mineru_dir, d))]

            if not subdirs:
                return None

            # MinerU_process下只会有一个文件夹
            subdir = subdirs[0]
            images_dir = os.path.join(mineru_dir, subdir, 'auto', 'images')

            if os.path.exists(images_dir):
                return images_dir

            return None

        except Exception as e:
            logger.error(f"获取images目录时出错: {e}")
            return None

    def _analyze_mineru_output(self, mineru_dir: str) -> Dict:
        """分析MinerU输出结果"""
        try:
            info = {
                "status": "success",
                "subdir_name": "",
                "markdown_file": "",
                "images_dir": "",
                "image_count": 0,
                "total_files": 0
            }

            if not os.path.exists(mineru_dir):
                info["status"] = "directory_not_found"
                return info

            # 查找子文件夹
            subdirs = [d for d in os.listdir(mineru_dir)
                       if os.path.isdir(os.path.join(mineru_dir, d))]

            if not subdirs:
                info["status"] = "no_subdirectory"
                return info

            subdir = subdirs[0]
            info["subdir_name"] = subdir

            auto_dir = os.path.join(mineru_dir, subdir, 'auto')
            if not os.path.exists(auto_dir):
                info["status"] = "no_auto_directory"
                return info

            # 查找markdown文件
            md_files = [f for f in os.listdir(auto_dir)
                        if f.lower().endswith('.md')]

            if md_files:
                info["markdown_file"] = os.path.join(auto_dir, md_files[0])

            # 查找images目录
            images_dir = os.path.join(auto_dir, 'images')
            if os.path.exists(images_dir):
                info["images_dir"] = images_dir
                # 统计图片数量
                image_files = [f for f in os.listdir(images_dir)
                               if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp'))]
                info["image_count"] = len(image_files)

            # 统计总文件数
            for root, dirs, files in os.walk(auto_dir):
                info["total_files"] += len(files)

            return info

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "subdir_name": "",
                "markdown_file": "",
                "images_dir": "",
                "image_count": 0,
                "total_files": 0
            }

    def _find_main_markdown_file(self, mineru_dir: str) -> Optional[str]:
        """在MinerU输出目录中查找主要的markdown文件"""
        try:
            if not os.path.exists(mineru_dir):
                return None

            # 查找子文件夹
            subdirs = [d for d in os.listdir(mineru_dir)
                       if os.path.isdir(os.path.join(mineru_dir, d))]

            if not subdirs:
                return None

            # MinerU_process下只会有一个文件夹
            subdir = subdirs[0]
            auto_dir = os.path.join(mineru_dir, subdir, 'auto')

            if not os.path.exists(auto_dir):
                return None

            # 查找markdown文件
            md_files = [f for f in os.listdir(auto_dir)
                        if f.lower().endswith('.md')]

            if md_files:
                return os.path.join(auto_dir, md_files[0])

            return None

        except Exception as e:
            logger.error(f"查找主markdown文件时出错: {e}")
            return None
    def _check_mineru_env(self) -> bool:
        """检查MinerU conda环境是否存在"""
        try:
            conda_executable = self._get_conda_executable()
            result = subprocess.run(
                [conda_executable, "env", "list"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                return self.config.MINERU_CONDA_ENV in result.stdout
            else:
                logger.error(f"检查conda环境失败: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"检查MinerU环境时出错: {e}")
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

    def convert_pdf_to_markdown_fallback(self, pdf_path: str, paper_dir: str) -> Optional[str]:
        """备用PDF转换方法：使用PyMuPDF，输出到MinerU_process目录"""
        try:
            import fitz  # PyMuPDF
        except ImportError:
            logger.error("PyMuPDF未安装，无法使用备用转换方法")
            return None

        try:
            # 输出到MinerU_process目录
            paper_id = os.path.splitext(os.path.basename(pdf_path))[0]
            mineru_dir = os.path.join(paper_dir, 'MinerU_process')
            output_file = os.path.join(mineru_dir, f"{paper_id}_fallback.md")

            # 打开PDF文档
            doc = fitz.open(pdf_path)

            # 提取文本
            text_content = []
            text_content.append(f"# {paper_id}\n")
            text_content.append("*注：此文件由备用方法生成，可能缺少图片和格式信息*\n\n")

            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text = page.get_text()
                if text.strip():  # 只添加非空页面
                    text_content.append(f"## 第 {page_num + 1} 页\n\n{text}\n\n")

            # 保存为markdown文件
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(text_content))

            doc.close()
            logger.info(f"备用方法转换完成: {output_file}")
            return mineru_dir

        except Exception as e:
            logger.error(f"备用转换方法失败: {e}")
            return None

    def convert_pdf_to_markdown(self, pdf_path: str, paper_dir: str) -> Optional[str]:
        """主要的PDF转换方法"""
        # 优先使用MinerU
        result = self.convert_pdf_to_markdown_with_mineru(pdf_path, paper_dir)

        # 如果MinerU失败，使用备用方法
        if not result:
            logger.info("MinerU转换失败，尝试备用方法")
            result = self.convert_pdf_to_markdown_fallback(pdf_path, paper_dir)

        return result

    def get_images_in_directory(self, mineru_dir: str) -> List[str]:
        """获取MinerU_process目录中的图片信息"""
        if not os.path.exists(mineru_dir):
            return []

        image_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg']
        images = []

        for root, dirs, files in os.walk(mineru_dir):
            for file in files:
                if any(file.lower().endswith(ext) for ext in image_extensions):
                    images.append(os.path.join(root, file))

        return images

    def save_paper_metadata(self, paper: Dict, paper_dir: str, processing_result: Dict):
        """保存论文元数据到result目录"""
        result_dir = os.path.join(paper_dir, 'result')
        metadata_file = os.path.join(result_dir, 'metadata.json')

        # 分析MinerU输出
        mineru_analysis = {}
        if processing_result.get('mineru_path'):
            mineru_analysis = self._analyze_mineru_output(processing_result['mineru_path'])

        metadata = {
            'paper_info': paper,
            'processing_result': processing_result,
            'mineru_analysis': mineru_analysis,
            'directory_structure': {
                'pdf_dir': os.path.join(paper_dir, 'pdf'),
                'mineru_dir': os.path.join(paper_dir, 'MinerU_process'),
                'result_dir': os.path.join(paper_dir, 'result')
            },
            'files_count': {
                'markdown_files': 1 if mineru_analysis.get('markdown_file') else 0,
                'image_files': mineru_analysis.get('image_count', 0),
                'other_files': mineru_analysis.get('total_files', 0) - mineru_analysis.get('image_count', 0) - (
                    1 if mineru_analysis.get('markdown_file') else 0)
            }
        }

        try:
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            logger.info(f"元数据保存完成: {metadata_file}")
        except Exception as e:
            logger.error(f"保存元数据失败: {e}")

    def process_paper(self, paper: Dict) -> Dict:
        """处理单篇论文"""
        paper_id = paper.get('id', 'unknown')
        logger.info(f"开始处理论文: {paper_id}")

        result = {
            'paper_id': paper_id,
            'title': paper.get('title', ''),
            'authors': paper.get('authors', []),
            'published': paper.get('published', ''),
            'success': False,
            'paper_dir': None,
            'pdf_path': None,
            'mineru_path': None,  # 替代md_path和img_dir
            'main_md_file': None,
            'result_dir': None,
            'error': None
        }

        try:
            # 1. 创建论文目录结构
            paper_dir = self.create_paper_directory(paper)
            result['paper_dir'] = paper_dir
            result['result_dir'] = os.path.join(paper_dir, 'result')

            # 2. 下载PDF
            pdf_path = self.download_pdf(paper, paper_dir)
            if not pdf_path:
                result['error'] = "PDF下载失败"
                self.save_paper_metadata(paper, paper_dir, result)
                return result

            result['pdf_path'] = pdf_path

            # 3. 转换PDF（MinerU处理）
            mineru_path = self.convert_pdf_to_markdown(pdf_path, paper_dir)
            if not mineru_path:
                result['error'] = "PDF转换失败"
                self.save_paper_metadata(paper, paper_dir, result)
                return result

            result['mineru_path'] = mineru_path

            # 4. 查找主要的markdown文件
            main_md = self._find_main_markdown_file(mineru_path)
            if main_md:
                result['main_md_file'] = main_md

            result['success'] = True

            # 5. 保存处理结果和元数据
            self.save_paper_metadata(paper, paper_dir, result)

            logger.info(f"论文处理完成: {paper_id}")
            logger.info(f"论文目录: {paper_dir}")
            logger.info(f"MinerU输出: {mineru_path}")

        except Exception as e:
            logger.error(f"处理论文时出错: {e}")
            result['error'] = str(e)
            if result['paper_dir']:
                self.save_paper_metadata(paper, result['paper_dir'], result)

        return result

    def process_papers(self, papers: List[Dict]) -> List[Dict]:
        """批量处理论文"""
        logger.info(f"开始处理 {len(papers)} 篇论文")

        results = []
        for paper in papers:
            result = self.process_paper(paper)
            results.append(result)

        # 统计处理结果
        successful = sum(1 for r in results if r['success'])
        logger.info(f"处理完成: {successful}/{len(papers)} 篇成功")

        # 生成批量处理报告
        self.generate_batch_report(results)

        return results

    def generate_batch_report(self, results: List[Dict]):
        """生成批量处理报告"""
        report_path = os.path.join(self.config.DATA_DIR, 'batch_processing_report.json')

        # 统计信息
        total_markdown_files = 0
        total_image_files = 0

        for result in results:
            if result['success'] and result['mineru_path']:
                analysis = self._analyze_mineru_output(result['mineru_path'])
                if analysis.get('markdown_file'):
                    total_markdown_files += 1
                total_image_files += analysis.get('image_count', 0)

        report = {
            'total_papers': len(results),
            'successful_papers': sum(1 for r in results if r['success']),
            'failed_papers': sum(1 for r in results if not r['success']),
            'total_markdown_files': total_markdown_files,
            'total_image_files': total_image_files,
            'processing_details': results
        }

        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            logger.info(f"批量处理报告生成: {report_path}")
        except Exception as e:
            logger.error(f"生成报告失败: {e}")

    def get_paper_directory_structure(self) -> Dict[str, List[str]]:
        """获取所有论文的目录结构概览"""
        if not os.path.exists(self.config.DATA_DIR):
            return {}

        structure = {}
        for item in os.listdir(self.config.DATA_DIR):
            item_path = os.path.join(self.config.DATA_DIR, item)
            if os.path.isdir(item_path) and not item.endswith('.json'):
                # 检查是否是论文目录（包含预期的子目录）
                expected_subdirs = ['pdf', 'MinerU_process', 'result']
                actual_subdirs = []
                for subdir in expected_subdirs:
                    subdir_path = os.path.join(item_path, subdir)
                    if os.path.exists(subdir_path):
                        actual_subdirs.append(subdir)

                if actual_subdirs:  # 至少有一个预期的子目录
                    structure[item] = actual_subdirs

        return structure
