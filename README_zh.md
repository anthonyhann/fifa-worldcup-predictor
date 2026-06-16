# 🏆 国际足联世界杯（FIFA World Cup）足球预测计算器

<p align="center">
  <strong>一个能自我进化的量化足球预测系统</strong><br>
  <em>Elo 评级 · 泊松分布 · 蒙特卡洛模拟 · 贝叶斯推断</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/版本-3.0-blue" alt="version">
  <img src="https://img.shields.io/badge/python-3.10%2B-green" alt="python">
  <img src="https://img.shields.io/badge/许可证-MIT-yellow" alt="license">
  <img src="https://img.shields.io/badge/状态-活跃-brightgreen" alt="status">
</p>

---

## 📖 概述

**FIFA 世界杯预测计算器**是一个专为世界杯比赛设计的、能自我进化的综合足球预测引擎。它融合了量化建模（Elo 评级、泊松分布、蒙特卡洛模拟）与贝叶斯概率推理及战术语境分析。其独特之处在于**自我进化能力** —— 每场比赛结束后，系统会搜索真实赛果、复盘对比、校准参数，持续提升预测准确率和投注收益。

### 🎯 核心目标

1. **最大化预测准确率** —— 从每一场比赛结果中学习
2. **最大化投注收益** —— 识别价值投注并优化仓位策略

---

## 🧠 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                FIFA 世界杯预测计算器 v3.0                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────────┐ │
│  │ 赛前预测     │   │ 赛后复盘     │   │ 自我进化引擎         │ │
│  │              │   │              │   │                      │ │
│  │ • Elo 评级   │──▶│ • 联网搜索   │──▶│ • 参数自动校准       │ │
│  │ • 泊松 xG    │   │ • 多维评分   │   │ • 准确率追踪         │ │
│  │ • 蒙特卡洛   │   │ • Elo 更新   │   │ • 趋势检测           │ │
│  │ • 贝叶斯推断 │   │ • 统计同步   │   │ • 策略优化           │ │
│  └──────────────┘   └──────────────┘   └──────────────────────┘ │
│                          │                                       │
│                          ▼                                       │
│                 ┌────────────────┐                               │
│                 │ 收益追踪器     │                               │
│                 │ • 虚拟投注     │                               │
│                 │ • ROI 追踪     │                               │
│                 │ • 最大回撤     │                               │
│                 │ • 策略对比     │                               │
│                 └────────────────┘                               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## ✨ 功能特性

### 🔮 预测能力（量化 + 贝叶斯）

| 功能 | 描述 |
|------|------|
| **单场预测** | Elo 评级 + 泊松 xG → 胜/平/负概率 + 最可能比分 |
| **爆冷检测** | 三层判据：风格克制、状态变量、赛制红利 |
| **晋级模拟** | 10 万次蒙特卡洛模拟推演淘汰赛晋级概率 |
| **赔率价值检测** | 模型概率 vs 市场隐含概率，≥3% 偏差标记价值信号 + Kelly 仓位 |
| **贝叶斯 P0→P1** | 先验 → 战术语境修正 → 联赛特性修正 → 似然更新 → 后验概率 |
| **战术分析** | 控球陷阱检测、风格克制分析、赛制特性修正 |
| **剧本预测** | 基于战术机制生成 2-4 套不同比赛剧本 |
| **v2.0 首轮修正** | 大赛首轮自动应用 xG 修正（强队进球 ×0.5、弱队加成、平局 +15%） |

### 🧬 自我进化（v3.0 新增）

| 功能 | 描述 |
|------|------|
| **赛后复盘** | 联网搜索真实赛果 → 对比预测 → 100 分制多维度评分 |
| **Elo 动态更新** | 赛后自动更新 Elo（小组赛 K=32 / 淘汰赛 K=48） |
| **参数自动校准** | 基于复盘数据优化：Elo 权重、平局加成、进球修正、K 因子 |
| **准确率追踪** | 追踪整体/近期方向准确率，趋势检测（上升/稳定/下降） |
| **收益追踪** | 虚拟投注模拟 → ROI 计算 → 策略对比（Kelly 半仓 / 固定比例 / 价值投注） |
| **进化报告** | 参数变更历史、准确率时间线、策略优化建议 |

