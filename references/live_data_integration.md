# 实时数据接入方案 — 伤停 / 首发 / 赔率

> 调研时间：2026-06-16 | 目标：为 FIFA 世界杯预测计算器接入实时伤停报告、首发阵容、赔率推送

---

## 一、数据源选型

### 方案A：BSD Free Football API（主推荐，首选项）

| 维度 | 评估 |
|------|------|
| 地址 | https://sports.bzzoiro.com/ |
| 世界杯2026 | ✅ 已确认覆盖（首页展示完整赛程和12个小组） |
| 首发阵容 | ✅ 赛前1小时自动抓取，含阵型、首发11人、替补 |
| 伤停信息 | ✅ `unavailable_players` 字段（受伤/停赛/存疑，按主客队分组） |
| 实时赔率 | ✅ 17+ 家博彩公司，支持 1X2、大小球、让球等多种盘口 |
| 实时比分 | ✅ 30秒刷新缓存 + WebSocket 推送 |
| 价格 | **完全免费**，零调用限制，无需信用卡 |
| 数据格式 | REST JSON + OpenAPI 文档 + WebSocket |
| 额外能力 | xG 射门图、球员档案（6万+人）、教练战术档案、ML 预测 |

**端点清单（与本次需求相关）：**

| 端点 | 用途 | 返回数据 |
|------|------|----------|
| `GET /api/events/` | 获取所有世界杯比赛 | 比分、阵容、`unavailable_players`、赔率、事件 |
| `GET /api/events/?league=27` | 按世界杯筛选 | league=27 是 World Cup 2026 |
| `GET /api/odds/compare/` | 多平台赔率对比 | 17+ 博彩公司实时赔率 |
| `GET /api/odds/best/` | 最佳赔率聚合 | 各盘口最优赔率 |
| `WebSocket /ws/` | 实时数据推送 | 比分变动、赔率变动、阵容公布等事件推送 |

**示意响应（`/api/events/` 关键字段）：**

```json
{
  "home_team": "Argentina",
  "away_team": "France",
  "home_score": null,
  "away_score": null,
  "time_elapsed": "notstarted",
  "lineup": {
    "home": {
      "formation": "4-3-3",
      "startXI": [{"name": "Messi", "number": 10, "position": "F"}, ...],
      "substitutes": [{"name": "Dybala", "number": 21, "position": "F"}, ...]
    },
    "away": {
      "formation": "4-2-3-1",
      "startXI": [...],
      "substitutes": [...]
    }
  },
  "unavailable_players": {
    "home": [
      {"name": "Di Maria", "reason": "Injury", "status": "Out"},
      {"name": "Acuna", "reason": "Yellow cards", "status": "Suspended"}
    ],
    "away": [
      {"name": "Kante", "reason": "Muscle injury", "status": "Doubtful"}
    ]
  },
  "odds_home": 2.45,
  "odds_draw": 3.10,
  "odds_away": 3.20
}
```

### 方案B：API-Football（备选）

| 维度 | 评估 |
|------|------|
| 地址 | https://www.api-football.com/ |
| 首发阵容 | ✅ 支持 |
| 伤停信息 | ❌ 不支持 |
| 赔率 | ❌ 免费层无赔率 |
| 免费限制 | 100 次/天 |
| 世界杯 | 需付费层（€19/月起）|

仅在 BSD 不可用时作为阵容数据的备选方案。

### 方案C：The Odds API（已在用）

| 维度 | 评估 |
|------|------|
| 当前状态 | `scripts/odds_fetcher.py` 已集成 |
| 免费限制 | 500 次/月 |
| 阵容/伤停 | ❌ 不支持 |

保留作为赔率对比的第二数据源，与 BSD 交叉验证。

---

## 二、落地架构

```
                              ┌─────────────────────┐
                              │   BSD Free API       │
                              │   (Primary)          │
                              │                     │
                              │ • Lineups           │
                              │ • Injuries          │
                              │ • Live Odds         │
                              │ • Live Scores       │
                              │ • WebSocket Push    │
                              └──────┬──────────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    │                │                │
                    ▼                ▼                ▼
           ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
           │ lineup       │ │ injury       │ │ live_odds    │
           │ _fetcher.py  │ │ _fetcher.py  │ │ _fetcher.py  │
           └──────┬───────┘ └──────┬───────┘ └──────┬───────┘
                  │                │                │
                  └────────────────┼────────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────┐
                    │  live_data_fetcher.py    │
                    │  (统一数据获取与整合层)    │
                    └──────────┬───────────────┘
                               │
            ┌──────────────────┼──────────────────┐
            │                  │                  │
            ▼                  ▼                  ▼
   ┌────────────────┐ ┌──────────────┐ ┌─────────────────┐
   │ prediction_    │ │ post_match_  │ │ profit_         │
   │ engine.py      │ │ review.py    │ │ tracker.py      │
   │                │ │              │ │                 │
   │ 阵容影响xG     │ │ 伤病验证     │ │ 赔率变化追踪    │
   │ 伤停调整Elo    │ │ 阵容比对     │ │                 │
   │ 实时赔率对比    │ │              │ │                 │
   └────────────────┘ └──────────────┘ └─────────────────┘
```

---

## 三、实施步骤

### Step 1: 注册 BSD API Key

```bash
# 注册地址：https://sports.bzzoiro.com/
# 获取 API Key 后配置环境变量
export BSD_API_KEY="your_key_here"
```

