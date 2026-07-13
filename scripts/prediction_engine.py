"""
足球预测引擎 v4.14 — FIFA世界杯预测计算器
模块: Elo评级 + 泊松回归 + 蒙特卡洛模拟 + 赔率分析 + Kelly仓位 + 自我进化 + 实时数据
              + 市场共识融合 + R1→R2攻击动量
v1.1修正: 单场决赛极端防守系数均值回归30%
v2.0修正: 大赛首轮xG修正(2026-06-16复盘，4场全平验证)
v2.1修正: 轮次自适应(2026-06-17复盘，4场3穿盘反向验证)
v3.0新增: Elo动态更新 + 赛后校准 + 进化日志接口
v3.3修正: R1系数进化(2026-06-18复盘)
v3.4新增: 市场共识预测 + R1→R2攻击动量修正(2026-06-23)
v4.4新增: 东道主效应 + 球星加成 + 让球风险标记 + 策略优先级(2026-07-01)
v4.5新增: 球星名单扩充 + KO均势xG爆发修正 + 概率优先策略 + 让球置信降级(2026-07-02)
  - SUPERSTAR_ROSTER新增: Kane(英格兰WC历史射手王)、De Bruyne(比利时核心)
  - KO均势对决(Elo差距<200, xG差<1.3倍)双方xG+30%: R32比利时xG 2.01→实际4球
  - KO赛策略: 概率方向>价值方向(R32 EV方向0/3全部失败)
  - 让球[-1]置信度降级: R32累计1/9(11.1%)→标记为"极低置信"
v4.6新增: 12场总计归纳进化 (2026-07-03)
  - 球星体系效应: SUPERSTAR_XG_BOOST 0.10→0.12(Yamal/Kane未亲自进球但全队输出提升)
  - KO主导胜xG修正: Elo差>150且xG比>1.5时强队xG+8%(西班牙3-0xG 1.63低估)
  - 比分Top6扩展: predict()返回Top6而非Top5(R16瑞士2-0在Top5却被遗漏)
  - 12场累计数据: FT方向83%·总进球Top2 92%·让球[-1]胜11.1%
v4.7新增: R32d针对性进化 (2026-07-04)
  - KO主导胜修正设上限: 0.08→0.05, 最大总增幅限制+15%(阿根廷73.7%→1-1修正过度)
  - 高Elo差爆冷缓冲: Elo>400时强队xG-8%、弱队xG+6%(阿根廷560 Elo差被佛得角守平)
  - 首次淘汰赛黑马加成: 首次进世界杯KO赛球队xG+8%(佛得角首秀超常发挥验证)
  - 15场累计数据更新: FT方向80%·总进球Top2 87%·HT/FT 53%
v4.10新增: 自我进化 (2026-07-06) — 球星逆袭+比分WLD一致性+参数同步
  - ELO_WEIGHT 0.30→0.45(同步evolution#22)，POISSON_WEIGHT 0.70→0.55
  - 球星逆袭加成: 弱队有超级巨星而强队没有时(KO赛)，弱队xG额外+8%(巴西vs挪威Haaland逆袭验证)
  - 比分WLD一致性: predict_with_consensus支持wld_direction参数，优先选同方向比分
v4.11新增: R32f重大爆冷复盘进化 (2026-07-06)
  - SUPERSTAR_UPSET_BOOST 0.08→0.12(Haaland双响+绝杀验证S级巨星KO战力远超+8%)
  - 巨星分级: S级(Haaland/Mbappé)KO逆袭+12%, A级(Kane/Bellingham/Vinicius)+6%
  - KO_TOTAL_GOALS_DISPERSION: 泊松P(k)方差+15%分散因子(墨西哥2-3红牌+双点球→5球)
  - KO underdog_boost 0.25→0.28(挪威255 Elo差逆袭+墨西哥240差距进2球)
v4.12新增: R16均势双场复盘进化 (2026-07-07)
  - KO东道主压力效应: R16+东道主vs强队(Elo差<150)时, +15%→-5%(美国1-4比利时验证)
  - KO防守型均势识别: 双方avg_conceded<1.0+Elo差<200 → xG-15%(葡0-1西防守战验证)
  - KO_BALANCED_XG_BOOST 0.30→0.20(19场累计均值偏差修正, 降低过度推高)
  - 比分尾部拓宽: poisson_matrix max_goals默认7→KO赛8(美国1-4不在Top6验证)
  - 19场累计: FT方向78.9%·比分Top6 63.2%·总进球Top2 73.7%·HT/FT 52.6%·让球1/11=9.1%
v4.13新增: R16硬币抛掷双场复盘进化 (2026-07-08)
  - KO防守战阈值放宽: KO_DEFENSIVE_BATTLE_CONCEDED 1.0→1.05(哥伦比亚avg_conceded=1.0原本卡在阈值外未触发)
  - 硬币抛掷死锁折扣: Elo差<50且双方防守稳健(avg_conceded<=1.05) → xG强折扣-22%(替代+20% boost)，瑞士0-0验证
  - 总进球尾部分散加宽: KO_TOTAL_GOALS_DISPERSION 0.15→0.25(阿根廷3-2=5球/瑞士0-0均极端漏判，泊松尾部过窄)
  - 精英队高Elo差buffer: Elo>2050顶级队buffer -8%→-4%(阿根廷2100逆转埃及验证，顶级队即便落后也维持输出)
  - 点球标记: 硬币抛掷+双防守稳健时加PENS_LIKELY标记 + 平局概率上调+8%
v4.14新增: QF1法国2-0摩洛哥复盘进化 (2026-07-10)
  - 精英队KO净胜2球修正: 当强队Elo>2050且KO时, 后处理score_probs, 净胜2球×1.18/净胜1球×0.88/净胜3+球×1.10
  - 依据: QF1 Elo差200未触发防守战/硬币抛掷(均严格<200才触发), 模型1-0(16%)>2-0(11.7%), 实际2-0
  - 根因: 精英队对"防守稳健但攻击乏力(缺核心箭头Saibari)"对手时, 下半场技术/体能优势扩大比分
  - 仅后处理比分分布, 不影响FT方向(poisson win_a独立计算), 范围限于精英队KO
v4.15新增: 比分/总进球特征增强 (2026-07-13)
  - 交锋史(H2H): data/h2h.json + get_head_to_head(), expected_goals()以H2H_XG_BLEND(0.15)融合历史交锋进球均值
  - 伤停/阵型 → xG主链路: 修复predict_with_live_data死代码, injuries/lineups经expected_goals()直接进入xG(不再只改WLD)
  - Poisson低比分校准: poisson_matrix()加Dixon-Coles式0-0/1-0/0-1/1-1通缩(仅作用score_probs, 不影响WLD)
  - 回放结论: N=5上OLD=NEW=40%单点命中, 零增益(特性保守 + H2H≈模型xG + 样本太小); 真实15.3%/16.7%弱项来自predict_with_consensus单点pick, 非poisson基座
v4.16新增: 交锋史/伤停注入consensus单点选择 (2026-07-13, 选项A)
  - predict_with_consensus() 新增 injuries/lineups/use_h2h 参数, 透传至predict()→expected_goals(), 使v4.15的H2H+伤停xG接线在共识路径真正生效
  - 用H2H调整xG重建泊松矩阵, 其top_scores并入共识候选池(扩大可覆盖比分线)
  - 总进球选择用H2H avg_total与模型xg_total按H2H_XG_BLEND(0.15)融合
  - 度量局限: 5场回放无历史市场participantCount且含前瞻污染, 无法证明命中率提升; 机制层面西班牙2-1(avg2.0/0.96→2:1)与真实赛果吻合
"""

import math
import json
import os
from typing import Dict, List, Tuple, Optional

# ============================================
# 核心参数
# ============================================
LEAGUE_AVG_GOALS = 1.35
ELO_WEIGHT = 0.45       # v4.10: 0.30→0.45(同步evolution#22, 累计WLD 73.3%支持高Elo权重)
POISSON_WEIGHT = 0.55   # v4.10: 0.70→0.55(总分准确率仅~29%, 降低泊松权重)
DEFENSE_REGRESSION = 0.30
DEFENSE_EXTREME_THRESHOLD = 0.5

# ============================================
# v4.4 新增: 东道主效应 + 球星加成
# ============================================
# 2026世界杯联合东道主（墨西哥/加拿大/美国）主场优势
HOST_NATIONS_2026 = {'墨西哥', '加拿大', '美国'}
HOST_XG_BOOST = 0.15       # 东道主xG +15%
HOST_OPPONENT_XG_PENALTY = 0.10  # 东道主对手xG -10%

# 超级巨星名单（KO赛爆发力难以用历史xG捕捉）
# 依据: 2026 R32复盘 — Mbappé双响(法国3-0瑞典, 模型xG低估1.31球)
# v4.5扩充: Kane(英格兰WC13球+逆转英雄)、De Bruyne(比利时核心中场)
# v4.11分级: S级(Top-3全球终结者, KO双响级), A级(顶级但终结能力不如S级)
SUPERSTAR_ROSTER = {
    'Mbappé': '法国',       # S级: Top-1全球射手, KO双响能力
    'Haaland': '挪威',      # S级: Top-2全球射手, KO双响79'90'绝杀巴西
    'Bellingham': '英格兰',  # A级: 顶级中场，双响能力(36'38')
    'Kane': '英格兰',        # A级: WC13球历史射手王, 逆转英雄75'86'
    'Vinicius': '巴西',      # A级: 顶级边锋, 终结能力不如S级
    'Lautaro': '阿根廷',     # A级
    'Musiala': '德国',       # A级
    'Yamal': '西班牙',       # A级: 年轻天才, 体系效应
    'De Bruyne': '比利时',   # A级: 核心中场, R32 AET绝杀助攻
}
SUPERSTAR_S_TIER = {'Mbappé', 'Haaland'}  # v4.11: S级巨星KO逆袭+12%
SUPERSTAR_A_TIER = {'Bellingham', 'Kane', 'Vinicius', 'Lautaro', 'Musiala', 'Yamal', 'De Bruyne'}

SUPERSTAR_XG_BOOST = 0.12  # 有超级巨星的球队KO赛xG +12% (v4.6: 0.10→0.12, 体系效应)

# v4.11: 球星逆袭加成 (Haaland效应) — 分级增强
# 依据: 2026 R16巴西1-2挪威 — Haaland(S级)双响+90'绝杀, 而Vinicius(A级)未进球
# 不同级别的巨星在KO赛的终结能力差距巨大: S级可以凭个人能力翻盘, A级需要团队支持
# S级巨星→弱队KO逆袭+12%, A级巨星→维持+6%
SUPERSTAR_UPSET_BOOST = 0.12          # v4.11: 0.08→0.12 (弱队有S级巨星KO逆袭xG+12%)
SUPERSTAR_A_UPSET_BOOST = 0.06        # v4.11新增: A级巨星KO逆袭xG+6%

