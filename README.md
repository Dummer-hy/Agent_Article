# 文献智能体 (Academic Agent)

一个用于搜索、下载、处理和分析学术文献的自动化工具。

## 📌 主要功能

1. **文献搜索与下载**
   - 从 arXiv 获取最新论文
   - 支持关键词搜索和筛选
   - 交互式选择下载论文

2. **文献处理**
   - 自动转换 PDF 为结构化 Markdown
   - 提取论文核心内容
   - 批量处理已下载文献

3. **智能分析**
   - 基于 AI 模型分析文本内容
   - 自动解析论文图表
   - 生成分析报告

4. **管理功能**
   - 查看论文目录结构
   - 重新分析已有文献
   - 管理排除列表

## 🛠️ 安装与配置

### 系统要求
- Python 3.10
- Conda/Miniconda (推荐)

### 安装步骤（待后续更新）
创建虚拟环境根据文件头引用安装所需包，本项目使用了MinerU来转换提取pdf内容，其次arvix_mcp也可选（目前使用arvix官方接口，无需安装mcp），MinerU：https://github.com/opendatalab/mineru?tab=readme-ov-file#known-issues，Arvix_MCP:https://github.com/blazickjp/arxiv-mcp-server

###License Information
some models in MinerU are trained based on YOLO. YOLO follows the AGPL license.
