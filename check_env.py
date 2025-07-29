import os
import subprocess
import requests
from typing import Dict, List, Optional, Tuple
from config import config, AVAILABLE_MODELS


class APIChecker:
    """API检查器类，基于config.py中的配置"""

    def __init__(self):
        # 从config.py读取配置
        self.available_models = AVAILABLE_MODELS
        self.config = config

    def get_api_key(self, model_name: str) -> Optional[str]:
        """从配置中获取API密钥"""
        model_config = self.available_models.get(model_name)
        if not model_config:
            return None

        api_key_env = model_config["api_key"]
        return getattr(self.config, api_key_env.replace("_API_KEY", "_API_KEY"), "")

    def test_api_connection(self, model_name: str, api_key: str) -> Tuple[bool, str]:
        """测试API连接"""
        model_config = self.available_models.get(model_name)
        if not model_config:
            return False, "模型配置未找到"

        try:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }

            data = {
                "model": model_name,
                "messages": [{"role": "user", "content": "测试连接"}],
                "max_tokens": 10,
                "stream": False
            }

            response = requests.post(
                model_config["endpoint"],
                headers=headers,
                json=data,
                timeout=15
            )

            if response.status_code == 200:
                return True, "连接成功"
            else:
                return False, f"连接失败 ({response.status_code}): {response.text[:200]}"

        except requests.exceptions.Timeout:
            return False, "连接超时"
        except requests.exceptions.ConnectionError:
            return False, "网络连接错误"
        except Exception as e:
            return False, f"测试失败: {str(e)}"

    def check_configured_models(self) -> Dict[str, Dict]:
        """检查配置文件中的所有模型"""
        results = {}

        for model_name, model_config in self.available_models.items():
            result = {
                "model_name": model_name,
                "endpoint": model_config["endpoint"],
                "supports_vision": model_config.get("supports_vision", False),
                "api_key_configured": False,
                "api_key_length": 0,
                "connection_success": False,
                "error_message": "",
                "is_current_model": False
            }

            # 检查是否为当前使用的模型
            current_models = [
                self.config.SEARCH_MODEL,
                self.config.TEXT_MODEL,
                self.config.IMAGE_MODEL
            ]
            result["is_current_model"] = model_name in current_models

            # 检查API密钥
            api_key = self.get_api_key(model_name)
            if api_key:
                result["api_key_configured"] = True
                result["api_key_length"] = len(api_key)

                # 测试连接
                success, message = self.test_api_connection(model_name, api_key)
                result["connection_success"] = success
                result["error_message"] = message
            else:
                result["error_message"] = f"API密钥未配置 ({model_config['api_key']})"

            results[model_name] = result

        return results

    def print_model_status(self, results: Dict[str, Dict]):
        """打印模型状态"""
        print("=== 模型配置检查 ===")

        # 当前使用的模型
        print("当前配置的模型:")
        print(f"  搜索模型: {self.config.SEARCH_MODEL}")
        print(f"  文本模型: {self.config.TEXT_MODEL}")
        print(f"  图像模型: {self.config.IMAGE_MODEL}")
        print()

        # 统计信息
        total_models = len(results)
        configured_models = sum(1 for r in results.values() if r["api_key_configured"])
        working_models = sum(1 for r in results.values() if r["connection_success"])
        current_working = sum(1 for r in results.values() if r["is_current_model"] and r["connection_success"])

        print(f"总计: {total_models} 个可用模型")
        print(f"已配置密钥: {configured_models} 个")
        print(f"连接正常: {working_models} 个")
        print(f"当前模型可用: {current_working}/3")
        print()

        # 详细结果
        for model_name, result in results.items():
            status_symbol = "✓" if result["connection_success"] else "✗"
            current_mark = " (当前使用)" if result["is_current_model"] else ""
            vision_mark = " [支持视觉]" if result["supports_vision"] else ""

            print(f"{status_symbol} {model_name}{current_mark}{vision_mark}")
            print(f"  端点: {result['endpoint']}")

            if result["api_key_configured"]:
                print(f"  密钥: 已配置 (长度: {result['api_key_length']})")
                print(f"  状态: {result['error_message']}")
            else:
                print(f"  密钥: {result['error_message']}")
            print()


def check_api_keys():
    """检查API密钥配置"""
    checker = APIChecker()
    results = checker.check_configured_models()
    checker.print_model_status(results)

    # 检查关键配置
    print("=== 关键配置检查 ===")
    critical_issues = []

    # 检查当前使用的模型是否可用
    current_models = [config.SEARCH_MODEL, config.TEXT_MODEL, config.IMAGE_MODEL]
    for model in current_models:
        if model in results:
            if not results[model]["connection_success"]:
                critical_issues.append(f"当前使用的模型 {model} 不可用")
        else:
            critical_issues.append(f"当前使用的模型 {model} 未在AVAILABLE_MODELS中定义")

    if critical_issues:
        print("⚠️  发现关键问题:")
        for issue in critical_issues:
            print(f"   - {issue}")
    else:
        print("✓ 所有当前使用的模型都可正常工作")

    return results


