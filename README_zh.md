<div align="center">

# 🏆 FIFA 世界杯预测引擎

### 一个每场赛后都会给自己打分的世界杯预测引擎

Elo 评级 + 泊松 xG + 10 万次蒙特卡洛模拟 + 贝叶斯战术语境——赛后自动复盘、轮次自适应自校准。**零依赖：纯 Python 标准库。**

[![version](https://img.shields.io/badge/version-v4.17-blue?style=flat-square)](SKILL.md)
[![python](https://img.shields.io/badge/python-3.10%2B-green?style=flat-square)](#-快速开始)
[![dependencies](https://img.shields.io/badge/dependencies-0-brightgreen?style=flat-square)](#-快速开始)
[![license](https://img.shields.io/badge/license-MIT-yellow?style=flat-square)](LICENSE)
[![stars](https://img.shields.io/github/stars/anthonyhann/fifa-worldcup-predictor?style=flat-square)](https://github.com/anthonyhann/fifa-worldcup-predictor/stargazers)

[快速开始](#-快速开始) · [学习闭环](#-学习闭环) · [真实数字](#-真实数字仓库可验证) · [目录结构](#-目录结构) · [诚实边界](#-诚实边界什么时候别用它) · [English](README.md)

</div>

## 大多数预测工具，大概是这样

- 告诉你谁会赢——然后**再也不回头看**实际发生了什么
- 首轮和决赛用同一套系数，仿佛淘汰赛 dynamics 不存在
- 让你"相信模型"，却没有一本**可审计的准确率台账**

这个引擎反着来：每场比赛结束后，它抓取真实比分，按 100 分制给自己的预测打分，更新球队评级，并按轮次重新校准系数——过拟合防御会拒绝它无法自圆其说的剧烈跳变。每次迭代都有日志，你能看着它变准（或者抓到他变飘）。

## 能做什么

| 阶段 | 能力 |
|---|---|
| 🔮 **赛前** | 胜平负概率 + 最可能比分（Elo + 泊松 + 10 万次蒙特卡洛）；轮次自适应系数（R1 保守 ×0.5 → R2 反弹 ×1.10 → R3 常态 → 淘汰赛防守）；三层爆冷检测；晋级路径模拟；错误赔率标记 + Kelly 仓位 |
| 🛰️ **实时数据** | 开赛前约 1 小时自动获取首发阵容与阵型、伤停报告、多博彩公司赔率——伤停修正实力评级，阵型修正预期进球（BSD API，免费 key） |
| 📺 **实时比分** | 接入 worldcup2026 REST API（覆盖全部 104 场比赛，免认证），真实比分自动喂入复盘引擎 |
| 📊 **赛后** | 自动对照真实结果复盘每场预测；按方向/比分/进球/价值四维度 100 分制评分；按真实赛果更新 Elo 评级 |
| 🧬 **自我进化** | 攒够 3 场复盘自动触发轮次自适应校准；新参数先回测再应用；三重过拟合防御（相邻轮次反向 >0.45 / 单次变化 >0.20 / 样本 <3 场低置信） |
| 💰 **收益追踪** | 并行模拟 4 种投注策略：半仓 Kelly / 全仓 Kelly / 固定 2% / 仅价值投注，输出 ROI 与最大回撤 |

## 🚀 快速开始

```bash
# 1. 克隆（无需 pip install——纯标准库）
git clone https://github.com/anthonyhann/fifa-worldcup-predictor.git
cd fifa-worldcup-predictor

# 2. 看一眼当前的准确率台账
python3 scripts/evolution_engine.py --report

# 3. 预测一场比赛
python3 -c "
from scripts.prediction_engine import FootballPredictionEngine
engine = FootballPredictionEngine(data_dir='data')
p = engine.predict('阿根廷', '法国', is_knockout=True)
print(p['final'])  # 胜/平/负概率 + 最可能比分
"
```

**给 AI Agent 用**——本仓库自带 [SKILL.md](SKILL.md)。把这句话粘贴给你的 Agent：

> 阅读 https://github.com/anthonyhann/fifa-worldcup-predictor 里的 SKILL.md，用它预测 <球队A> vs <球队B>。

可选：设置 `BSD_API_KEY` 环境变量可接入阵容/伤停/实时赔率增强。不设也能正常跑上面的全部流程。

## 🔁 学习闭环

1. **预测** —— Elo + 泊松 xG + 战术语境 + 实时数据
2. **复盘** —— 抓取真实比分，给预测打分，写进日志
3. **学习** —— 每攒够 3 场复盘触发轮次自适应校准，回测通过才应用
4. **进步** —— 系数一场一场地向真实世界收敛

整个闭环是公开记账的：[SKILL.md](SKILL.md) 记录了 **23 个版本迭代（v1.1 → v4.17）**，每一版都写明了踩坑教训。最有代表性的是 **v4.7**——引擎抓到了*自己的指标虚高 bug*（自评准确率 98.6% → 修复后真实 36.7%），并据此重置了参数。能自我审计的预测器，才是重点。

## 📊 真实数字（仓库可验证）

- **13 个 Python 脚本**，约 5,750 行，**0 三方依赖**（只用 json / math / urllib）
- **48 支国家队**的 Elo 评级 + 攻防数据；**54 个修正因子**（`data/`）
- 每条晋级路径 **100,000 次**蒙特卡洛模拟（`prediction_engine.py`）
- **4** 种投注策略并行追踪（`profit_tracker.py`）
- **365** 条赛后复盘记录（`logs/review_log.jsonl`），持续增长
- [SKILL.md](SKILL.md) 记录的自评准确率：胜平负方向 **~78%**、整体 ~38%、近 20 场 55%——自报数据，可审计，也诚实标注短板（让球方向 1/9，已标记极低置信）
- 接入 **2** 个免费数据 API：BSD Football API（阵容/伤停/赔率）+ worldcup2026（104 场实时比分）

## 📂 目录结构

```
fifa-worldcup-predictor/
├── SKILL.md                  # 完整能力规格 + 23 版进化日志
├── scripts/
│   ├── prediction_engine.py  # 核心引擎：Elo + 泊松 + 蒙特卡洛 + 市场共识（41 个方法）
│   ├── live_data_fetcher.py  # 阵容 / 伤停 / 赔率 / 实时比分
│   ├── evolution_engine.py   # 自动校准 + 回测 + 过拟合防御
│   ├── post_match_review.py  # 100 分制复盘评分 + 结果抓取
│   ├── profit_tracker.py     # 4 策略投注模拟
│   ├── odds_fetcher.py       # 双源赔率对比
│   ├── wc2026_client.py      # worldcup2026 REST API 客户端
│   └── …                     # + 诊断、回测、批量运行脚本（共 13 个）
├── data/                     # elo_ratings / team_stats / corrections / h2h（48 支球队）
├── references/               # 分析框架、校准方法论、实时数据集成方案
├── outputs/                  # 预测报告样例（R32 各批次）
└── logs/                     # prediction_log.md、review_log.jsonl（365 条）、profit_track.jsonl
```

## ⚠️ 诚实边界——什么时候别用它

- **这不是投注建议。** 它只输出概率与市场偏差；每个决策（及其后果）都是你自己的。
- **不预测点球大战。** 只建模常规时间与加时赛。
- **范围仅限 48 队 2026 世界杯。** 欧洲杯、美洲杯、各国联赛在路线图上，目前不支持。
- **实时功能需要联网。** 离线时仍可用缓存数据预测，但没有阵容/伤停/赔率增强。
- **准确率是自报的。** ~38% 整体 / ~78% 方向来自它自己的复盘日志——请把它当研究工具，真金白银之前先跑自己的回测。


## 🙋 关于作者

在 2026 世界杯期间公开迭代——23 个有记录的版本，每一版都由一场模型预测错的真比赛驱动。赛期内每天自用，准确率台账直接放在仓库里。如果它帮你省掉了凌晨两点手调 Elo 系数的痛苦，⭐ 一下，让下一位分析师知道它真的能用。

## License

MIT — 详见 [LICENSE](LICENSE)。