---

## 📁 文件结构

```
fifa-worldcup-predictor/
├── README.md                          # 英文版 README
├── README_zh.md                       # 中文版 README（当前文件）
├── SKILL.md                           # 完整技能定义与工作流
├── scripts/
│   ├── prediction_engine.py           # 核心引擎（Elo + 泊松 + 蒙特卡洛）
│   ├── odds_fetcher.py                # 实时赔率获取（The Odds API）
│   ├── post_match_review.py           # 赛后复盘引擎（联网搜索 + 评分）
│   ├── evolution_engine.py            # 自我进化引擎（参数校准）
│   └── profit_tracker.py              # 收益追踪器（虚拟投注 + ROI）
├── data/
│   ├── elo_ratings.json               # 48 支世界杯参赛队 Elo 评级
│   ├── team_stats.json                # 球队攻防数据（指数滑动平均更新）
│   └── corrections.json               # 修正因子参数库
├── references/
│   ├── analytical_framework.md        # 贝叶斯分析框架参考
│   └── calibration_methodology.md     # 参数校准方法论
└── logs/
    ├── prediction_log.md              # 赛前预测记录
    ├── review_log.jsonl               # 赛后复盘记录（JSONL 格式）
    ├── profit_track.jsonl             # 投注盈亏记录（JSONL 格式）
    ├── evolution_state.json           # 进化引擎状态与参数历史
    └── profit_state.json              # 收益追踪状态
```

---

## 🚀 快速开始

### 环境要求

- Python 3.10+
- 网络连接（用于获取实时赔率和赛后联网搜索）

### 安装

```bash
# 克隆仓库
git clone https://github.com/anthonyhann/fifa-worldcup-predictor.git
cd fifa-worldcup-predictor

# 无需安装外部依赖 — 纯 Python 标准库！
```

### 预测一场比赛

```python
from scripts.prediction_engine import FootballPredictionEngine

engine = FootballPredictionEngine(data_dir='data')

# 阿根廷 vs 法国（淘汰赛）
prediction = engine.predict('阿根廷', '法国', is_knockout=True)

print(f"胜: {prediction['final']['win_a']}%")
print(f"平: {prediction['final']['draw']}%")
print(f"负: {prediction['final']['win_b']}%")
print(f"xG: {prediction['xg_a']} - {prediction['xg_b']}")
print(f"最可能比分: {prediction['most_likely_scores'][0]}")
```

### 赛后复盘

```python
from scripts.post_match_review import PostMatchReviewer

reviewer = PostMatchReviewer('.')
review = reviewer.review_match('阿根廷', '法国', (2, 1), prediction)

print(f"复盘评分: {review['scores']['total']}/100 ({review['scores']['grade']})")
print(f"Elo 变化: {review['elo_changes']}")
print(f"方向正确: {review['scores']['direction_correct']}")
```

### 触发进化

```python
from scripts.evolution_engine import EvolutionEngine

evo = EvolutionEngine('.')
result = evo.evolve()

print(f"已进化: {result['evolved']}")
print(f"变更参数: {list(result.get('changes', {}).keys())}")
print(f"准确率指标: {evo.compute_accuracy_metrics()}")
```

### 收益追踪

```python
from scripts.profit_tracker import ProfitTracker

tracker = ProfitTracker('.')

# 模拟投注
bet = tracker.simulate_bet(
    '阿根廷', '法国', prediction,
    odds={'home': 2.80, 'draw': 3.20, 'away': 2.50},
    actual_score=(2, 1)
)

print(f"结果: {bet['result']}")
print(f"盈亏: {bet['profit']}")

# 完整报告
report = tracker.get_profit_report()
print(f"ROI: {report['roi']}%")
print(f"最大回撤: {report['max_drawdown']}%")
```

