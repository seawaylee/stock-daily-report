# 📈 AI Stock Analysis & Report Generator

> A股智能选股、研报生成与可视化工具

## 📁 项目结构

```
stock-daily-report/
├── common/                 # 公共模块
│   ├── config.py           # 配置参数
│   ├── data_fetcher.py     # 数据拉取
│   ├── prompts.py          # AI Prompt 模板
│   └── signals.py          # 信号检测逻辑
├── modules/
│   ├── fish_basin/         # 鱼盆趋势模型
│   │   ├── fish_basin.py         # 指数分析
│   │   └── fish_basin_sectors.py # 题材板块分析
│   └── daily_report/       # 日报生成
│       ├── run_ai_analysis.py    # 主程序入口
│       ├── sector_flow.py        # 板块资金流
│       ├── limit_up_ladder.py    # 涨停阶梯
│       └── generate_ladder_prompt.py
├── config/                 # 配置文件
│   └── fish_basin_sectors.json   # 板块列表配置
├── scripts/                # 启动脚本
│   ├── run.sh              # 通用脚本运行器
│   ├── run_all.sh          # 鱼盆全量运行
│   └── run_fish_basin.sh   # 单独运行鱼盆
└── results/                # 输出目录 (按日期)
    └── YYYYMMDD/
        ├── fish_basin_report.xlsx
        ├── fish_basin_sectors.xlsx
        ├── stock_list_*.csv
        └── ...
```

## 🚀 快速开始

### 环境要求
- Python 3.11 (Conda: `py311`)
- 依赖: `pip install -r requirements.txt`

### 运行鱼盆模型
```bash
bash scripts/run_all.sh
```

### 运行日报分析
```bash
bash scripts/run.sh modules/daily_report/run_ai_analysis.py
```

## 📊 输出说明

所有结果保存在 `results/{YYYYMMDD}/` 目录：

| 文件 | 说明 |
|------|------|
| `fish_basin_report.xlsx` | 指数鱼盆分析（颜色标注） |
| `fish_basin_sectors.xlsx` | 板块题材鱼盆分析 |
| `stock_list_*.csv` | 当日股票列表缓存 |
| `xiaohongshu_*.txt` | 小红书文案 |
| `image_prompt_*.txt` | AI海报提示词 |
| `sector_flow_image_prompt.txt` | 资金流提示词 |

## ⚙️ 配置

### 板块列表
编辑 `config/fish_basin_sectors.json` 以自定义监控的板块：
```json
[
  {"name": "半导体", "type": "THS", "code": "881121"},
  {"name": "人工智能", "type": "THS_CONCEPT", "code": "302035"}
]
```

### 环境变量
复制 `.env.example` 为 `.env` 并填写 API Key：
```
GOOGLE_API_KEY=your_key_here
```

## 📝 License
MIT