def check_conda_envs():
    """检查conda环境"""
    print("\n=== Conda环境检查 ===")

    try:
        # 检查conda是否可用
        result = subprocess.run(["conda", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✓ Conda: {result.stdout.strip()}")
        else:
            print("✗ Conda: 未安装或不在PATH中")
            return
    except FileNotFoundError:
        print("✗ Conda: 未找到")
        return

    # 检查配置中的环境
    try:
        result = subprocess.run(["conda", "env", "list"], capture_output=True, text=True)
        if result.returncode == 0:
            envs = result.stdout

            # 检查Arxiv环境
            if config.ARXIV_CONDA_ENV in envs:
                print(f"✓ Arxiv环境 '{config.ARXIV_CONDA_ENV}': 存在")
            else:
                print(f"✗ Arxiv环境 '{config.ARXIV_CONDA_ENV}': 不存在")

            # 检查MinerU环境
            if config.MINERU_CONDA_ENV in envs:
                print(f"✓ MinerU环境 '{config.MINERU_CONDA_ENV}': 存在")
            else:
                print(f"✗ MinerU环境 '{config.MINERU_CONDA_ENV}': 不存在")

            # 显示所有可用环境
            print("\n可用环境:")
            for line in envs.split('\n'):
                if line.strip() and not line.startswith('#'):
                    env_name = line.strip().split()[0]
                    if env_name in [config.ARXIV_CONDA_ENV, config.MINERU_CONDA_ENV]:
                        print(f"    ✓ {line.strip()}")
                    else:
                        print(f"      {line.strip()}")

    except Exception as e:
        print(f"✗ 检查conda环境时出错: {e}")


def check_directories():
    """检查目录结构"""
    print("\n=== 目录结构检查 ===")

    directories = [
        config.DATA_DIR,
        config.PROCESSED_DIR,
        config.REPORTS_DIR,
        os.path.join(config.PROCESSED_DIR, "pdfs"),
        os.path.join(config.PROCESSED_DIR, "markdown"),
        os.path.join(config.PROCESSED_DIR, "images")
    ]

    for directory in directories:
        if os.path.exists(directory):
            print(f"✓ {directory}: 存在")
        else:
            print(f"○ {directory}: 不存在（将自动创建）")

    # 检查关键文件
    print("\n关键文件检查:")
    files_to_check = [
        (config.QUESTION_FILE, "问题文件"),
        (config.EXCLUDE_CSV, "排除列表")
    ]

    for file_path, description in files_to_check:
        if os.path.exists(file_path):
            print(f"✓ {description} ({file_path}): 存在")
        else:
            print(f"○ {description} ({file_path}): 不存在")


def check_config_consistency():
    """检查配置一致性"""
    print("\n=== 配置一致性检查 ===")

    issues = []

    # 检查模型是否在可用模型中
    if config.SEARCH_MODEL not in AVAILABLE_MODELS:
        issues.append(f"SEARCH_MODEL '{config.SEARCH_MODEL}' 不在AVAILABLE_MODELS中")

    if config.TEXT_MODEL not in AVAILABLE_MODELS:
        issues.append(f"TEXT_MODEL '{config.TEXT_MODEL}' 不在AVAILABLE_MODELS中")

    if config.IMAGE_MODEL not in AVAILABLE_MODELS:
        issues.append(f"IMAGE_MODEL '{config.IMAGE_MODEL}' 不在AVAILABLE_MODELS中")

    # 检查图像模型是否支持视觉
    if config.IMAGE_MODEL in AVAILABLE_MODELS:
        if not AVAILABLE_MODELS[config.IMAGE_MODEL].get("supports_vision", False):
            issues.append(f"IMAGE_MODEL '{config.IMAGE_MODEL}' 不支持视觉功能")

    if issues:
        print("⚠️  配置问题:")
        for issue in issues:
            print(f"   - {issue}")
    else:
        print("✓ 配置检查通过")


if __name__ == "__main__":
    print("环境配置检查")
    print("=" * 50)
    print(f"配置文件: config.py")
    print(f"数据目录: {config.DATA_DIR}")
    print(f"处理目录: {config.PROCESSED_DIR}")
    print(f"文献目录: {config.REPORTS_DIR}")
    print()

    # 各项检查
    api_results = check_api_keys()
    check_conda_envs()
    check_directories()
    check_config_consistency()

    print("\n=== 总结和建议 ===")

    # API配置建议
    working_models = [name for name, result in api_results.items() if result["connection_success"]]
    if working_models:
        print(f"✓ 可用模型: {', '.join(working_models)}")
    else:
        print("✗ 没有可用的模型，请检查API密钥配置")

    print("\n务必检查:")
    print("1. 确保在config.py中正确设置了API密钥默认值或环境变量")
    print("2. 验证conda环境名称与实际环境匹配")
    print("3. 确保当前使用的模型都在AVAILABLE_MODELS中定义")
    print("4. 为图像处理任务选择支持视觉的模型")
    print("\n运行Acadenuc_Agent下的 'python main.py' 开始使用本系统")