# ============================================
# v4.5 新增: KO均势对决xG爆发修正
# ============================================
# 依据: R32c复盘 — 比利时vs塞内加尔模型xG合计2.01→实际90分钟4球(2倍误差)
# 均势对决在KO赛中"背水一战"心态大幅推高进球数，泊松模型无法捕捉
KO_BALANCED_XG_BOOST = 0.20       # v4.12: 0.30→0.20 (19场累计均值修正, 葡西高估2.13+美比低估1.45)
KO_BALANCED_ELO_THRESHOLD = 200   # Elo差距<200判定为均势
KO_BALANCED_XG_RATIO = 1.30       # xG最大值/最小值<1.3判定为均势xG

# ============================================
# v4.12 新增: KO东道主压力效应 + 防守型均势识别
# ============================================
# 依据: R16美国1-4比利时 — 美国获+15%xG boost但实际xG仅0.63(vs比利时2.01)
# 东道主在R16+面对强队(Elo差<150)时, 主场压力>主场优势
# R32东道主vs弱队(墨西哥2-0厄瓜多尔, 美国2-0波黑)时+15%仍然正确
KO_HOST_PRESSURE_ELO_GAP = 150    # 东道主Elo低于对手<150时触发压力效应
KO_HOST_PRESSURE_XG_PENALTY = 0.05  # 东道主xG -5% (替代+15% boost)
KO_HOST_PRESSURE_OPPONENT_RESTORE = True  # 对手不再被-10% penalty

# 依据: R16葡萄牙0-1西班牙 — 双方防守强队均势对决, 模型xG 3.13→实际1球
# 当双方场均失球均<1.0时, KO赛趋于低比分防守战, xG应下调而非boost
KO_DEFENSIVE_BATTLE_CONCEDED = 1.05  # v4.13: 1.0→1.05 (覆盖哥伦比亚avg_conceded=1.0原本卡在阈值外)
KO_DEFENSIVE_BATTLE_XG_DISCOUNT = 0.15  # 防守型均势xG -15% (替代+20% boost)

# ============================================
# v4.13 新增: KO硬币抛掷死锁 + 总进球尾部分散 + 精英队修正
# 依据: R16瑞士0-0哥伦比亚 — Elo差仅6触发balanced boost(+20%)但哥伦比亚avg_conceded=1.0
#       恰好未<1.0阈值, 防守战标记未触发, xG被推高至2.74, 实际0-0
#       阿根廷3-2埃及 — 模型xG 2.24→实际5球, 泊松尾部过窄+精英队输出被压
# 三处修复:
#   (1) 硬币抛掷死锁: Elo差<50且双方防守稳健(avg_conceded<=1.05) → 强死锁折扣+平局上调
#   (2) 总进球尾部分散: KO赛泊松方差+25%(15%→25%), 双侧尾部(0球/5+球)概率提升
#   (3) 精英队修正: Elo>2050的顶级队高Elo差buffer从-8%降至-4%(阿根廷逆转验证)
KO_COINFLIP_ELO_THRESHOLD = 50         # Elo差<50判定为真正硬币抛掷
KO_PENS_LIKELY_DRAW_BOOST = 0.08       # 硬币抛掷时平局概率上调(→点球概率标记)
KO_DEADLOCK_XG_DISCOUNT = 0.22         # 硬币抛掷+双防守稳健 → xG强折扣(替代+20% boost)
KO_TOTAL_GOALS_DISPERSION = 0.25       # v4.13: 0.15→0.25 (KO总进球泊松尾部加宽)
ELITE_ELO_THRESHOLD = 2050             # Elo>2050判定为顶级精英队
HIGH_ELO_GAP_FAV_BUFFER_ELITE = 0.04   # v4.13: 精英队高Elo差buffer -8%→-4%

# v4.14 新增: 精英队 KO 净胜2球修正
# 依据: QF1 法国2-0摩洛哥 — Elo差200(未触发防守战/硬币抛掷), 模型1-0(16%)>2-0(11.7%)实际2-0
#   精英队(>2050)对"防守稳健但攻击乏力"对手时, 下半场技术/体能优势扩大比分, 净胜2球概率应高于泊松默认
#   后处理 score_probs: 不影响FT方向(来自poisson win_a), 只调比分分布
ELITE_WIN2_BOOST = 0.18      # 净胜2球单元格 ×1.18
ELITE_WIN1_DAMP = 0.12       # 净胜1球单元格 ×0.88
ELITE_WIN3_BOOST = 0.10      # 净胜3+球单元格 ×1.10

# ============================================
# v4.6→v4.7 修正: KO主导胜xG修正（设上限 + 高Elo差缓冲）
# ============================================
# v4.7: 0.08→0.05 (阿根廷73.7%被佛得角逼平，主导胜修正过度激进)
# 新增上限: 强队xG总增幅(含此前叠加)不超过+15%
KO_FAVORITE_XG_BOOST = 0.05       # 主导方额外xG +5% (v4.7: 0.08→0.05)
KO_FAVORITE_ELO_THRESHOLD = 150   # Elo差距>150判定为主导
KO_FAVORITE_XG_RATIO = 1.50       # xG最大值/最小值>1.5判定为主导
KO_FAVORITE_OPPONENT_PENALTY = 0.05  # 被主导方xG -5%
KO_FAVORITE_MAX_TOTAL_BOOST = 0.15   # v4.7新增: 强队xG总增幅上限+15%

# ============================================
# v4.7 新增: 高Elo差爆冷缓冲 + 首次KO赛黑马加成
# ============================================
# 依据: R32d复盘 — 阿根廷(560 Elo差)被佛得角(首次KO)1-1逼平
# 高Elo差(>400)时强队倾向于"控制而非屠杀" → xG被系统性高估
# 首次进KO赛的球队往往超水平发挥 → 需要独立加成
HIGH_ELO_GAP_THRESHOLD = 400          # Elo差>400触发爆冷缓冲
HIGH_ELO_GAP_FAV_BUFFER = 0.08        # 高Elo差强队xG -8% (避免屠杀预期)
HIGH_ELO_GAP_UNDERDOG_BOOST = 0.06    # 高Elo差弱队xG +6% (爆冷潜力)

# 首次世界杯淘汰赛球队名单（2026 R32d验证: 佛得角首秀逼平阿根廷）
FIRST_KO_DEBUT_BOOST = 0.08           # 首次进KO赛球队xG +8%
DEFAULT_FIRST_KO_DEBUT_TEAMS = {      # v4.7: 需要通过比赛进程手动维护
    '佛得角', 'Cape Verde',
    # 随着比赛推进陆续添加其他首次KO球队
}

# ============================================
# v4.15 新增: 比分/总进球特征增强（交锋史 + 伤停/阵型 + 比分线校准）
# 依据: 复盘准确率 比分15.3% / 总进球16.7% 为最弱维度
#   1) 交锋史(H2H): 两队历史交锋进球倾向微调xG均值（data/h2h.json）
#   2) 伤停/阵型: 从predict_with_live_data死代码接入expected_goals()主链路
#   3) 比分线校准: Dixon-Coles式低比分(0-0/1-0/0-1/1-1)修正, 校正泊松对低比分的过预测
H2H_XG_BLEND = 0.15              # H2H历史均值对xG的融合权重(保守, 避免小样本过拟合)
DC_LOW_00 = 0.12                 # 0-0单元格通缩(校正泊松对0-0的过预测)
DC_LOW_10 = 0.06                 # 1-0单元格通缩
DC_LOW_01 = 0.06                 # 0-1单元格通缩
DC_LOW_11 = 0.04                 # 1-1单元格通缩
SCORELINE_CAL_DEFAULT = True     # 比分线校准默认开启(回放可统一关闭)