### Step 2: 新建 `scripts/live_data_fetcher.py`

核心类设计：

```python
class LiveDataFetcher:
    """统一实时数据获取层"""
    
    def __init__(self, api_key=None):
        self.base_url = "https://sports.bzzoiro.com/api"
        self.ws_url = "wss://sports.bzzoiro.com/ws"
        
    def get_lineups(self, match_id=None, home_team=None, away_team=None) -> Dict:
        """获取首发阵容：阵型 + 首发11人 + 替补"""
        
    def get_injuries(self, match_id=None, home_team=None, away_team=None) -> Dict:
        """获取伤停信息：受伤/停赛/存疑球员"""
        
    def get_live_odds(self, match_id=None) -> Dict:
        """获取实时赔率：17+家博彩公司对比"""
        
    def get_match_events(self, league_id=27) -> List[Dict]:
        """批量获取世界杯所有比赛的完整数据"""
        
    def subscribe_websocket(self, callback) -> None:
        """订阅 WebSocket 实时推送"""
```

### Step 3: 整合到预测引擎

在 `prediction_engine.py` 中新增方法：

```python
def predict_with_live_data(self, team_a, team_b, live_data=None):
    """结合实时数据增强预测"""
    if live_data:
        # 伤病调整：缺阵核心球员 → 降低球队实力系数
        elo_a, elo_b = self._adjust_for_injuries(
            team_a, team_b, 
            live_data.get('injuries', {})
        )
        
        # 阵容调整：根据首发阵容修正 xG
        xg_a, xg_b = self._adjust_for_lineups(
            team_a, team_b,
            live_data.get('lineups', {})
        )
    
    # 继续标准预测流程...
```

### Step 4: 整合到复盘引擎

在 `post_match_review.py` 中新增：

```python
def review_with_live_context(self, team_a, team_b, actual_score, prediction, live_data):
    """对比预测时使用的伤停/阵容信息与实际赛果"""
    # 验证伤病影响是否被正确估算
    # 检查阵容预测的准确度
```

### Step 5: 新增实时赔率推送

在 `odds_fetcher.py` 中补充 BSD 数据源，或新建 `scripts/odds_pusher.py`：

```python
class OddsPusher:
    """实时赔率推送与价值监控"""
    
    def __init__(self):
        self.bsd = LiveDataFetcher()      # 主数据源
        self.the_odds = OddsFetcher()     # 备用/验证源
    
    def monitor_value_changes(self, match_id):
        """监控赔率波动，检测价值信号变化"""
        # 当任一博彩公司赔率偏离 ≥3% 时触发提醒
```

---

## 四、数据流关键路径

### 赛前 3 小时

```
BSD API → 拉取最新阵容预测 / 伤停名单
         → 写入 data/live_cache.json
         → 预测引擎调用 predict_with_live_data()
         → 输出增强预测（含伤病/阵容修正因子）
```

### 赛前 1 小时

```
BSD API → 官方首发公布（自动刷新）
         → WebSocket 推送阵容更新事件
         → 可选：对比阵容预测 vs 实际首发，评估预测准确度
```

### 赛中

```
BSD WebSocket → 实时比分推送
              → 实时赔率变动推送
              → 赔率监控模块：赔率大幅变动触发告警
```

### 赛后

```
BSD API → 最终比分 + 球员数据
        → 复盘引擎自动比对
        → Elo 更新 + 进化触发
```

---

## 五、降级与容错

| 场景 | 策略 |
|------|------|
| BSD API 不可用 | 降级到 The Odds API（赔率）+ API-Football（阵容），伤病数据标记 UNAVAILABLE |
| WebSocket 断连 | 自动回退到 60 秒轮询 REST |
| 赛前 1 小时仍无阵容 | 使用历史常用阵容作为近似，标注 UNCERTAIN |
| API Key 过期 | 提前 7 天检查 + 日志告警 |

---

## 六、新增文件清单

| 文件 | 功能 | 依赖 |
|------|------|------|
| `scripts/live_data_fetcher.py` | 统一数据获取层，封装 BSD API 调用 | `requests` |
| `scripts/bsd_client.py` | BSD API 原始客户端（认证、请求、错误处理） | `requests` |
| `data/live_cache.json` | 实时数据本地缓存（阵容/伤停/赔率快照） | — |
| `references/live_data_integration.md` | 实时数据集成参考文档 | — |

**修改文件：**

| 文件 | 修改内容 |
|------|----------|
| `scripts/prediction_engine.py` | 新增 `predict_with_live_data()`、伤病调整方法、阵容权重方法 |
| `scripts/post_match_review.py` | 新增阵容/伤停维度的复盘评分 |
| `scripts/odds_fetcher.py` | 双数据源支持（BSD + The Odds API） |
| `SKILL.md` | 更新工作流，增加实时数据获取步骤 |

---

## 七、时间评估

| 步骤 | 预计工时 |
|------|----------|
| 注册 BSD API + 测试连通性 | 30 分钟 |
| 编写 `live_data_fetcher.py` | 1-2 小时 |
| 整合到预测引擎 | 1-2 小时 |
| WebSocket 实时推送 | 1 小时 |
| 降级与容错 | 1 小时 |
| 测试 + 文档 | 1 小时 |
| **合计** | **约 5-8 小时** |
