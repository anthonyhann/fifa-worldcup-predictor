"""
足球预测引擎 v3.2 — FIFA世界杯预测计算器
模块: Elo评级 + 泊松回归 + 蒙特卡洛模拟 + 赔率分析 + Kelly仓位 + 自我进化 + 实时数据
v1.1修正: 单场决赛极端防守系数均值回归30%
v2.0修正: 大赛首轮xG修正(2026-06-16复盘，4场全平验证)
v2.1修正: 轮次自适应(2026-06-17复盘，4场3穿盘反向验证)
  - 取消统一首轮修正
  - 新增 group_stage_round2: 强队反弹系数1.10(打出血性)
  - 新增 group_stage_round3: 接近常规状态
  - 新增 knockout_stage: 强队稍弱队0.95(淘汰赛防守)
v3.0新增: Elo动态更新 + 赛后校准 + 进化日志接口
v3.1新增: 实时数据集成(阵容/伤停/赔率)
v3.2新增: 爆冷分析模块(三层判据) + 轮次自适应全面进化
"""

import math
import json
import os
from typing import Dict, List, Tuple, Optional

# ============================================
# 核心参数
# ============================================
LEAGUE_AVG_GOALS = 1.35
ELO_WEIGHT = 0.30
POISSON_WEIGHT = 0.70
DEFENSE_REGRESSION = 0.30
DEFENSE_EXTREME_THRESHOLD = 0.5


class FootballPredictionEngine:
    """足球比赛预测引擎 v3.2+"""
    
    def __init__(self, data_dir: str = None):
        self.elo_ratings = {}
        self.team_stats = {}
        self.prediction_log = []
        # v4.0: 可被进化引擎注入的自定义轮次系数
        self._round_coefficients = None
        
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
    
    def elo_expected(self, elo_a: float, elo_b: float) -> float:
        return 1 / (1 + 10 ** ((elo_b - elo_a) / 400))
    
    @staticmethod
    def poisson_prob(lam: float, k: int) -> float:
        return (lam ** k) * math.exp(-lam) / math.factorial(k)
    
    def expected_goals(self, team_a: str, team_b: str, 
                       is_knockout: bool = False,
                       tournament_round: str = None) -> Tuple[float, float]:
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
                    'fav_discount': 0.50,    # 首轮强队折半(谨慎/未热身)
                    'underdog_boost': 0.40,  # 首轮弱队加成(状态佳)
                    'draw_boost': 0.15       # 首轮平局上调
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
                    'draw_boost': 0.05       # 淘汰赛更可能平
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
        return xg_a, xg_b
    
    def poisson_matrix(self, xg_a: float, xg_b: float, max_goals: int = 7) -> Dict:
        win_a = draw = win_b = 0.0
        score_probs = {}
        
        for ga in range(max_goals):
            for gb in range(max_goals):
                p = self.poisson_prob(xg_a, ga) * self.poisson_prob(xg_b, gb)
                score_probs[f"{ga}-{gb}"] = round(p * 100, 2)
                if ga > gb: win_a += p
                elif ga == ga: draw += p if ga == gb else 0
                else: win_b += p
        
        # 修复draw计算
        win_a = draw = win_b = 0.0
        for ga in range(max_goals):
            for gb in range(max_goals):
                p = self.poisson_prob(xg_a, ga) * self.poisson_prob(xg_b, gb)
                if ga > gb: win_a += p
                elif ga == gb: draw += p
                else: win_b += p
        
        return {'win_a': win_a, 'draw': draw, 'win_b': win_b, 'score_probs': score_probs}
    
    def predict(self, team_a: str, team_b: str,
                corrections: Dict = None, is_knockout: bool = False,
                tournament_round: str = None) -> Dict:
        corrections = corrections or {}
        
        elo_a = self.elo_ratings.get(team_a, 1500)
        elo_b = self.elo_ratings.get(team_b, 1500)
        elo_exp_a = self.elo_expected(elo_a, elo_b)
        
        xg_a, xg_b = self.expected_goals(team_a, team_b, is_knockout, tournament_round)
        poisson = self.poisson_matrix(xg_a, xg_b)
        
        combined_a = elo_exp_a * ELO_WEIGHT + poisson['win_a'] * POISSON_WEIGHT
        combined_draw = (1 - abs(elo_exp_a - 0.5)) * 0.15 + poisson['draw'] * POISSON_WEIGHT
        combined_b = (1 - elo_exp_a) * ELO_WEIGHT + poisson['win_b'] * POISSON_WEIGHT
        
        # v2.1修正: 大赛平局概率按轮次调整
        DRAW_BOOST_BY_ROUND = {
            'group_stage_round1': 0.15,  # 首轮平局+15%
            'group_stage_round2': -0.10, # 第2轮平局-10%(打出血性)
            'group_stage_round3': -0.05, # 第3轮稍降
            'knockout_stage': 0.05       # 淘汰赛平局+5%
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
        
        total = combined_a + combined_draw + combined_b
        combined_a /= total; combined_draw /= total; combined_b /= total
        
        adj_a = combined_a + corrections.get('a', 0)
        adj_draw = combined_draw + corrections.get('draw', 0)
        adj_b = combined_b + corrections.get('b', 0)
        
        total2 = adj_a + adj_draw + adj_b
        adj_a /= total2; adj_draw /= total2; adj_b /= total2
        
        top_scores = sorted(poisson['score_probs'].items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            'team_a': team_a, 'team_b': team_b,
            'elo_a': elo_a, 'elo_b': elo_b,
            'elo_expected_a': round(elo_exp_a, 3),
            'xg_a': round(xg_a, 2), 'xg_b': round(xg_b, 2),
            'poisson': {
                'win_a': round(poisson['win_a'] * 100, 1),
                'draw': round(poisson['draw'] * 100, 1),
                'win_b': round(poisson['win_b'] * 100, 1)
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
            'tournament_round': tournament_round
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