class FootballPredictionEngine:
    """足球比赛预测引擎 v3.2+"""
    
    # v3.4: R1→R2攻击动量 — 首轮进球3+的球队在R2获得xG加成
    R1_SCORING_THRESHOLD = 3    # 首轮进球≥3球触发动量
    R1_MOMENTUM_BOOST = 0.15    # 首轮3+进球→R2 xG +15%

    # v4.4: 东道主效应 + 球星加成开关（默认开启，可关闭用于回测）
    _host_effect_enabled = True
    _superstar_effect_enabled = True

    def __init__(self, data_dir: str = None):
        self.elo_ratings = {}
        self.team_stats = {}
        self.prediction_log = []
        # v4.0: 可被进化引擎注入的自定义轮次系数
        self._round_coefficients = None
        # v3.4: 首轮进球追踪用于R2攻击动量修正
        self._r1_goals = {}  # {team_name: goals_scored}
        # v4.4: 赛事东道主名单（默认2026世界杯联合东道主）
        self._host_nations = set(HOST_NATIONS_2026)
        # v4.4: 球星→球队映射（默认内置名单）
        self._superstar_map = dict(SUPERSTAR_ROSTER)
        # v4.7: 首次KO赛球队追踪
        self._first_ko_debut_teams = set(DEFAULT_FIRST_KO_DEBUT_TEAMS)

        # v4.15: 特征增强开关 + 状态
        self._h2h_enabled = True
        self._injury_formation_enabled = True
        self._scoreline_cal_enabled = SCORELINE_CAL_DEFAULT
        self._h2h_data = {}
        self._injuries = None
        self._lineups = None

        if data_dir:
            self.load_data(data_dir)
    
    def load_data(self, data_dir: str):
        """加载数据文件"""
        elo_path = os.path.join(data_dir, 'elo_ratings.json')
        stats_path = os.path.join(data_dir, 'team_stats.json')
        
        if os.path.exists(elo_path):
            with open(elo_path, 'r', encoding='utf-8') as f:
                self.elo_ratings = json.load(f)
        
        if os.path.exists(stats_path):
            with open(stats_path, 'r', encoding='utf-8') as f:
                self.team_stats = json.load(f)

        # v4.15: 加载交锋史(H2H)数据
        h2h_path = os.path.join(data_dir, 'h2h.json')
        if os.path.exists(h2h_path):
            with open(h2h_path, 'r', encoding='utf-8') as f:
                self._h2h_data = json.load(f)

    def set_r1_scoring(self, team_goals: Dict[str, int]):
        """v3.4: 设置各队首轮进球数，用于R2攻击动量修正

        用法：赛后记录各队R1进球 → 下轮预测时自动对3+进球的球队
        在R2给xG + R1_MOMENTUM_BOOST(15%)加成
        
        Args:
            team_goals: {team_name: goals_scored_in_r1, ...}
        """
        self._r1_goals = dict(team_goals)
    
    def set_round_coefficients(self, coefficients: Dict):
        """v4.0: 接受进化引擎注入的自定义轮次系数
        
        Args:
            coefficients: {
                'group_stage_round1': {'fav_discount': 0.50, 'underdog_boost': 0.40, 'draw_boost': 0.15},
                'group_stage_round2': {'fav_discount': 1.10, 'underdog_boost': -0.20, 'draw_boost': -0.10},
                ...
            }
        """
        self._round_coefficients = coefficients

    def set_host_nations(self, hosts: set):
        """v4.4: 设置赛事东道主名单

        Args:
            hosts: {'墨西哥', '加拿大', '美国'} 或其他赛事的东道主集合
        """
        self._host_nations = set(hosts)

    def set_superstar_map(self, star_to_team: Dict[str, str]):
        """v4.4: 设置超级巨星→球队映射

        Args:
            star_to_team: {'Mbappé': '法国', 'Haaland': '挪威', ...}
        """
        self._superstar_map = dict(star_to_team)

    def set_first_ko_debut_teams(self, teams: set):
        """v4.7: 设置首次世界杯淘汰赛球队名单

        Args:
            teams: {'佛得角', 'Cape Verde', ...} 首次进KO赛的球队集合
        """
        self._first_ko_debut_teams = set(teams)

    # v4.15 新增: 特征增强 setter + 查询
    def set_head_to_head(self, h2h: Dict):
        """v4.15: 注入交锋史数据 { 'A|B': {...}, ... }（顺序无关，引擎自动解析方向）"""
        self._h2h_data = h2h or {}

    def set_injuries(self, injuries: Dict):
        """v4.15: 设置伤停数据（与predict_with_live_data格式一致: home_out_count等）"""
        self._injuries = injuries

    def set_lineups(self, lineups: Dict):
        """v4.15: 设置阵容/阵型数据（含 home/away.formation）"""
        self._lineups = lineups

    def toggle_features(self, h2h: bool = None, injury_formation: bool = None,
                        scoreline_cal: bool = None):
        """v4.15: 回放用 — 统一开关三大新特性（None=保持当前值）"""
        if h2h is not None:
            self._h2h_enabled = h2h
        if injury_formation is not None:
            self._injury_formation_enabled = injury_formation
        if scoreline_cal is not None:
            self._scoreline_cal_enabled = scoreline_cal

    def get_head_to_head(self, team_a: str, team_b: str) -> Optional[Dict]:
        """v4.15: 获取两队交锋史（顺序无关）

        Returns:
            {'avg_a': float, 'avg_b': float, 'avg_total': float, 'meetings': int, ...}
            其中 avg_a/avg_b 已按 (team_a, team_b) 方向对齐；无数据返回 None
        """
        if not self._h2h_enabled:
            return None
        for key, rec in self._h2h_data.items():
            parts = key.split('|')
            if len(parts) == 2 and {parts[0], parts[1]} == {team_a, team_b}:
                gf = rec.get('goals_for', {})
                if team_a in gf and team_b in gf:
                    return {
                        'avg_a': gf[team_a],
                        'avg_b': gf[team_b],
                        'avg_total': rec.get('avg_total'),
                        'meetings': rec.get('meetings'),
                        'source': rec.get('source'),
                        'note': rec.get('note'),
                    }
        return None

    def _team_has_superstar(self, team: str) -> bool:
        """v4.4: 检查球队是否有超级巨星"""
        return team in self._superstar_map.values()
    
    def elo_expected(self, elo_a: float, elo_b: float) -> float:
        return 1 / (1 + 10 ** ((elo_b - elo_a) / 400))
    
    @staticmethod
    def poisson_prob(lam: float, k: int) -> float:
        return (lam ** k) * math.exp(-lam) / math.factorial(k)
    
    def expected_goals(self, team_a: str, team_b: str, 
                       is_knockout: bool = False,
                       tournament_round: str = None,
                       injuries: Dict = None,
                       lineups: Dict = None) -> Tuple[float, float]:
        stats_a = self.team_stats.get(team_a, {'avg_goals': LEAGUE_AVG_GOALS, 'avg_conceded': LEAGUE_AVG_GOALS})
        stats_b = self.team_stats.get(team_b, {'avg_goals': LEAGUE_AVG_GOALS, 'avg_conceded': LEAGUE_AVG_GOALS})
        
        attack_a = stats_a['avg_goals'] / LEAGUE_AVG_GOALS
        defense_a = stats_a['avg_conceded'] / LEAGUE_AVG_GOALS
        attack_b = stats_b['avg_goals'] / LEAGUE_AVG_GOALS
        defense_b = stats_b['avg_conceded'] / LEAGUE_AVG_GOALS
        
        # v1.1修正: 淘汰赛极端防守均值回归
        if is_knockout:
            if defense_b < DEFENSE_EXTREME_THRESHOLD:
                defense_b = defense_b * (1 - DEFENSE_REGRESSION) + 1.0 * DEFENSE_REGRESSION
            if defense_a < DEFENSE_EXTREME_THRESHOLD:
                defense_a = defense_a * (1 - DEFENSE_REGRESSION) + 1.0 * DEFENSE_REGRESSION
        
        # v2.0/v2.1/v4.0修正: 大赛轮次自适应xG修正
        # 2026-06-16复盘: 首轮4场全平，强队xG被高估
        # 2026-06-17复盘: 第2轮4场3穿盘，强队xG被严重低估
        # v4.0: 进化引擎可注入自定义系数，优先使用注入值
        # 结论: 不同轮次强队表现差异巨大，需要按轮次调整
        if tournament_round in ['group_stage_round1', 'group_stage_round2',
                               'group_stage_round3', 'knockout_stage']:
            elo_a = self.elo_ratings.get(team_a, 1500)
            elo_b = self.elo_ratings.get(team_b, 1500)
            
            # v4.0: 优先使用进化引擎注入的自定义系数，否则用默认硬编码
            round_coefficients = self._round_coefficients if self._round_coefficients else {
                'group_stage_round1': {
                    'fav_discount': 0.65,    # v3.3: 首轮强队折扣(60%→65%，6/18复核强队胜率75%)
                    'underdog_boost': 0.25,  # v3.3: 首轮弱队加成(0.40→0.25，实际弱队进球均值仅1.25)
                    'draw_boost': 0.08       # v3.3: 首轮平局上调(0.15→0.08，回归25%平局均值)
                },
                'group_stage_round2': {
                    'fav_discount': 1.10,    # 第2轮强队反弹+10%(打出血性)
                    'underdog_boost': -0.20, # 第2轮弱队-0.20(回归常态)
                    'draw_boost': -0.10      # 第2轮平局下调
                },
                'group_stage_round3': {
                    'fav_discount': 1.00,    # 第3轮接近常态
                    'underdog_boost': 0.00,
                    'draw_boost': -0.05
                },
                'knockout_stage': {
                    'fav_discount': 0.95,    # 淘汰赛强队略打折(防守更严)
                    'underdog_boost': 0.10,  # 弱队稍加成
                    'draw_boost': 0.10       # v4.3: 0.05→0.10, R32复盘3场2平验证
                }
            }
            
            coeffs = round_coefficients[tournament_round]
            
            if elo_a > elo_b:
                attack_a *= coeffs['fav_discount']
                attack_b += coeffs['underdog_boost'] / LEAGUE_AVG_GOALS
            elif elo_b > elo_a:
                attack_b *= coeffs['fav_discount']
                attack_a += coeffs['underdog_boost'] / LEAGUE_AVG_GOALS
            # else: Elo相等，不修正
        
        xg_a = LEAGUE_AVG_GOALS * attack_a * defense_b
        xg_b = LEAGUE_AVG_GOALS * attack_b * defense_a

        # v3.4: R1→R2攻击动量修正
        # 如果首轮进球≥3，R2的攻击力会有惯性余势(挪威首轮4-1→R2攻击力被低估)
        # 只在R2启用（R3已回归常态）
        if tournament_round == 'group_stage_round2' and self._r1_goals:
            r1_a = self._r1_goals.get(team_a, 0)
            r1_b = self._r1_goals.get(team_b, 0)
            if r1_a >= self.R1_SCORING_THRESHOLD:
                xg_a *= (1 + self.R1_MOMENTUM_BOOST)
            if r1_b >= self.R1_SCORING_THRESHOLD:
                xg_b *= (1 + self.R1_MOMENTUM_BOOST)

        # v4.4→v4.12: 东道主效应修正（KO赛生效）
        # v4.4: 东道主主场xG +15%, 对手xG -10%
        # v4.12新增: 东道主压力效应 — R16+东道主vs强队(Elo差<150)时反转
        #   依据: 美国R16 1-4比利时, 美国xG+15%但实际xG仅0.63
        #   东道主面对强队时观众期望→压力→失误, 主场优势变劣势
        if self._host_effect_enabled and is_knockout:
            a_is_host = team_a in self._host_nations
            b_is_host = team_b in self._host_nations
            elo_a_val = self.elo_ratings.get(team_a, 1500)
            elo_b_val = self.elo_ratings.get(team_b, 1500)
            
            if a_is_host and not b_is_host:
                # v4.12: 东道主压力效应判定
                host_pressure = (elo_b_val - elo_a_val) > 0 and \
                                abs(elo_a_val - elo_b_val) < KO_HOST_PRESSURE_ELO_GAP
                if host_pressure:
                    # 东道主vs强队, 压力>优势
                    xg_a *= (1 - KO_HOST_PRESSURE_XG_PENALTY)
                    # 对手不再被penalty (恢复常态)
                else:
                    # 东道主vs弱队或均势, 正常+15%
                    xg_a *= (1 + HOST_XG_BOOST)
                    xg_b *= (1 - HOST_OPPONENT_XG_PENALTY)
            elif b_is_host and not a_is_host:
                host_pressure = (elo_a_val - elo_b_val) > 0 and \
                                abs(elo_a_val - elo_b_val) < KO_HOST_PRESSURE_ELO_GAP
                if host_pressure:
                    xg_b *= (1 - KO_HOST_PRESSURE_XG_PENALTY)
                else:
                    xg_b *= (1 + HOST_XG_BOOST)
                    xg_a *= (1 - HOST_OPPONENT_XG_PENALTY)

        # v4.4: 球星加成（KO赛生效）
        # 依据: 2026 R32复盘 — 法国3-0瑞典，Mbappé双响，模型xG 1.69 vs 实际3球，误差+1.31
        # 超级巨星在KO赛爆发力难以用历史平均xG捕捉
        if self._superstar_effect_enabled and is_knockout:
            if self._team_has_superstar(team_a):
                xg_a *= (1 + SUPERSTAR_XG_BOOST)
            if self._team_has_superstar(team_b):
                xg_b *= (1 + SUPERSTAR_XG_BOOST)

        # v4.11: 球星逆袭加成 — 分级增强
        # S级(Haaland/Mbappé)KO逆袭+12%, A级(Kane/Bellingham等)维持+6%
        # 依据: 2026 R16巴西1-2挪威 — Haaland(S级)双响79'90'绝杀, Vinicius(A级)未进球
        if self._superstar_effect_enabled and is_knockout:
            elo_a = self.elo_ratings.get(team_a, 1500)
            elo_b = self.elo_ratings.get(team_b, 1500)
            elo_gap = abs(elo_a - elo_b)

            if 200 <= elo_gap <= 400:
                # 弱队A有S级巨星 + 强队B没有巨星
                if elo_a < elo_b:
                    a_stars = [s for s, t in self._superstar_map.items() if t == team_a]
                    b_has_star = self._team_has_superstar(team_b)
                    if a_stars and not b_has_star:
                        # 分级判定
                        if any(s in SUPERSTAR_S_TIER for s in a_stars):
                            xg_a *= (1 + SUPERSTAR_UPSET_BOOST)  # S级+12%
                        elif any(s in SUPERSTAR_A_TIER for s in a_stars):
                            xg_a *= (1 + SUPERSTAR_A_UPSET_BOOST)  # A级+6%
                # 弱队B有S级巨星 + 强队A没有巨星
                elif elo_b < elo_a:
                    b_stars = [s for s, t in self._superstar_map.items() if t == team_b]
                    a_has_star = self._team_has_superstar(team_a)
                    if b_stars and not a_has_star:
                        if any(s in SUPERSTAR_S_TIER for s in b_stars):
                            xg_b *= (1 + SUPERSTAR_UPSET_BOOST)  # S级+12%
                        elif any(s in SUPERSTAR_A_TIER for s in b_stars):
                            xg_b *= (1 + SUPERSTAR_A_UPSET_BOOST)  # A级+6%

        # v4.5→v4.12: KO均势对决xG爆发修正（含防守型均势例外）
        # v4.5: 均势对决(Elo差<200, xG接近<1.3倍)在KO赛背水一战心态下进球远超预期
        # v4.12新增: 防守型均势例外 — 双方avg_conceded<1.0时为防守战, xG应-15%而非+20%
        #   依据: 葡0-1西(模型xG 3.13->实际1球), 双方均为防守强队
        if is_knockout:
            elo_a = self.elo_ratings.get(team_a, 1500)
            elo_b = self.elo_ratings.get(team_b, 1500)
            xg_max = max(xg_a, xg_b)
            xg_min = min(xg_a, xg_b)
            xg_ratio = xg_max / max(xg_min, 0.01)

            # v4.13: 防守型均势判定 (阈值放宽至1.05, 覆盖哥伦比亚avg_conceded=1.0)
            stats_a_def = stats_a.get('avg_conceded', LEAGUE_AVG_GOALS)
            stats_b_def = stats_b.get('avg_conceded', LEAGUE_AVG_GOALS)
            both_solid_defense = (stats_a_def <= KO_DEFENSIVE_BATTLE_CONCEDED and
                                  stats_b_def <= KO_DEFENSIVE_BATTLE_CONCEDED)
            is_defensive_battle = (both_solid_defense and
                                    abs(elo_a - elo_b) < KO_BALANCED_ELO_THRESHOLD)

            # v4.13: 硬币抛掷死锁判定 (Elo差<50 + 双防守稳健)
            # 依据: 瑞士0-0哥伦比亚(Elo差6), 真正硬币抛掷且双方防守扎实→易闷平/点球
            is_coinfllip_deadlock = (both_solid_defense and
                                     abs(elo_a - elo_b) < KO_COINFLIP_ELO_THRESHOLD)

            if is_coinfllip_deadlock:
                # 硬币抛掷死锁: 强折扣(比防守战-15%更狠), xG大幅下调
                xg_a *= (1 - KO_DEADLOCK_XG_DISCOUNT)
                xg_b *= (1 - KO_DEADLOCK_XG_DISCOUNT)
            elif is_defensive_battle:
                # 防守型均势: xG下调而非boost
                xg_a *= (1 - KO_DEFENSIVE_BATTLE_XG_DISCOUNT)
                xg_b *= (1 - KO_DEFENSIVE_BATTLE_XG_DISCOUNT)
            elif abs(elo_a - elo_b) < KO_BALANCED_ELO_THRESHOLD and xg_ratio < KO_BALANCED_XG_RATIO:
                # 普通均势: +20% boost (v4.12: 从+30%下调)
                xg_a *= (1 + KO_BALANCED_XG_BOOST)
                xg_b *= (1 + KO_BALANCED_XG_BOOST)

        # v4.7: KO主导胜xG修正（设上限 + 高Elo差缓冲替代v4.6旧逻辑）
        # v4.6: +8%无上限 → v4.7: +5%且设总增幅上限+15%
        # 依据: R32d阿根廷73.7%被佛得角逼平，主导胜修正过度激进
        if is_knockout:
            xg_ratio_fav = max(xg_a, xg_b) / max(min(xg_a, xg_b), 0.01)
            elo_gap = abs(elo_a - elo_b)
            if elo_gap > KO_FAVORITE_ELO_THRESHOLD and xg_ratio_fav > KO_FAVORITE_XG_RATIO:
                # v4.7: 主导胜修正设上限 — 强队xG总增幅不超过+15%
                if xg_a > xg_b:
                    pre_boost_xg = xg_a
                    xg_a *= (1 + KO_FAVORITE_XG_BOOST)
                    actual_boost = (xg_a - pre_boost_xg) / pre_boost_xg
                    if actual_boost > KO_FAVORITE_MAX_TOTAL_BOOST:
                        xg_a = pre_boost_xg * (1 + KO_FAVORITE_MAX_TOTAL_BOOST)
                    xg_b *= (1 - KO_FAVORITE_OPPONENT_PENALTY)
                else:
                    pre_boost_xg = xg_b
                    xg_b *= (1 + KO_FAVORITE_XG_BOOST)
                    actual_boost = (xg_b - pre_boost_xg) / pre_boost_xg
                    if actual_boost > KO_FAVORITE_MAX_TOTAL_BOOST:
                        xg_b = pre_boost_xg * (1 + KO_FAVORITE_MAX_TOTAL_BOOST)
                    xg_a *= (1 - KO_FAVORITE_OPPONENT_PENALTY)

        # v4.7: 高Elo差(>400)爆冷缓冲
        # 依据: R32d阿根廷(560 Elo差)→被佛得角1-1逼平
        # 英格兰(Kane 2-goal)高Elo差场景同样未兑现屠杀
        # 高Elo差时强队"控制而非屠杀"→xG被系统性高估
        if is_knockout:
            elo_gap = abs(self.elo_ratings.get(team_a, 1500) - self.elo_ratings.get(team_b, 1500))
            if elo_gap > HIGH_ELO_GAP_THRESHOLD:
                # v4.13: 精英队(Elo>2050)高Elo差buffer从-8%降至-4%
                # 依据: 阿根廷(Elo2100)3-2埃及, 顶级队即便落后也能维持输出(逆转验证)
                fav_elo_a = self.elo_ratings.get(team_a, 1500)
                fav_elo_b = self.elo_ratings.get(team_b, 1500)
                fav_buffer = HIGH_ELO_GAP_FAV_BUFFER_ELITE if (
                    fav_elo_a > ELITE_ELO_THRESHOLD or fav_elo_b > ELITE_ELO_THRESHOLD
                ) else HIGH_ELO_GAP_FAV_BUFFER
                if fav_elo_a > fav_elo_b:
                    xg_a *= (1 - fav_buffer)  # 强队xG折扣(精英-4%/普通-8%)
                    xg_b *= (1 + HIGH_ELO_GAP_UNDERDOG_BOOST)  # 弱队xG +6%
                else:
                    xg_b *= (1 - fav_buffer)
                    xg_a *= (1 + HIGH_ELO_GAP_UNDERDOG_BOOST)

        # v4.7: 首次淘汰赛黑马精神加成
        # 依据: R32d佛得角(首次KO赛)逼平阿根廷，表现远超纸面实力
        # 首次进世界杯淘汰赛的球队往往有"无惧无畏"的超常发挥
        if is_knockout and self._first_ko_debut_teams:
            if team_a in self._first_ko_debut_teams:
                xg_a *= (1 + FIRST_KO_DEBUT_BOOST)
            if team_b in self._first_ko_debut_teams:
                xg_b *= (1 + FIRST_KO_DEBUT_BOOST)

        # v4.15: 伤停/阵型 → xG 主链路接线（修复 predict_with_live_data 死代码）
        # 此前阵型/伤停只改WLD corrections, 从不进入xG → 比分分布完全不受影响
        # 现在直接作为xG乘子, 让伤停/阵型真正改变比分与总进球分布
        if self._injury_formation_enabled:
            inj = injuries if injuries is not None else self._injuries
            lin = lineups if lineups is not None else self._lineups
            if lin:
                mod_a, mod_b = self._adjust_xg_for_lineups(team_a, team_b, lin)
                xg_a *= mod_a
                xg_b *= mod_b
            if inj:
                elo_a0 = self.elo_ratings.get(team_a, 1500)
                elo_b0 = self.elo_ratings.get(team_b, 1500)
                elo_a_adj, elo_b_adj = self._adjust_elo_for_injuries(team_a, team_b, inj)
                # 将伤停导致的Elo折损折算为xG乘子(15 Elo ≈ 1% xG, 系数1.5放大可见度)
                if elo_a_adj != elo_a0:
                    xg_a *= (1 + (elo_a_adj - elo_a0) / max(elo_a0, 1) * 1.5)
                if elo_b_adj != elo_b0:
                    xg_b *= (1 + (elo_b_adj - elo_b0) / max(elo_b0, 1) * 1.5)

        # v4.15: 交锋史(H2H) → xG 均值微调
        # 两队历史交锋的进球倾向是比分/总进球的有效先验；
        # 仅以保守权重(H2H_XG_BLEND)融合, 避免小样本/极端值(如1-7)过拟合
        if self._h2h_enabled:
            h2h = self.get_head_to_head(team_a, team_b)
            if h2h and h2h.get('avg_a') is not None and h2h.get('avg_b') is not None:
                xg_a = xg_a * (1 - H2H_XG_BLEND) + h2h['avg_a'] * H2H_XG_BLEND
                xg_b = xg_b * (1 - H2H_XG_BLEND) + h2h['avg_b'] * H2H_XG_BLEND

        return xg_a, xg_b
    
    def poisson_matrix(self, xg_a: float, xg_b: float, max_goals: int = 7,
                       ko_dispersion: float = 0.0) -> Dict:
        win_a = draw = win_b = 0.0
        score_probs = {}
        raw = {}
        for ga in range(max_goals):
            for gb in range(max_goals):
                p = self.poisson_prob(xg_a, ga) * self.poisson_prob(xg_b, gb)
                raw[(ga, gb)] = p
                if ga > gb:
                    win_a += p
                elif ga == gb:
                    draw += p
                else:
                    win_b += p
        
        # v4.13: KO赛总进球尾部加宽
        # 泊松模型低估极端比分(0球闷平 / 5+球大战)概率, 对尾部加权提升概率质量
        if ko_dispersion > 0:
            mean_total = sum((ga + gb) * p for (ga, gb), p in raw.items())
            adj = {}
            for (ga, gb), p in raw.items():
                total = ga + gb
                dev = abs(total - mean_total)
                if total == 0 or total >= 4:
                    # 极端尾部: 强加权 (0球和5+球更强)
                    factor = 1 + ko_dispersion * (1.5 if (total == 0 or total >= 5) else 1.0)
                elif dev >= 2:
                    factor = 1 + ko_dispersion * 0.5
                else:
                    # 中心区(1-3球)轻微降权, 让出概率质量给尾部
                    factor = 1 - ko_dispersion * 0.25
                adj[(ga, gb)] = p * factor
            s = sum(adj.values())
            raw = {k: v / s for k, v in adj.items()}
            win_a = draw = win_b = 0.0
            for (ga, gb), p in raw.items():
                if ga > gb:
                    win_a += p
                elif ga == gb:
                    draw += p
                else:
                    win_b += p
        
        for (ga, gb), p in raw.items():
            score_probs[f"{ga}-{gb}"] = round(p * 100, 2)
        
        # v4.15: Dixon-Coles式低比分修正 — 仅作用于比分分布, 不影响WLD(win_a/draw/win_b)
        # 独立泊松对 0-0/1-0/0-1/1-1 存在系统性过预测(实际足球低比分略少),
        # 轻度通缩把概率质量推向邻格, 使单点比分/总进球分布更贴近真实频率
        if self._scoreline_cal_enabled:
            dc = {(0, 0): DC_LOW_00, (1, 0): DC_LOW_10, (0, 1): DC_LOW_01, (1, 1): DC_LOW_11}
            cal = {}
            for sc, pct in score_probs.items():
                ga, gb = map(int, sc.split('-'))
                f = 1.0 - dc.get((ga, gb), 0.0)
                cal[sc] = pct * f
            s = sum(cal.values())
            score_probs = {k: round(v / s * 100, 2) for k, v in cal.items()}
        
        return {'win_a': win_a, 'draw': draw, 'win_b': win_b, 'score_probs': score_probs}
    
    def predict(self, team_a: str, team_b: str,
                corrections: Dict = None, is_knockout: bool = False,
                tournament_round: str = None,
                injuries: Dict = None,
                lineups: Dict = None) -> Dict:
        corrections = corrections or {}
        
        elo_a = self.elo_ratings.get(team_a, 1500)
        elo_b = self.elo_ratings.get(team_b, 1500)
        elo_exp_a = self.elo_expected(elo_a, elo_b)
        
        xg_a, xg_b = self.expected_goals(team_a, team_b, is_knockout, tournament_round,
                                         injuries, lineups)
        poisson = self.poisson_matrix(
            xg_a, xg_b,
            ko_dispersion=KO_TOTAL_GOALS_DISPERSION if is_knockout else 0.0
        )

        # v4.14: 精英队 KO 净胜2球修正 (后处理 score_probs, 不影响 FT 方向)
        # 依据: QF1法国2-0摩洛哥, 模型1-0>2-0但实际2-0; 精英队下半场扩大比分
        if is_knockout and (elo_a >= ELITE_ELO_THRESHOLD or elo_b >= ELITE_ELO_THRESHOLD):
            fav_is_a = elo_a > elo_b
            _adj_sp = {}
            for _score, _p in poisson['score_probs'].items():
                _ga, _gb = map(int, _score.split('-'))
                _diff = (_ga - _gb) if fav_is_a else (_gb - _ga)
                if _diff == 2:
                    _adj_sp[_score] = _p * (1 + ELITE_WIN2_BOOST)
                elif _diff == 1:
                    _adj_sp[_score] = _p * (1 - ELITE_WIN1_DAMP)
                elif _diff >= 3:
                    _adj_sp[_score] = _p * (1 + ELITE_WIN3_BOOST)
                else:
                    _adj_sp[_score] = _p
            _s = sum(_adj_sp.values())
            poisson['score_probs'] = {k: round(v / _s * 100, 2) for k, v in _adj_sp.items()}
        
        combined_a = elo_exp_a * ELO_WEIGHT + poisson['win_a'] * POISSON_WEIGHT
        combined_draw = (1 - abs(elo_exp_a - 0.5)) * 0.15 + poisson['draw'] * POISSON_WEIGHT
        combined_b = (1 - elo_exp_a) * ELO_WEIGHT + poisson['win_b'] * POISSON_WEIGHT
        
        # v2.1修正: 大赛平局概率按轮次调整
        DRAW_BOOST_BY_ROUND = {
            'group_stage_round1': 0.08,   # v3.3: 首轮平局+8%(从15%下调，6/18平局率25%)
            'group_stage_round2': -0.10,  # 第2轮平局-10%(打出血性)
            'group_stage_round3': -0.05,  # 第3轮稍降
            'knockout_stage': 0.10        # v4.3: 淘汰赛平局+10%(从5%上调，R32 3场2平验证)
        }
        if tournament_round in DRAW_BOOST_BY_ROUND:
            draw_boost = DRAW_BOOST_BY_ROUND[tournament_round]
            combined_draw += draw_boost
            # 从胜和负中各抽取一半补给平局（正）或反向（负）
            combined_a -= draw_boost / 2
            combined_b -= draw_boost / 2
            combined_a = max(0.01, combined_a)
            combined_b = max(0.01, combined_b)
            combined_draw = max(0.05, min(0.90, combined_draw))
        
        # v4.13: 硬币抛掷死锁 → 平局概率上调(→点球标记)
        # 依据: 瑞士0-0哥伦比亚(Elo差6), 真正硬币抛掷+双防守稳健, 120min闷平→点球
        pens_likely = False
        if is_knockout and abs(elo_a - elo_b) < KO_COINFLIP_ELO_THRESHOLD:
            stats_a_def = self.team_stats.get(team_a, {}).get('avg_conceded', LEAGUE_AVG_GOALS)
            stats_b_def = self.team_stats.get(team_b, {}).get('avg_conceded', LEAGUE_AVG_GOALS)
            if stats_a_def <= KO_DEFENSIVE_BATTLE_CONCEDED and stats_b_def <= KO_DEFENSIVE_BATTLE_CONCEDED:
                pens_likely = True
                db = KO_PENS_LIKELY_DRAW_BOOST
                combined_draw += db
                combined_a -= db / 2
                combined_b -= db / 2
                combined_a = max(0.01, combined_a)
                combined_b = max(0.01, combined_b)
                combined_draw = max(0.05, min(0.90, combined_draw))
        
        total = combined_a + combined_draw + combined_b
        combined_a /= total; combined_draw /= total; combined_b /= total
        
        adj_a = combined_a + corrections.get('a', 0)
        adj_draw = combined_draw + corrections.get('draw', 0)
        adj_b = combined_b + corrections.get('b', 0)
        
        total2 = adj_a + adj_draw + adj_b
        adj_a /= total2; adj_draw /= total2; adj_b /= total2
        
        top_scores = sorted(poisson['score_probs'].items(), key=lambda x: x[1], reverse=True)[:6]  # v4.6: 5→6

        # v4.11: 让球风险标记 — 17场累计
        # 依据: 17场累计让球[-1]胜仅1/9(11.1%)，让球盘与真实赛果偏差极大
        ft_direction = 'a' if adj_a > adj_b else 'b' if adj_b > adj_a else 'draw'
        handicap_warnings = []
        if is_knockout:
            handicap_warnings.append('让球盘命中率极低(19场累计1/11=9.1%)，建议远离')
            if ft_direction != 'draw':
                handicap_warnings.append(f'FT方向偏向{team_a if ft_direction=="a" else team_b}，让球反向投注属高风险')

        # v4.11: 策略推荐标记 — 17场累计
        # 依据: 17场累计数据(R32 9场+R16 5场+R32d 3场)
        #   FT概率方向 13/17(76.5%) > 总进球Top2 14/17(82.4%) > 总进球Top1 10/17(58.8%)
        #   HT/FT Top1 9/17(52.9%) > 比分Top6 ~11/17(64.7%) > 让球[-1]W 1/9(11%)
        strategy_hints = []
        if is_knockout:
            strategy_hints.append('FT概率方向为主推(21场累计~81%)，EV价值方向不推荐')
            strategy_hints.append('总进球Top1为次推(21场累计~67%)，Top2覆盖达~62% — KO尾部分散后极端球增多, Top2覆盖下降')
            strategy_hints.append('HT/FT Top1命中率~52%(12/23)，可信度低，仅作辅助')
            strategy_hints.append('比分建议Top6覆盖(21场累计~52%)，弱队有S级巨星时注意覆盖客胜比分')
            strategy_hints.append('让球[-1]胜极低置信(1/11=9.1%)，禁止做串关断链腿')
            strategy_hints.append('v4.13: 硬币抛掷死锁(Elo差<50+双防守稳健xG-22%+平局+8%)+总进球尾部分散+25%+精英队buffer-4%')

        return {
            'team_a': team_a, 'team_b': team_b,
            'elo_a': elo_a, 'elo_b': elo_b,
            'elo_expected_a': round(elo_exp_a, 3),
            'xg_a': round(xg_a, 2), 'xg_b': round(xg_b, 2),
            'poisson': {
                'win_a': round(poisson['win_a'] * 100, 1),
                'draw': round(poisson['draw'] * 100, 1),
                'win_b': round(poisson['win_b'] * 100, 1),
                'score_probs': poisson['score_probs']
            },
            'combined': {
                'win_a': round(combined_a * 100, 1),
                'draw': round(combined_draw * 100, 1),
                'win_b': round(combined_b * 100, 1)
            },
            'final': {
                'win_a': round(adj_a * 100, 1),
                'draw': round(adj_draw * 100, 1),
                'win_b': round(adj_b * 100, 1)
            },
            'top_scores': top_scores,
            'corrections': corrections,
            'is_knockout': is_knockout,
            'tournament_round': tournament_round,
            # v4.7 增强字段
            'enhancements': {
                'host_effect_applied': is_knockout and (team_a in self._host_nations or team_b in self._host_nations),
                'superstar_effect_applied': is_knockout and (self._team_has_superstar(team_a) or self._team_has_superstar(team_b)),
                'superstar_upset_boost_applied': False,  # v4.10: 在expected_goals中计算后设为True
                'balanced_xg_boost_applied': is_knockout and abs(elo_a - elo_b) < KO_BALANCED_ELO_THRESHOLD and (max(xg_a, xg_b) / max(min(xg_a, xg_b), 0.01)) < KO_BALANCED_XG_RATIO,
                'coinfllip_deadlock_applied': is_knockout and abs(elo_a - elo_b) < KO_COINFLIP_ELO_THRESHOLD and (
                    self.team_stats.get(team_a, {}).get('avg_conceded', LEAGUE_AVG_GOALS) <= KO_DEFENSIVE_BATTLE_CONCEDED and
                    self.team_stats.get(team_b, {}).get('avg_conceded', LEAGUE_AVG_GOALS) <= KO_DEFENSIVE_BATTLE_CONCEDED
                ),
                'pens_likely': pens_likely,
                'high_elo_gap_buffer_applied': is_knockout and abs(elo_a - elo_b) > HIGH_ELO_GAP_THRESHOLD,
                'elite_win2_boost_applied': is_knockout and (elo_a >= ELITE_ELO_THRESHOLD or elo_b >= ELITE_ELO_THRESHOLD),
                'first_ko_debut_boost_applied': is_knockout and (team_a in self._first_ko_debut_teams or team_b in self._first_ko_debut_teams),
                'handicap_warnings': handicap_warnings,
                'strategy_hints': strategy_hints,
            }
        }
    
    # ============================================
    # v3.0 实时数据增强预测
    # ============================================
    
    def predict_with_live_data(self, team_a: str, team_b: str,
                               live_data: Dict = None,
                               corrections: Dict = None,
                               is_knockout: bool = False,
                               tournament_round: str = None) -> Dict:
        """结合实时伤停/阵容数据增强预测
        
        Args:
            team_a, team_b: 球队名
            live_data: LiveDataFetcher.get_full_match_data() 的输出
                {
                    'lineups': {...},
                    'injuries': {...},
                    'odds': {...}
                }
        
        增强逻辑:
        1. 伤停 → 调整 Elo (缺核心球员降低实力)
        2. 阵容 → 调整 xG (根据阵型和首发调整预期进球)
        3. 赔率 → 作为 corrections 参考
        """
        corrections = dict(corrections or {})
        
        if not live_data:
            return self.predict(team_a, team_b, corrections, is_knockout, tournament_round)
        
        injuries = live_data.get('injuries', {})
        lineups = live_data.get('lineups', {})
        
        # 步骤1: 伤病调整 Elo（临时覆盖实例属性）
        orig_elo_a = self.elo_ratings.get(team_a, 1500)
        orig_elo_b = self.elo_ratings.get(team_b, 1500)
        
        elo_a_adj, elo_b_adj = self._adjust_elo_for_injuries(team_a, team_b, injuries)
        
        # 临时替换 Elo
        self.elo_ratings[team_a] = elo_a_adj
        self.elo_ratings[team_b] = elo_b_adj
        
        # 步骤2: 阵容调整 xG 系数 → 注入为 corrections
        xg_mod_a, xg_mod_b = self._adjust_xg_for_lineups(team_a, team_b, lineups)
        
        # 进攻阵型倾向更高比分 → 调高双方胜率、降低平局
        if xg_mod_a > 1.0 and xg_mod_b < 1.0:
            corrections['a'] = corrections.get('a', 0) + 0.05
            corrections['draw'] = corrections.get('draw', 0) - 0.03
        elif xg_mod_b > 1.0 and xg_mod_a < 1.0:
            corrections['b'] = corrections.get('b', 0) + 0.05
            corrections['draw'] = corrections.get('draw', 0) - 0.03
        elif xg_mod_a > 1.0 and xg_mod_b > 1.0:
            corrections['a'] = corrections.get('a', 0) + 0.02
            corrections['b'] = corrections.get('b', 0) + 0.02
            corrections['draw'] = corrections.get('draw', 0) - 0.02
        
        # 步骤3: 执行预测（此时 Elo 已被临时替换）
        prediction = self.predict(team_a, team_b, corrections, is_knockout, tournament_round)
        
        # 步骤4: 恢复原始 Elo
        self.elo_ratings[team_a] = orig_elo_a
        self.elo_ratings[team_b] = orig_elo_b
        
        # 注入实时数据上下文
        prediction['live_data'] = {
            'used': True,
            'elo_adjusted': (elo_a_adj, elo_b_adj),
            'elo_original': (orig_elo_a, orig_elo_b),
            'xg_modifiers': (xg_mod_a, xg_mod_b),
            'injuries': {
                'available': injuries.get('available', False),
                'summary': injuries.get('impact_summary', '')
            },
            'lineups': {
                'available': lineups.get('available', False),
                'has_official': lineups.get('has_official', False)
            }
        }
        
        return prediction
    
    def _adjust_elo_for_injuries(self, team_a: str, team_b: str,
                                  injuries: Dict) -> Tuple[float, float]:
        """根据伤停信息调整 Elo 评级
        
        规则:
        - 每缺阵1人: Elo -15 (核心缺阵影响更大)
        - 每存疑1人: Elo -5
        - 最多影响 -60 Elo
        """
        elo_a = self.elo_ratings.get(team_a, 1500)
        elo_b = self.elo_ratings.get(team_b, 1500)
        
        if not injuries or not injuries.get('available'):
            return elo_a, elo_b
        
        # 主队伤病扣减
        impact_a = injuries.get('home_out_count', 0) * 15 + \
                   injuries.get('home_doubtful_count', 0) * 5
        impact_a = min(impact_a, 60)
        
        # 客队伤病扣减
        impact_b = injuries.get('away_out_count', 0) * 15 + \
                   injuries.get('away_doubtful_count', 0) * 5
        impact_b = min(impact_b, 60)
        
        return elo_a - impact_a, elo_b - impact_b
    
    def _adjust_xg_for_lineups(self, team_a: str, team_b: str,
                                lineups: Dict) -> Tuple[float, float]:
        """根据首发阵容调整 xG 系数
        
        规则:
        - 进攻阵型(4-3-3): xG +10%
        - 防守阵型(5-4-1/5-3-2): xG -10%
        - 标准阵型(4-4-2/4-2-3-1): 不变
        - 阵容不可用: 不影响
        """
        if not lineups or not lineups.get('available'):
            return 1.0, 1.0
        
        mod_a = self._formation_xg_modifier(
            (lineups.get('home') or {}).get('formation', '')
        )
        mod_b = self._formation_xg_modifier(
            (lineups.get('away') or {}).get('formation', '')
        )
        
        return mod_a, mod_b
    
    def _formation_xg_modifier(self, formation: str) -> float:
        """阵型 → xG 修正系数"""
        if not formation:
            return 1.0
        
        attacking = ['4-3-3', '3-4-3', '3-5-2', '4-2-4']
        defensive = ['5-4-1', '5-3-2', '4-5-1', '5-2-3']
        
        if any(f in formation for f in attacking):
            return 1.10
        if any(f in formation for f in defensive):
            return 0.90
        return 1.0
    
    # ============================================
    # v3.0 原始预测方法
    # ============================================

    def predict_with_consensus(self, team_a: str, team_b: str,
                                market_scores: Dict[str, int] = None,
                                market_totals: Dict[str, int] = None,
                                corrections: Dict = None,
                                is_knockout: bool = False,
                                tournament_round: str = None,
                                wld_direction: str = None,
                                injuries: Dict = None,
                                lineups: Dict = None,
                                use_h2h: bool = True) -> Dict:  # v4.10新增 / v4.16 H2H+injury threading
        """v3.4/v4.10/v4.16: 融合泊松概率 + H2H交锋史 + 市场共识的增强预测

        解决的问题：纯泊松比分选择至今0%命中率。泊松最高概率比分
        在世界杯中极少中奖。市场人气(participantCount)是有效的
        交叉验证信号。

        v4.10新增: wld_direction参数，当WLD方向已确定时(尤其低置信覆盖),
        比分选择优先从与该方向一致的选项中选，避免比分与WLD矛盾:
        - 'home' → 优先主场胜的比分 (如 1:0, 2:0, 2:1)
        - 'away' → 优先客场胜的比分 (如 0:1, 0:2, 1:2)
        - 'draw' → 优先平局比分 (如 1:1, 0:0, 2:2)
        - None  → 使用原有逻辑(不改变行为)

        v4.16新增: 将 H2H 交锋史与伤停/阵容信号注入 consensus 单点选择:
        - injuries/lineups 透传至 predict() → expected_goals(), 使 Round2 的
          H2H xG 接线 + 伤停/阵容 → xG 接线在共识路径真正生效
        - 用 H2H 调整 xG 重建泊松矩阵, 将其 top_scores 并入共识候选池,
          直接扩大单点选择可覆盖的比分线
        - 总进球选择用 H2H avg_total 与模型 xg_total 按 H2H_XG_BLEND 融合

        Args:
            team_a, team_b: 球队名
            market_scores: {score_option: participant_count, ...}
                例: {"1:0": 0, "2:0": 21, "3:0": 8, ...}
            market_totals: {total_option: participant_count, ...}
                例: {"0": 0, "1": 0, "2": 19, "3": 11, ...}
            corrections: 修正因子
            is_knockout: 是否淘汰赛
            tournament_round: 比赛轮次
            wld_direction: WLD方向 'home'/'away'/'draw'/None(不约束)
            injuries: 伤停字典 (透传 expected_goals)
            lineups: 阵容字典 (透传 expected_goals)
            use_h2h: 是否启用 H2H 交锋史增强 (默认 True)

        Returns:
            标准预测dict + consensus_scores和consensus_totals字段
        """
        # 步骤1: 基础预测 — 透传 injuries/lineups 使 expected_goals 的 H2H+伤停 xG 接线生效
        result = self.predict(team_a, team_b, corrections, is_knockout, tournament_round, injuries, lineups)

        # v4.16: H2H 信号提取（顺序无关）— 用于扩大共识候选池 + 总进球融合
        h2h = None
        h2h_scoreline = None
        h2h_total = None
        if use_h2h and self._h2h_enabled:
            h2h = self.get_head_to_head(team_a, team_b)
            if h2h and h2h.get('avg_a') is not None and h2h.get('avg_b') is not None:
                ga_h = int(round(h2h['avg_a']))
                gb_h = int(round(h2h['avg_b']))
                h2h_scoreline = f"{ga_h}:{gb_h}"
                h2h_total = h2h.get('avg_total')
                result['h2h_signal'] = {
                    'scoreline': h2h_scoreline,
                    'avg_a': h2h['avg_a'], 'avg_b': h2h['avg_b'],
                    'avg_total': h2h_total, 'meetings': h2h.get('meetings'),
                    'source': h2h.get('source'),
                }
                # 用 H2H 调整 xG 重建泊松矩阵 → 并入共识候选池
                xg_a_h = result['xg_a'] * (1 - H2H_XG_BLEND) + h2h['avg_a'] * H2H_XG_BLEND
                xg_b_h = result['xg_b'] * (1 - H2H_XG_BLEND) + h2h['avg_b'] * H2H_XG_BLEND
                pois_h = self.poisson_matrix(
                    xg_a_h, xg_b_h,
                    ko_dispersion=KO_TOTAL_GOALS_DISPERSION if is_knockout else 0.0
                )
                top_h = sorted(pois_h['score_probs'].items(), key=lambda x: x[1], reverse=True)[:6]
                seen = set()
                merged = []
                for sc, pr in list(result['top_scores']) + top_h:
                    sc_c = sc.replace('-', ':')
                    if sc_c not in seen:
                        seen.add(sc_c)
                        merged.append((sc_c, pr))
                result['h2h_xg'] = {'xg_a': round(xg_a_h, 2), 'xg_b': round(xg_b_h, 2)}
                top_scores_for_consensus = merged
            else:
                top_scores_for_consensus = [(s.replace('-', ':'), p) for s, p in result['top_scores']]
        else:
            top_scores_for_consensus = [(s.replace('-', ':'), p) for s, p in result['top_scores']]

        # 步骤2: 市场共识辅助选择最佳比分
        top_scores = top_scores_for_consensus
        result['consensus_candidate_pool'] = top_scores_for_consensus  # v4.16 debug: H2H扩展后的候选池
        best_score = None
        best_score_reason = ""
        candidate_scores = []  # v4.16: 提升至步骤2外层, 供H2H偏好覆盖使用

        if market_scores:
            # 将市场scores的key规范化（colon格式）
            norm_market = {k.replace('-', ':'): v for k, v in market_scores.items()}
            norm_market = {k: v for k, v in market_scores.items()}

            # v4.10: 比分解析辅助函数 — 判断比分方向
            def _score_matches_wld(score_str: str, wld: str) -> bool:
                """检查比分是否符合WLD方向
                score_str: "1:0" / "2:1" / "0:0" 等
                wld: 'home'/'away'/'draw'
                """
                try:
                    ga, gb = map(int, score_str.split(':'))
                    if wld == 'home':
                        return ga > gb
                    elif wld == 'away':
                        return ga < gb
                    elif wld == 'draw':
                        return ga == gb
                except:
                    pass
                return False

            # 从top_scores中找第一个存在于市场选项中的比分
            candidate_scores = []
            for score_str, prob in top_scores:
                score_str_colon = score_str.replace('-', ':')
                if score_str_colon in market_scores:
                    candidate_scores.append((score_str_colon, prob, market_scores.get(score_str_colon, 0)))

            # v4.10: 如果提供了WLD方向，优先过滤同方向比分
            wld_candidates = []
            if wld_direction in ('home', 'away', 'draw') and candidate_scores:
                for s, p, c in candidate_scores:
                    if _score_matches_wld(s, wld_direction):
                        wld_candidates.append((s, p, c))

                if wld_candidates:
                    # 有同方向候选 → 使用同方向候选中的最佳比分
                    s1, p1, c1 = wld_candidates[0]
                    if len(wld_candidates) >= 2:
                        s2, p2, c2 = wld_candidates[1]
                        if abs(p1 - p2) < 3.0 and c2 > c1:
                            (s1, p1, c1) = (s2, p2, c2)
                            best_score_reason = (
                                f"WLD一致性({wld_direction}): 泊松top2接近({p1:.1f}%vs{p2:.1f}%), "
                                f"选同方向中市场共识更高的{s1}({c1}人)"
                            )
                        else:
                            best_score_reason = (
                                f"WLD一致性({wld_direction}): 泊松top1={s1}({p1:.1f}%), "
                                f"与WLD方向一致"
                            )
                    else:
                        best_score_reason = (
                            f"WLD一致性({wld_direction}): 唯一同方向候选{s1}({p1:.1f}%)"
                        )
                    best_score = s1
                    result['score_pick'] = s1
                    result['score_confidence'] = p1
                    result['score_selection_note'] = best_score_reason
                    result['wld_consistency_applied'] = True
                else:
                    # v4.10: 没有同方向候选 → 回退到原逻辑但标注警告
                    result['wld_consistency_warning'] = (
                        f"WLD={wld_direction}但没有同方向比分可选, "
                        f"退回到原泊松选择逻辑"
                    )
                    # 继续使用以下原逻辑
                    wld_candidates = None  # 标记回退

            if best_score is None:
                # v4.10: 只有在best_score还未确定时才走原逻辑
                if len(candidate_scores) >= 2:
                    # v3.4核心逻辑: 当top2比分概率差<3%时，优先选市场共识高的
                    s1, p1, c1 = candidate_scores[0]
                    s2, p2, c2 = candidate_scores[1] if len(candidate_scores) > 1 else (None, 0, 0)

                    if abs(p1 - p2) < 3.0 and c2 > c1:
                        best_score = s2
                        best_score_reason = (
                            f"泊松top2接近({p1:.1f}%vs{p2:.1f}%)，"
                            f"市场共识{s2}({c2}人)>{s1}({c1}人)，选{s2}"
                        )
                        result['score_selection_note'] = best_score_reason
                        result['score_pick'] = best_score
                        result['score_confidence'] = p2
                    else:
                        best_score = s1
                        result['score_pick'] = s1
                        result['score_confidence'] = p1
                elif len(candidate_scores) == 1:
                    best_score = candidate_scores[0][0]
                    result['score_pick'] = best_score
                    result['score_confidence'] = candidate_scores[0][1]
                elif len(top_scores) > 0:
                    # 所有top scores都不在市场选项中 → 选市场共识最高的
                    if market_scores:
                        best_by_market = max(market_scores.items(), key=lambda x: x[1])
                        best_score = best_by_market[0]
                        result['score_selection_note'] = (
                            f"泊松top_scores均不在市场选项中，"
                            f"跟随市场最高共识{best_score}({best_by_market[1]}人)"
                        )
                        result['score_pick'] = best_score
                        result['score_confidence'] = 0
        else:
            # 无市场数据，退回到原始top_scores[0]
            if top_scores:
                best_score = top_scores[0][0].replace('-', ':')
                result['score_pick'] = best_score
                result['score_confidence'] = top_scores[0][1]

        # v4.16: H2H 偏好覆盖（仅在有市场共识交叉验证、且未触发WLD一致性时生效）—
        # 当 H2H 隐含比分线在候选池中、且与当前pick泊松概率接近(≤4%)且市场参与
        # 人数不低于当前pick的60%时, 优先H2H线。这是把H2H喂进共识单点选择的关键机制。
        if (h2h_scoreline and best_score and h2h_scoreline != best_score
                and h2h and candidate_scores
                and not result.get('wld_consistency_applied')):
            h2h_cand = next((c for c in candidate_scores if c[0] == h2h_scoreline), None)
            if h2h_cand:
                s_h, p_h, c_h = h2h_cand
                cur = next((c for c in candidate_scores if c[0] == best_score), None)
                if cur:
                    s_c, p_c, c_c = cur
                    if abs(p_h - p_c) <= 4.0 and c_h >= c_c * 0.6:
                        best_score = s_h
                        result['score_pick'] = s_h
                        result['score_confidence'] = p_h
                        result['score_selection_note'] = (
                            f"H2H偏好覆盖: 历史交锋隐含{h2h_scoreline}"
                            f"(avg {h2h['avg_a']:.2f}/{h2h['avg_b']:.2f}, n={h2h.get('meetings')}), "
                            f"泊松{p_h:.1f}%≈当前pick{p_c:.1f}%且市场{c_h}≥{c_c*0.6:.0f}, 优先H2H线"
                        )
                        result['h2h_override_applied'] = True

        # 步骤3: 市场共识辅助选择总进球
        if market_totals:
            xg_total = result['xg_a'] + result['xg_b']
            # v4.16: H2H avg_total 与模型 xg_total 按 H2H_XG_BLEND 融合
            if h2h_total is not None:
                xg_total = xg_total * (1 - H2H_XG_BLEND) + h2h_total * H2H_XG_BLEND
                result['h2h_total_blend'] = round(xg_total, 2)
            # 计算泊松各总进球概率
            from math import exp, factorial
            poisson_totals = {}
            for k_str in market_totals:
                if k_str == '7+':
                    poisson_totals['7+'] = 1 - sum(
                        (xg_total ** k) * exp(-xg_total) / factorial(k) for k in range(7)
                    ) * 100
                else:
                    k = int(k_str)
                    poisson_totals[k_str] = ((xg_total ** k) * exp(-xg_total) / factorial(k)) * 100

            # 找泊松最高和市场最高
            best_poisson = max(poisson_totals, key=poisson_totals.get)
            best_market = max(market_totals, key=market_totals.get)

            result['consensus_totals'] = {
                'xg_total': round(xg_total, 2),
                'poisson_top': (best_poisson, round(poisson_totals[best_poisson], 1)),
                'market_top': (best_market, market_totals[best_market]),
                'poisson_distribution': {k: round(v, 1) for k, v in poisson_totals.items()},
                'market_distribution': market_totals
            }

            # v3.4: 如果市场共识与泊松top不同且市场人数明显更多，跟市场
            if best_poisson != best_market:
                market_count = market_totals.get(best_market, 0)
                poisson_count = market_totals.get(best_poisson, 0)
                if market_count > poisson_count * 3:
                    result['total_pick'] = best_market
                    result['total_confidence'] = min(25, poisson_totals.get(best_market, 0))
                    result['total_selection_note'] = (
                        f"市场共识{best_market}({market_count}人)>>"
                        f"泊松top{best_poisson}({poisson_count}人,{poisson_totals[best_poisson]:.1f}%)，"
                        f"跟随市场"
                    )
                else:
                    result['total_pick'] = best_poisson
                    result['total_confidence'] = poisson_totals[best_poisson]
            else:
                result['total_pick'] = best_poisson
                result['total_confidence'] = poisson_totals[best_poisson]

        return result
    
    def monte_carlo_path(self, team: str, stages: List[Dict], 
                         simulations: int = 100000) -> Dict:
        import random
        results = {i: 0 for i in range(len(stages) + 1)}
        results[0] = simulations
        
        for _ in range(simulations):
            current = True
            for stage_idx, stage in enumerate(stages):
                if not current: break
                if random.random() < stage['win_prob']:
                    results[stage_idx + 1] += 1
                else:
                    current = False
        
        return {
            'team': team,
            'simulations': simulations,
            'probabilities': {
                f'stage_{i}': round(results[i] / simulations * 100, 1)
                for i in range(len(stages) + 1)
            }
        }
    
    @staticmethod
    def odds_to_probability(odds_a: float, odds_draw: float, odds_b: float) -> Dict:
        raw_a = 1 / odds_a; raw_d = 1 / odds_draw; raw_b = 1 / odds_b
        total = raw_a + raw_d + raw_b
        vig = total - 1
        return {
            'win_a': round(raw_a / total * 100, 1),
            'draw': round(raw_d / total * 100, 1),
            'win_b': round(raw_b / total * 100, 1),
            'vig': round(vig * 100, 1)
        }
    
    def value_detection(self, model_prob: Dict, market_prob: Dict, 
                        threshold: float = 3.0) -> Dict:
        edges = {}
        for key in ['win_a', 'draw', 'win_b']:
            model = model_prob.get(key, 0)
            market = market_prob.get(key, 0)
            edge = model - market
            edges[key] = {
                'model': model, 'market': market,
                'edge': round(edge, 1),
                'is_value': abs(edge) >= threshold
            }
        return edges
    
    @staticmethod
    def kelly(prob: float, odds: float, fraction: float = 0.5) -> float:
        full_kelly = (prob * odds - 1) / (odds - 1)
        return max(0, full_kelly * fraction)
    
    # ============================================
    # v3.2 爆冷分析模块 (来自 football-match-analysis v2.1)
    # ============================================
    
    def upset_analysis(self, team_a: str, team_b: str,
                       match_context: Dict = None,
                       tournament_round: str = None) -> Dict:
        """爆冷分析 — 基于三层判据：风格克制、状态变量、赛制红利
        
        Args:
            team_a, team_b: 球队名
            match_context: 比赛上下文
                - is_first_match: 小组首轮
                - is_last_group_match: 末轮
                - rotation_risk: 强队可能轮换
                - expansion_format: 48队扩军赛制
                - internal_strife: 强队存在内讧
                - key_injury: 强队核心伤缺
                - slow_starter: 强队历来慢热
            tournament_round: 比赛轮次 (group_stage_round1/2/3, knockout_stage)
        
        Returns:
            爆冷分析报告，含基础/调整后概率、修正详情、等级判定
        """
        match_context = match_context or {}
        
        # 确定强队和弱队（基于Elo）
        elo_a = self.elo_ratings.get(team_a, 1500)
        elo_b = self.elo_ratings.get(team_b, 1500)
        favorite = team_a if elo_a >= elo_b else team_b
        underdog = team_b if favorite == team_a else team_a
        elo_gap = abs(elo_a - elo_b)
        
        # 基础预测
        base_pred = self.predict(team_a, team_b, tournament_round=tournament_round)
        underdog_key = 'win_b' if favorite == team_a else 'win_a'
        draw_key = 'draw'
        base_upset_prob = base_pred['final'][underdog_key] / 100.0
        base_draw_prob = base_pred['final'][draw_key] / 100.0
        
        # 三层爆冷修正
        corrections = {'style': 0, 'status': 0, 'format': 0}
        
        # 1. 风格克制修正
        stats_fav = self.team_stats.get(favorite, {
            'avg_goals': LEAGUE_AVG_GOALS, 'avg_conceded': LEAGUE_AVG_GOALS
        })
        stats_und = self.team_stats.get(underdog, {
            'avg_goals': LEAGUE_AVG_GOALS, 'avg_conceded': LEAGUE_AVG_GOALS
        })
        
        # 攻强守弱（场均进球>1.8且失球>0.9）遇铁桶（弱队失球<0.9）
        if stats_fav['avg_goals'] > 1.8 and stats_fav['avg_conceded'] > 0.9 \
           and stats_und['avg_conceded'] < 0.9:
            corrections['style'] += 0.04
        
        # 弱队反击型 vs 控球型强队
        if stats_und['avg_goals'] > 1.3 and stats_und['avg_conceded'] < 1.0 \
           and stats_fav['avg_goals'] > 2.0:
            corrections['style'] += 0.03
        
        # 2. 状态变量修正
        if match_context.get('internal_strife'):
            corrections['status'] -= 0.04
        if match_context.get('key_injury'):
            corrections['status'] -= 0.03
        if match_context.get('slow_starter'):
            corrections['status'] += 0.02
        
        # 3. 赛制红利修正
        if match_context.get('is_first_match'):
            corrections['format'] += 0.03
        if match_context.get('rotation_risk'):
            corrections['format'] += 0.06
        if match_context.get('is_last_group_match'):
            corrections['format'] += 0.02
        if match_context.get('expansion_format'):
            corrections['format'] += 0.03
        
        total_correction = corrections['style'] + corrections['status'] + corrections['format']
        
        adjusted_upset = min(0.95, base_upset_prob + total_correction)
        adjusted_draw = min(0.50, base_draw_prob + abs(corrections['status']) * 0.3)
        
        # 爆冷等级判定
        upset_combined = adjusted_upset + adjusted_draw * 0.5
        if upset_combined >= 0.40:
            tier = "Tier 1 - 高概率爆冷"
        elif upset_combined >= 0.30:
            tier = "Tier 2 - 中概率爆冷"
        elif upset_combined >= 0.20:
            tier = "Tier 3 - 值得盯的暗冷"
        else:
            tier = "常规 - 爆冷概率低"
        
        return {
            'favorite': favorite,
            'underdog': underdog,
            'elo_gap': elo_gap,
            'base_upset_prob': round(base_upset_prob * 100, 1),
            'base_draw_prob': round(base_draw_prob * 100, 1),
            'corrections': {k: round(v * 100, 1) for k, v in corrections.items()},
            'total_correction': round(total_correction * 100, 1),
            'adjusted_upset_prob': round(adjusted_upset * 100, 1),
            'adjusted_draw_prob': round(adjusted_draw * 100, 1),
            'upset_combined': round(upset_combined * 100, 1),
            'tier': tier,
            'key_factors': [f for f, v in corrections.items() if abs(v) >= 0.01]
        }
    
    # ============================================
    # v3.0 自我进化方法
    # ============================================
    
    def update_elo(self, team_a: str, team_b: str, result_a: float,
                   k_factor: float = 32) -> Tuple[float, float]:
        """赛后Elo动态更新
        
        Args:
            team_a: 主队名
            team_b: 客队名
            result_a: 主队赛果 (1=胜, 0.5=平, 0=负)
            k_factor: K值，世界杯淘汰赛可用K=48
        
        Returns:
            (新elo_a, 新elo_b)
        """
        elo_a = self.elo_ratings.get(team_a, 1500)
        elo_b = self.elo_ratings.get(team_b, 1500)
        
        expected_a = self.elo_expected(elo_a, elo_b)
        
        new_elo_a = elo_a + k_factor * (result_a - expected_a)
        new_elo_b = elo_b + k_factor * ((1 - result_a) - (1 - expected_a))
        
        self.elo_ratings[team_a] = round(new_elo_a)
        self.elo_ratings[team_b] = round(new_elo_b)
        
        return round(new_elo_a), round(new_elo_b)
    
    def calibrate_from_result(self, team_a: str, team_b: str,
                              actual_score: Tuple[int, int],
                              prediction: Dict) -> Dict:
        """赛后校准：对比预测与实际结果，计算偏差
        
        Returns:
            {
                'direction_correct': bool,    # 方向预测是否正确
                'score_error': float,         # 比分误差(总进球差)
                'xg_error': float,            # xG误差
                'calibration_note': str       # 校准建议
            }
        """
        ga, gb = actual_score
        
        # 方向对比
        if ga > gb:
            actual_winner = 'a'
        elif gb > ga:
            actual_winner = 'b'
        else:
            actual_winner = 'draw'
        
        pred_final = prediction['final']
        predicted_winner = max(pred_final, key=pred_final.get)
        # 将final的key映射为方向
        pred_map = {'win_a': 'a', 'win_b': 'b', 'draw': 'draw'}
        predicted_dir = pred_map.get(predicted_winner, 'draw')
        
        direction_correct = actual_winner == predicted_dir
        
        # 比分误差
        pred_xg = prediction['xg_a'] + prediction['xg_b']
        actual_goals = ga + gb
        score_error = abs(pred_xg - actual_goals)
        
        # xG误差
        xg_error_a = abs(prediction['xg_a'] - ga)
        xg_error_b = abs(prediction['xg_b'] - gb)
        xg_error = (xg_error_a + xg_error_b) / 2
        
        # 校准建议
        notes = []
        if not direction_correct:
            notes.append(f"方向预测错误：预测{predicted_dir}，实际{actual_winner}")
        if score_error > 1.5:
            notes.append(f"总进球偏差较大({score_error:.1f}球)，需检查攻防系数")
        if xg_error_a > 1.0 or xg_error_b > 1.0:
            notes.append(f"xG偏差显著(A:{xg_error_a:.1f}/B:{xg_error_b:.1f})，首轮修正因子可能需要调整")
        
        return {
            'direction_correct': direction_correct,
            'actual_winner': actual_winner,
            'predicted_winner': predicted_dir,
            'score_error': round(score_error, 2),
            'xg_error': round(xg_error, 2),
            'calibration_note': '; '.join(notes) if notes else '预测准确，无需校准'
        }
    
    def save_elo_data(self, data_dir: str):
        """保存Elo数据到文件（进化后持久化）"""
        elo_path = os.path.join(data_dir, 'elo_ratings.json')
        with open(elo_path, 'w', encoding='utf-8') as f:
            json.dump(self.elo_ratings, f, ensure_ascii=False, indent=2)
    
    def save_team_stats(self, data_dir: str):
        """保存球队统计数据到文件"""
        stats_path = os.path.join(data_dir, 'team_stats.json')
        with open(stats_path, 'w', encoding='utf-8') as f:
            json.dump(self.team_stats, f, ensure_ascii=False, indent=2)
    
    def update_team_stats(self, team: str, goals_for: int, goals_against: int):
        """赛后更新球队攻防统计（滑动平均）"""
        if team not in self.team_stats:
            self.team_stats[team] = {'avg_goals': LEAGUE_AVG_GOALS, 'avg_conceded': LEAGUE_AVG_GOALS}
        
        stats = self.team_stats[team]
        # 指数滑动平均，权重0.3为新数据
        alpha = 0.3
        stats['avg_goals'] = round(stats['avg_goals'] * (1 - alpha) + goals_for * alpha, 2)
        stats['avg_conceded'] = round(stats['avg_conceded'] * (1 - alpha) + goals_against * alpha, 2)


