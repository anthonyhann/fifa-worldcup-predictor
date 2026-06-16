# FIFA 世界杯预测计算器

<p align="center">
  <strong>预测世界杯比赛，复盘真实结果，越用越准。</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/版本-3.0-blue" alt="version">
  <img src="https://img.shields.io/badge/python-3.10%2B-green" alt="python">
  <img src="https://img.shields.io/badge/许可证-MIT-yellow" alt="license">
</p>

> English version: [README.md](README.md)

---

## 这是什么？

一个帮你分析世界杯比赛的工具。输入两支球队，它会告诉你谁更可能赢、大概什么比分、赔率有没有被低估。

跟一般预测工具不同的是：比赛打完以后，它会自动搜索真实结果，跟自己的预测做比对。如果发现自己哪里判断偏了，就调整参数。看的比赛越多，预测越靠谱。

就像一个永远在复盘录像的分析师。

---

## 能做什么

### 赛前

- **预测胜平负概率**，给出最可能出现的比分
- **提前发现爆冷迹象** —— 当弱队因为风格克制或赛制红利真有取胜机会时，系统会标记出来
- **模拟晋级路线**，看每支球队进八强、四强、决赛的概率
- **找出被错误定价的赔率** —— 当模型判断和博彩市场明显不一致时提醒你
- **生成比赛剧本**，不只给数字，也描绘比赛可能怎么演变

### 赛后

- **自动复盘**，联网搜索真实比分跟预测做对比
- **给自己打分**（100 分制），从胜负方向、比分精度、进球预测、价值判断四个维度
- **更新球队实力评级**，反映真实比赛表现

### 自我进化

- **积累足够场次后自动校准** —— 根据历史预测偏差调整内部参数
- **追踪准确率变化趋势**，一眼看出预测质量是在变好还是变差
- **模拟多种投注策略的盈亏**，看哪种方式真实比赛中能赚钱

---

## 快速开始

```bash
git clone https://github.com/anthonyhann/fifa-worldcup-predictor.git
cd fifa-worldcup-predictor
```

不用装任何依赖，纯 Python 标准库就能跑。

### 预测一场比赛

```python
from scripts.prediction_engine import FootballPredictionEngine

engine = FootballPredictionEngine(data_dir='data')

# 阿根廷 vs 法国，淘汰赛
prediction = engine.predict('阿根廷', '法国', is_knockout=True)

print(f"阿根廷胜: {prediction['final']['win_a']}%")
print(f"平局:     {prediction['final']['draw']}%")
print(f"法国胜:   {prediction['final']['win_b']}%")
print(f"最可能比分: {prediction['most_likely_scores'][0]}")
```

### 赛后复盘

```python
from scripts.post_match_review import PostMatchReviewer

reviewer = PostMatchReviewer('.')
review = reviewer.review_match('阿根廷', '法国', (2, 1), prediction)

print(f"复盘评分: {review['scores']['total']}/100 — {review['scores']['grade']}")
print(f"方向正确: {review['scores']['direction_correct']}")
```

### 查看进化效果

```python
from scripts.evolution_engine import EvolutionEngine

evo = EvolutionEngine('.')
evo.evolve()          # 数据够了就自动校准
print(evo.compute_accuracy_metrics())
```

### 模拟投资收益

```python
from scripts.profit_tracker import ProfitTracker

tracker = ProfitTracker('.')
bet = tracker.simulate_bet(
    '阿根廷', '法国', prediction,
    odds={'home': 2.80, 'draw': 3.20, 'away': 2.50},
    actual_score=(2, 1)
)
print(f"结果: {bet['result']}, 盈亏: {bet['profit']}")

report = tracker.get_profit_report()
print(f"ROI: {report['roi']}%, 最大回撤: {report['max_drawdown']}%")
```

---

## 学习闭环

系统的运作方式很简单：

1. **预测** —— Elo 评级打底，泊松分布估算预期进球，再用战术语境和赛制因素修正
2. **复盘** —— 赛后联网搜索真实比分，跟预测逐项对比
3. **学习** —— 每攒够 3 场以上的复盘数据，触发一次参数校准，调整各个因子的权重
4. **进步** —— 重复这个循环，预测越来越准

同时追踪四种投注策略（半仓 Kelly、全仓 Kelly、固定比例、仅价值投注），方便你对比不同风险偏好下的收益表现。

---

## 文件结构

```
fifa-worldcup-predictor/
├── README.md                    # 英文版
├── README_zh.md                 # 中文版（当前文件）
├── scripts/
│   ├── prediction_engine.py     # 赛前预测
│   ├── post_match_review.py     # 赛后复盘 + 联网搜索
│   ├── evolution_engine.py      # 自动校准
│   ├── profit_tracker.py        # 投注模拟
│   └── odds_fetcher.py          # 实时赔率（The Odds API）
├── data/
│   ├── elo_ratings.json         # 48 支球队 Elo 评级
│   ├── team_stats.json          # 攻防数据
│   └── corrections.json         # 经验校准的修正因子
└── logs/                        # 预测与复盘记录
```

---

## 底线

一些这个工具明确不会做的事情：

- 不会直接告诉你该买哪边。它给出概率和偏差，决策你自己做
- 不预测点球大战结果 —— 只建模常规时间和加时赛
- 模型和市场大幅偏差时，会标注不确定性而不是假装一切精准
- 数据缺失就说缺失，不猜不凑
- 所有联网搜索结果标注来源和时间

---

## 计划路线

接下来想做的事情：

- [ ] 支持更多赛事和联赛（欧洲杯、美洲杯、各国联赛）
- [ ] 更细致的战术分析 —— 球员级别追踪、阵型分析、定位球概率
- [ ] 更多仓位策略 —— 分级 Kelly 变体、置信度加权缩放
- [ ] 实时数据接入 —— 伤停报告、首发公布、实时赔率推送
- [ ] 可视化面板 —— 把预测、复盘、准确率趋势用图表展示出来

欢迎认领一项，开个 PR。

---

## 许可证

MIT — 详见 [LICENSE](LICENSE)。