---

## 🔬 工作原理

### 1. 赛前预测

```
用户输入（球队、轮次）
    ↓
Elo 评级对比 → 胜率期望
    +
泊松分布 → 预期进球（xG）
    +
修正因子（首轮、主场优势等）
    ↓
基础概率（P0）
    ↓
贝叶斯战术语境更新
  ├── 控球陷阱检测
  ├── 风格克制分析
  ├── 伤停/首发似然
  └── 赛事特有因素
    ↓
后验概率（P1）+ 剧本预测
    ↓
赔率对比 + Kelly 仓位计算
```

### 2. 赛后复盘

系统联网搜索真实比赛结果，对预测进行 100 分制评分：

| 维度 | 满分 | 评分标准 |
|------|------|----------|
| 方向 | 30 | 方向正确满分；平局或一方正确部分得分 |
| 比分 | 30 | 精确匹配加分；总分相近最高 20 分 |
| xG 准确度 | 20 | 误差 <0.5 球 20 分；<1.0 球 15 分；<2.0 球 10 分 |
| 赔率价值 | 20 | 预测低概率事件正确 20 分 |

每场复盘后自动更新 Elo 评级和球队攻防统计数据。

### 3. 自我进化

累积 ≥3 场复盘数据后，进化引擎自动触发校准：

| 参数 | 触发条件 | 调整逻辑 |
|------|----------|----------|
| `ELO_WEIGHT` | Elo 准确率 vs 整体 | 根据偏差 ±0.05 |
| `OPENER_DRAW_BOOST` | 实际首轮平局率 | 每轮 ±0.03 |
| `FAV_GOAL_DISCOUNT` | 首轮 xG 偏差 | 根据进球偏差调整 |
| `K_FACTOR` | 整体准确率趋势 | 准确率下降则 ↑；稳定则 ↓ |

单次调整幅度上限为 ±20%，所有变更记录在 `evolution_state.json` 中。

### 4. 收益追踪

同时追踪四种策略：

| 策略 | 描述 |
|------|------|
| **半仓 Kelly** | Kelly 准则 × 0.5（保守型） |
| **全仓 Kelly** | 完整 Kelly 准则（激进型） |
| **固定比例** | 每次投注资金的 5% |
| **仅价值投注** | 仅在模型优势 ≥ 3% 时投注 |

---

## 📊 数据来源

- **Elo 评级**：预加载 48 支世界杯球队数据，赛后动态更新
- **球队统计**：场均进球/失球（指数滑动平均，α=0.3）
- **实时赔率**：通过 The Odds API（`scripts/odds_fetcher.py`）
- **比赛结果**：赛后联网搜索
- **修正因子**：基于世界杯历史数据经验校准

---

## 🛡️ 安全红线

- ⚠️ **绝不直接建议投注** —— 仅提供分析框架
- 📊 **绝不伪造数据** —— 所有计算通过代码执行
- 🔍 **从不隐藏偏差** —— 模型与市场大幅偏差时标注不确定性
- ⚠️ **始终附风险提示** —— 每次分析结尾必附
- 🎲 **不预测点球大战** —— 仅建模 90/120 分钟结果
- 🏷️ **标注数据来源** —— 联网搜索数据标注 URL 与时间戳
- 🚫 **缺失数据 = UNAVAILABLE** —— 绝不猜测或插值

---

## 📝 许可证

MIT License — 详见 [LICENSE](LICENSE) 文件。

---

## 🤝 贡献指南

欢迎贡献！感兴趣的领域：

- 扩展更多联赛/赛事支持
- 更精细的战术模型
- 替代仓位策略
- 实时数据 API 集成

---

<p align="center">
  <sub>为足球分析爱好者倾心打造 ❤️</sub>
</p>
