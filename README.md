# 📈 A股智能研报系统 (AI Stock Daily Report)

> 结合量化数据分析与AI大模型能力的A股智能研报生成系统。
> 支持鱼盆趋势模型、B1策略选股、资金流分析及涨停天梯，自动生成分析报告与AI绘画提示词。

## 📁 项目结构

```
stock-daily-report/
├── main.py                 # 统一入口程序
├── common/                 # 公共模块
│   ├── config.py           # 配置参数
│   ├── data_fetcher.py     # 数据API (Akshare)
│   ├── prompts.py          # AI Prompt 模板
│   └── signals.py          # 信号检测逻辑
├── modules/
│   ├── fish_basin/         # [Module 1] 鱼盆趋势模型
│   │   ├── fish_basin.py         # 指数分析
│   │   └── fish_basin_sectors.py # 题材板块分析
│   ├── stock_selection/    # [Module 2] B1策略选股
│   │   └── b1_selection.py       # 选股与AI分析逻辑
│   ├── sector_flow/        # [Module 3] 板块资金流
│   └── market_ladder/      # [Module 4] 涨停天梯
├── config/                 # 配置文件
│   └── fish_basin_sectors.json   # 监控板块配置
├── scripts/                # 工具脚本
│   └── run.sh              # 标准启动脚本 (封装Python环境)
└── results/                # 产物输出 (按日期归档)
    └── YYYYMMDD/
        ├── 趋势模型_指数.xlsx
        ├── 趋势模型_题材.xlsx
        ├── selected_top10.json
        ├── agent_tasks/        # [中间] 待AI处理的任务
        ├── agent_outputs/      # [中间] AI处理结果
        └── AI提示词/           # [最终] 可用于生图的Prompt
```

## 🚀 快速开始

### 1. 环境准备
确保使用 **Python 3.11** 环境（推荐使用 Conda）：
```bash
conda activate py311
pip install -r requirements.txt
```

### 2. 标准启动方式
建议使用封装好的脚本运行，它会自动指向正确的 Python解释器：

**一键全量运行（推荐）：**
```bash
./scripts/run.sh all
```

**单独运行模块：**
```bash
./scripts/run.sh fish_basin   # 鱼盆趋势
./scripts/run.sh b1           # B1选股 (需配合Agent)
./scripts/run.sh sector_flow  # 资金流向
./scripts/run.sh ladder       # 涨停天梯
```

---

## 🤖 B1选股模块：人机协作工作流

B1 选股模块采用 **"Python初筛 + Agent深度分析"** 的人机协作模式。

### 步骤流程：
1. **运行初筛**：执行 `./scripts/run.sh b1`，程序会筛选出符合条件的股票，生成 `agent_tasks/task_analysis.txt` 后暂停。
2. **AI 分析**：使用 AI Agent (如 Gemini/ChatGPT) 读取 task 文件，将分析结果写入 `agent_outputs/result_analysis.txt`。
3. **最终产出**：再次运行命令，程序检测到分析结果，直接生成最终的 **图片提示词**。

> **💡 效率秘籍**：
> 你可以直接向 Agent 发送以下指令，让 Agent 自动帮你跑完所有流程（无需手动分步执行）：
> 
> **"帮我运行 run all，如果遇到 B1 需要分析，你就帮我分析并写入文件，直到跑完为止。"**
>
> Agent 会代替你执行“运行脚本 -> 读取任务 -> 再次运行”的循环，直到生成最终结果。

---

## 📊 产物清单

所有结果均保存在 `results/{YYYYMMDD}/` 目录下：

### 📈 数据报表
| 文件名 | 内容说明 |
|--------|----------|
| `趋势模型_指数.xlsx` | 宽基指数趋势状态 (YES/NO/WAIT) |
| `趋势模型_题材.xlsx` | 热门板块趋势状态 (含细分题材) |
| `selected_top10.json` | B1策略精选的前10只股票详单 |

### 🎨 AI绘画提示词 (在 `AI提示词/` 目录)
| 文件名 | 用途 |
|--------|------|
| `趋势模型_指数_Prompt.txt` | 生成指数趋势仪表盘 |
| `趋势模型_题材_Prompt.txt` | 生成题材热度气泡图 |
| `资金流向_Prompt.txt` | 生成行业资金流向海报 |
| `涨停天梯_Prompt.txt` | 生成市场涨停梯队图 |
| `趋势B1选股_Prompt.txt` | 生成每日精选股票手绘图 |
| `周刊/下周重要事件_Prompt.txt` | 生成下周市场大事件前瞻海报 |
| `周刊/本周要闻_Prompt.txt` | 生成本周市场回顾海报 |
| `周刊/下周A股日历_Prompt.txt` | 生成下周财经日历海报 |

---

## ⚙️ 配置说明

**修改监控板块**：
编辑 `config/fish_basin_sectors.json`，支持以下类型：
- `THS`: 同花顺行业 (如 "半导体")
- `THS_CONCEPT`: 同花顺概念 (如 "人工智能")
- `INDEX`: 指数 (如 "sh000300") - **系统优先使用东方财富源，自动回退新浪源**

## 📝 License
MIT