if __name__ == "__main__":
    engine = FootballPredictionEngine(data_dir=os.path.join(os.path.dirname(__file__), '..', 'data'))
    print(f"已加载 {len(engine.elo_ratings)} 支球队Elo数据")
    print(f"已加载 {len(engine.team_stats)} 支球队攻防数据")

    # 爆冷分析快速测试
    test_matches = [
        ("巴西", "摩洛哥", {"is_first_match": True, "expansion_format": True}),
        ("荷兰", "日本", {"is_first_match": True, "expansion_format": True}),
        ("法国", "塞内加尔", {"is_first_match": True, "expansion_format": True, "slow_starter": True}),
        ("比利时", "伊朗", {"expansion_format": True}),
        ("挪威", "法国", {"is_last_group_match": True, "rotation_risk": True, "expansion_format": True}),
        ("乌拉圭", "西班牙", {"is_last_group_match": True, "expansion_format": True}),
        ("英格兰", "加纳", {"expansion_format": True, "slow_starter": True}),
        ("德国", "厄瓜多尔", {"is_last_group_match": True, "expansion_format": True}),
        ("美国", "土耳其", {"is_last_group_match": True, "expansion_format": True}),
        ("葡萄牙", "哥伦比亚", {"is_last_group_match": True, "expansion_format": True}),
    ]
    print("\n=== 2026世界杯爆冷分析测试 ===\n")
    for fav, und, ctx in test_matches:
        result = engine.upset_analysis(fav, und, ctx)
        print(f"{result['favorite']} vs {result['underdog']} | Elo差{result['elo_gap']} | "
              f"基础爆冷{result['base_upset_prob']}% → 调整后{result['adjusted_upset_prob']}% | "
              f"修正: 风格{result['corrections']['style']}% 状态{result['corrections']['status']}% 赛制{result['corrections']['format']}% | "
              f"{result['tier']}")
