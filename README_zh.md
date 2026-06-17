# :trophy: FIFA 世界杯预测计算器

<p align="center">
  <strong>预测世界杯比赛，复盘真实结果，越用越准。</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/版本-3.2-blue" alt="version">
  <img src="https://img.shields.io/badge/python-3.10%2B-green" alt="python">
  <img src="https://img.shields.io/badge/许可证-MIT-yellow" alt="license">
  <img src="https://img.shields.io/badge/数据-实时阵容%20%2B%20伤停%20%2B%20赔率-red" alt="live data">
</p>

> :us: English version: [README.md](README.md)

---

## :mag: 这是什么？

一个帮你分析世界杯比赛的工具。输入两支球队，它会告诉你谁更可能赢、大概什么比分、赔率有没有被低估。

跟一般预测工具不同的是：比赛打完以后，它会自动搜索真实结果，跟自己的预测做比对。如果发现自己哪里判断偏了，就调整参数。看的比赛越多，预测越靠谱。

就像一个永远在复盘录像的分析师。

---

## :dart: 能做什么

### :crystal_ball: 赛前预测

- **预测胜平负概率**，给出最可能出现的比分
- **轮次自适应预测** — R1保守(×0.5) → R2反弹(×1.10) → R3常态 → 淘汰赛防守 (v3.2)
- **三层爆冷检测** — 风格克制 + 状态变量 + 赛制红利，Tier 1/2/3 分级预警
- **模拟晋级路线**，看每支球队进八强、四强、决赛的概率
- **找出被错误定价的赔率** —— 当模型判断和博彩市场明显不一致时提醒你

### :satellite: 实时数据（v3.1 新增）

- **首发阵容** —— 赛前约 1 小时自动获取，含阵型分析
- **伤停报告** —— 谁受伤、谁停赛、谁存疑，以及这对胜负意味着什么
- **实时赔率** —— 多家博彩公司对比，每 60 秒刷新
- **增强预测** —— 伤停调整球队实力评级，阵型修正预期进球

> 基于 [BSD Free Football API](https://sports.bzzoiro.com/)。设置 `BSD_API_KEY` 环境变量即可使用 —— 完全免费，无调用次数限制。

### :bar_chart: 赛后复盘

- **自动复盘**，联网搜索真实比分跟预测做对比
- **给自己打分**（100 分制），从胜负方向、比分精度、进球预测、价值判断四个维度
- **更新球队实力评级**，反映真实比赛表现

### :dna: 自我进化

- **积累足够场次后自动校准** —— 根据历史预测偏差调整内部参数
- **追踪准确率变化趋势**，一眼看出预测质量是在变好还是变差
- **模拟多种投注策略的盈亏**，看哪种方式真实比赛能赚钱

---

## :rocket: 快速开始

```bash
git clone https://github.com/anthonyhann/fifa-worldcup-predictor.git
cd fifa-worldcup-predictor
```

不用装任何依赖，纯 Python 标准库就能跑。

### 用实时数据增强预测

```python
from scripts.live_data_fetcher import LiveDataFetcher
from scripts.prediction_engine import FootballPredictionEngine

# 一次拉取阵容、伤停、赔率
fetcher = LiveDataFetcher()
live = fetcher.get_full_match_data('阿根廷', '法国')

engine = FootballPredictionEngine(data_dir='data')
prediction = engine.predict_with_live_data('阿根廷', '法国', live, is_knockout=True)

print(f"阿根廷胜: {prediction['final']['win_a']}%")
print(f"平局:     {prediction['final']['draw']}%")
print(f"法国胜:   {prediction['final']['win_b']}%")
print(f"伤停: {prediction['live_data']['injuries']['summary']}")
```

### 不用实时数据也行

```python
prediction = engine.predict('阿根廷', '法国', is_knockout=True)
# 什么都没变，不配 API Key 也能跑
```

### 复盘和学习

```python
from scripts.post_match_review import PostMatchReviewer

reviewer = PostMatchReviewer('.')
review = reviewer.review_match('阿根廷', '法国', (2, 1), prediction)
print(f"复盘评分: {review['scores']['total']}/100 — {review['scores']['grade']}")

# 攒够 3 场，进化引擎自动校准
from scripts.evolution_engine import EvolutionEngine
EvolutionEngine('.').evolve()
```

---

## :repeat: 学习闭环

1. **预测** —— Elo 评级打底 + 泊松分布算进球 + 战术语境修正 + 实时数据（伤停/阵容）
2. **复盘** —— 赛后联网搜索真实比分，逐项对比
3. **学习** —— 每攒够 3 场以上复盘数据，触发参数校准
4. **进步** —— 重复循环，预测越来越准

同时追踪四种投注策略：半仓 Kelly、全仓 Kelly、固定比例、仅价值投注。

---

## :file_folder: 文件结构

```
fifa-worldcup-predictor/
├── README.md                  # 英文版
├── README_zh.md               # 中文版（当前文件）
├── scripts/
│   ├── prediction_engine.py   # 赛前预测 + 实时数据集成
│   ├── live_data_fetcher.py   # 阵容、伤停、赔率（BSD API）
│   ├── bsd_client.py          # BSD API 客户端
│   ├── odds_fetcher.py        # 双源赔率（BSD + The Odds API）
│   ├── post_match_review.py   # 赛后复盘 + 联网搜索
│   ├── evolution_engine.py    # 自动校准
│   └── profit_tracker.py      # 投注模拟
├── data/                      # Elo 评级、球队统计、修正因子
├── references/                # 分析框架、校准方法论、集成方案
└── logs/                      # 预测与复盘记录
```

---

## :shield: 底线

- 不会直接告诉你该买哪边 —— 给概率和偏差，决策你自己做
- 只建模常规时间和加时赛 —— 不预测点球大战
- 模型和市场大幅偏差时标注不确定性 —— 不假装精准
- 数据缺失就说缺失 —— 不猜不凑
- 所有联网搜索结果标注来源和时间

---

## :construction: 计划路线

- [x] ~~实时数据接入 —— 伤停报告、首发公布、实时赔率~~ :tada:
- [x] ~~轮次自适应修正 —— R1→R2→R3→淘汰赛动态系数~~ :tada:
- [x] ~~爆冷分析升级 —— 三层判据 + Tier 1/2/3 分级~~ :tada:
- [ ] 支持更多赛事（欧洲杯、美洲杯、各国联赛）
- [ ] 更细致的战术模型 —— 球员级别追踪、定位球概率
- [ ] 更多仓位策略 —— 分级 Kelly、置信度加权
- [ ] 可视化面板 —— 图表展示预测、复盘、准确率趋势

---

## :page_facing_up: 许可证

MIT — 详见 [LICENSE](LICENSE)。
