"""
自我进化引擎 v2.1 — FIFA世界杯预测计算器
功能：
  1. 追踪预测准确率变化趋势
  2. 基于复盘数据自动校准核心参数（轮次自适应）
  3. 自适应Elo K值调整
  4. 轮次系数动态优化 (R1/R2/R3/KO)
  5. 回测验证 — 防止过度拟合
  6. 进化事件日志

v2.0 进化 (2026-06-17)：基于 football-match-analysis 的迭代经验
  - 从单参数校准进化为轮次自适应多参数系统
  - 新增回测验证层，防止v2.0→v2.1式的过拟合事故

v2.1 进化 (2026-07-03)：修复准确率计算污染bug
  - 修复: compute_accuracy_metrics() 使用 hit/is_correct 替代 actual_winner/predicted_winner
  - 根因: review_log 中 290/291 条缺少 actual_winner/predicted_winner → None==None→True → 98.6%虚高
  - 修复: calibrate_elo_weight/calibrate_round_coefficients/calibrate_k_factor/backtest 全部同步修复
  - 重置被污染参数: K_FACTOR 64→36, ELO_WEIGHT 0.15→0.30, KO系数回归合理值
"""

import json
import os
import math
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from prediction_engine import FootballPredictionEngine, LEAGUE_AVG_GOALS, ELO_WEIGHT, POISSON_WEIGHT


class EvolutionEngine:
    """自我进化引擎 v2.0 — 轮次自适应 + 回测验证 + 过拟合防御"""

    def __init__(self, skill_dir: str):
        self.skill_dir = skill_dir
        self.data_dir = os.path.join(skill_dir, 'data')
        self.logs_dir = os.path.join(skill_dir, 'logs')
        self.evolution_state_path = os.path.join(self.logs_dir, 'evolution_state.json')
        self.engine = FootballPredictionEngine(data_dir=self.data_dir)
        self.state = self._load_state()

    def _load_state(self) -> Dict:
        """加载进化状态"""
        if os.path.exists(self.evolution_state_path):
            with open(self.evolution_state_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            'version': '2.0',
            'created_at': datetime.now().isoformat(),
            'evolution_count': 0,
            'param_history': [],
            'accuracy_timeline': [],
            'overfitting_warnings': [],
            'current_params': {
                'LEAGUE_AVG_GOALS': LEAGUE_AVG_GOALS,
                'ELO_WEIGHT': 0.30,
                'POISSON_WEIGHT': 0.70,
                'K_FACTOR': 36,  # v2.1: 基于真实 35-36% 准确率校准
                'DEFENSE_REGRESSION': 0.30,
                'VALUE_THRESHOLD': 3.0
            },
            # v2.0: 轮次自适应参数
            'round_coefficients': {
                'group_stage_round1': {
                    'fav_discount': 0.50,
                    'underdog_boost': 0.40,
                    'draw_boost': 0.15
                },
                'group_stage_round2': {
                    'fav_discount': 1.10,
                    'underdog_boost': -0.20,
                    'draw_boost': -0.10
                },
                'group_stage_round3': {
                    'fav_discount': 1.00,
                    'underdog_boost': 0.00,
                    'draw_boost': -0.05
                },
                'knockout_stage': {
                    'fav_discount': 0.95,
                    'underdog_boost': 0.10,
                    'draw_boost': 0.05
                }
            }
        }

    def _save_state(self):
        """保存进化状态"""
        os.makedirs(self.logs_dir, exist_ok=True)
        with open(self.evolution_state_path, 'w', encoding='utf-8') as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    # ============================================
    # v2.1 修复: 统一处理旧/新格式的 ground truth
    # ============================================

    @staticmethod
    def _get_correct(review: Dict) -> Optional[bool]:
        """从 review 中提取是否预测正确（兼容旧/新格式）

        旧格式: {'hit': True/False}
        新格式: {'is_correct': True/False}
        """
        for key in ('hit', 'is_correct'):
            val = review.get(key)
            if val is not None:
                return val
        return None

    @staticmethod
    def _get_type(review: Dict) -> str:
        """从 review 中提取预测类型"""
        return review.get('type', review.get('market_type', ''))

    @staticmethod
    def _is_win_lose_draw(review: Dict) -> bool:
        """判断是否为胜平负类型"""
        t = EvolutionEngine._get_type(review)
        return t in ('win_lose_draw',)

    @staticmethod
    def _has_ground_truth(review: Dict) -> bool:
        """判断 review 是否包含真实标注数据"""
        return EvolutionEngine._get_correct(review) is not None

    def _filter_reviews_with_truth(self, reviews: List[Dict] = None) -> List[Dict]:
        """过滤出有真实标注数据的 review"""
        if reviews is None:
            reviews = self.load_reviews()
        return [r for r in reviews if self._has_ground_truth(r)]

    def load_reviews(self) -> List[Dict]:
        """加载复盘数据"""
        log_path = os.path.join(self.logs_dir, 'review_log.jsonl')
        if not os.path.exists(log_path):
            return []
        reviews = []
        with open(log_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    reviews.append(json.loads(line))
        return reviews

    def load_reviews_by_round(self) -> Dict[str, List[Dict]]:
        """按轮次分组复盘数据"""
        reviews = self.load_reviews()
        by_round = {}
        for r in reviews:
            rd = r.get('calibration', {}).get('tournament_round',
                   r.get('tournament_round', 'unknown'))
            if rd not in by_round:
                by_round[rd] = []
            by_round[rd].append(r)
        return by_round

    # ============================================
    # 准确率追踪
    # ============================================

    def compute_accuracy_metrics(self, reviews: List[Dict] = None) -> Dict:
        """计算各种准确率指标（v2.1 修复：使用 hit/is_correct 替代 actual_winner/predicted_winner）"""
        if reviews is None:
            reviews = self.load_reviews()

        # v2.1: 只统计有真实标注的条目
        valid = self._filter_reviews_with_truth(reviews)
        if not valid:
            return {'total': 0, 'message': '无复盘数据'}

        total = len(valid)
        correct = sum(1 for r in valid if self._get_correct(r))

        # 滑动窗口（最近20场）
        window = min(20, total)
        recent = valid[-window:]
        recent_correct = sum(1 for r in recent if self._get_correct(r))

        # 趋势检测
        trend = 'stable'
        if total >= 10:
            half = total // 2
            first_half = valid[:half]
            second_half = valid[half:]
            first_acc = sum(1 for r in first_half if self._get_correct(r)) / max(len(first_half), 1)
            second_acc = sum(1 for r in second_half if self._get_correct(r)) / max(len(second_half), 1)
            diff = second_acc - first_acc
            if diff > 0.05:
                trend = 'improving'
            elif diff < -0.05:
                trend = 'declining'

        # 按类型准确率
        by_type = {}
        for r in valid:
            t = self._get_type(r)
            if not t:
                t = 'unknown'
            if t not in by_type:
                by_type[t] = {'total': 0, 'correct': 0}
            by_type[t]['total'] += 1
            if self._get_correct(r):
                by_type[t]['correct'] += 1

        type_accuracy = {}
        for t, v in by_type.items():
            type_accuracy[t] = round(v['correct'] / v['total'] * 100, 1) if v['total'] > 0 else 0

        return {
            'total': total,
            'overall_accuracy': round(correct / total * 100, 1) if total > 0 else 0,
            'recent_accuracy': round(recent_correct / window * 100, 1) if window > 0 else 0,
            'window_size': window,
            'trend': trend,
            'by_type': type_accuracy,
            'by_round': {},  # v2.1: 暂不可用，review_log 无 tournament_round 字段
            'grade_distribution': self._compute_grades(reviews)
        }

    def _compute_grades(self, reviews: List[Dict]) -> Dict:
        grades = {'A': 0, 'B': 0, 'C': 0, 'D': 0, 'F': 0}
        for r in reviews:
            scores = r.get('scores', {})
            g = scores.get('grade', 'F')[0]
            if g in grades:
                grades[g] += 1
        return grades

    # ============================================
    # 参数自动校准 — 轮次自适应
    # ============================================

    def calibrate_elo_weight(self, reviews: List[Dict]) -> float:
        """v2.1 修复: 基于胜平负类型准确率调整 Elo 权重

        胜平负准确率高 → Elo有效 → 保持或提高权重
        胜平负准确率低 → 泊松更有效 → 降低 Elo 权重
        """
        valid = self._filter_reviews_with_truth(reviews)
        wld = [r for r in valid if self._is_win_lose_draw(r)]

        if len(wld) < 3:
            return self.state['current_params']['ELO_WEIGHT']

        wld_acc = sum(1 for r in wld if self._get_correct(r)) / len(wld)
        current = self.state['current_params']['ELO_WEIGHT']

        # 胜平负准确率 >70% → Elo表现好，保持或微涨
        if wld_acc > 0.70:
            new_weight = min(0.50, current + 0.03)
        # 胜平负准确率 <40% → Elo表现差，降权重
        elif wld_acc < 0.40:
            new_weight = max(0.15, current - 0.05)
        # 中间区间 → 保持
        else:
            new_weight = current

        return round(new_weight, 2)

    def calibrate_round_coefficients(self, reviews: List[Dict]) -> Dict[str, Dict]:
        """v2.1 修复: 基于可用数据（胜平负/比分/总进球准确率）校准轮次系数

        使用 hit/is_correct 替代 actual_winner/predicted_winner/xG误差。
        胜平负准确率 → 调节 fav_discount
        比分准确率 → 调节 underdog_boost（比分预测好=弱队xG被合理估计）
        平局频率 → 调节 draw_boost
        """
        valid = self._filter_reviews_with_truth(reviews)
        if len(valid) < 3:
            return dict(self.state['round_coefficients'])

        # 按预测类型分组
        wld = [r for r in valid if self._get_type(r) == 'win_lose_draw']
        score = [r for r in valid if self._get_type(r) == 'score']
        goals = [r for r in valid if self._get_type(r) == 'total_goals']

        # 计算各类型准确率
        wld_acc = sum(1 for r in wld if self._get_correct(r)) / max(len(wld), 1)
        score_acc = sum(1 for r in score if self._get_correct(r)) / max(len(score), 1)
        goals_acc = sum(1 for r in goals if self._get_correct(r)) / max(len(goals), 1)

        # 只校准 KO 阶段（当前活跃轮次）
        new_coefficients = {}
        for rd_name in self.state['round_coefficients']:
            old = self.state['round_coefficients'][rd_name]
            new = dict(old)

            if rd_name == 'knockout_stage' and len(wld) >= 3:
                # 胜平负准确率驱动 fav_discount
                if wld_acc > 0.75:
                    # 预测很准，当前系数合适，微调趋近
                    new['fav_discount'] = min(1.05, old['fav_discount'] + 0.02)
                elif wld_acc < 0.50:
                    # 预测不准，系数可能过高或过低
                    # 检查 pick 分布来推断方向
                    picks = [r.get('pick', '') for r in wld]
                    home_wins = sum(1 for p in picks if p == '主胜')
                    if home_wins > len(picks) * 0.6:
                        # 过度预测主胜 → 降低系数
                        new['fav_discount'] = max(0.70, old['fav_discount'] - 0.05)
                    else:
                        new['fav_discount'] = min(1.05, old['fav_discount'] + 0.03)

                # 比分准确率驱动 underdog_boost
                if len(score) >= 3 and score_acc < 0.15:
                    # 比分预测差 → 弱队进球被低估
                    new['underdog_boost'] = min(0.30, old['underdog_boost'] + 0.03)
                elif len(score) >= 3 and score_acc > 0.25:
                    new['underdog_boost'] = max(-0.10, old['underdog_boost'] - 0.02)

                # 平局频率驱动 draw_boost
                draw_picks = sum(1 for r in wld if r.get('pick') == '平')
                draw_rate = draw_picks / max(len(wld), 1)
                if draw_rate > 0.3:
                    new['draw_boost'] = min(0.15, old['draw_boost'] + 0.02)
                elif draw_rate < 0.1:
                    new['draw_boost'] = max(-0.05, old['draw_boost'] - 0.01)

            new_coefficients[rd_name] = new

        return new_coefficients

    def _detect_overfitting(self, old_coefficients: Dict, new_coefficients: Dict,
                            reviews: List[Dict]) -> List[str]:
        """过拟合检测：防止参数过度校准到单次复盘

        检测规则：
        1. 相邻轮次系数方向相反且幅度>0.15 → 标记为潜在过拟合
        2. 系数单次变化>0.20 → 高风险警告
        3. 基于<3场数据的校准 → 低置信度警告
        """
        warnings = []
        round_order = ['group_stage_round1', 'group_stage_round2',
                       'group_stage_round3', 'knockout_stage']

        # 规则1: 检查相邻轮次方向相反
        for i in range(len(round_order) - 1):
            r1 = round_order[i]
            r2 = round_order[i + 1]
            if r1 in new_coefficients and r2 in new_coefficients:
                c1 = new_coefficients[r1]
                c2 = new_coefficients[r2]
                # 如果R1大幅降低强队系数而R2大幅提高
                if c1['fav_discount'] < 0.60 and c2['fav_discount'] > 1.05:
                    warnings.append(
                        f"⚠️ 过拟合风险：{r1} fav_discount={c1['fav_discount']} vs "
                        f"{r2} fav_discount={c2['fav_discount']}，相邻轮次反向跨度>0.45。"
                        f"建议：检查是否将R1特性过度推广到全局。"
                    )

        # 规则2: 系数变化幅度检查
        for rd_name in new_coefficients:
            if rd_name in old_coefficients:
                changes = {
                    k: abs(new_coefficients[rd_name][k] - old_coefficients[rd_name][k])
                    for k in ['fav_discount', 'underdog_boost', 'draw_boost']
                }
                for k, delta in changes.items():
                    if delta > 0.20:
                        warnings.append(
                            f"⚠️ 剧烈变化：{rd_name}.{k} 单次调整 {delta:.2f}。"
                            f"建议：分步校准，每轮调整≤0.10。"
                        )

        # 规则3: 数据量不足警告
        by_round = self.load_reviews_by_round()
        for rd_name in new_coefficients:
            count = len(by_round.get(rd_name, []))
            if count < 3 and any(
                abs(new_coefficients[rd_name][k] - old_coefficients.get(rd_name, {}).get(k, 0)) > 0.05
                for k in ['fav_discount', 'underdog_boost', 'draw_boost']
            ):
                warnings.append(
                    f"⚠️ 低置信度：{rd_name} 仅{count}场数据校准，建议积累≥5场后再调整。"
                )

        return warnings

    def calibrate_k_factor(self, reviews: List[Dict]) -> int:
        """v2.1 修复: 基于真实准确率优化Elo K值"""
        valid = self._filter_reviews_with_truth(reviews)
        if len(valid) < 3:
            return self.state['current_params']['K_FACTOR']

        accuracy = sum(1 for r in valid if self._get_correct(r)) / max(len(valid), 1)
        current = self.state['current_params']['K_FACTOR']

        # 真实准确率 35-55% → K值应在 30-40 范围
        if accuracy < 0.35:
            new_k = max(16, current - 4)
        elif accuracy > 0.55:
            new_k = min(48, current + 4)
        else:
            new_k = current

        return int(new_k)

    # ============================================
    # v2.0 回测验证
    # ============================================

    def backtest(self, test_reviews: List[Dict] = None) -> Dict:
        """v2.1 修复: 基于可用数据回测验证

        使用 hit/is_correct 计算方向准确率。
        xG偏差暂不可用（review_log 无 actual_score/predicted_xg）。
        """
        if test_reviews is None:
            test_reviews = self.load_reviews()

        valid = self._filter_reviews_with_truth(test_reviews)
        if not valid:
            return {'error': '无复盘数据可供回测'}

        direction_correct = sum(1 for r in valid if self._get_correct(r))

        # 按类型分组统计
        per_type = {}
        for r in valid:
            t = self._get_type(r) or 'unknown'
            if t not in per_type:
                per_type[t] = {'total': 0, 'correct': 0}
            per_type[t]['total'] += 1
            if self._get_correct(r):
                per_type[t]['correct'] += 1

        return {
            'direction_accuracy': round(direction_correct / len(valid) * 100, 1),
            'per_type': {
                t: {
                    'count': v['total'],
                    'accuracy': round(v['correct'] / v['total'] * 100, 1) if v['total'] > 0 else 0
                }
                for t, v in per_type.items()
            },
            'total_deviation': 'N/A (v2.1: review_log 无 actual_score/predicted_xg)',
            'avg_xg_error': 'N/A (v2.1: review_log 无 actual_score/predicted_xg)',
            'sample_count': len(valid),
            'note': 'v2.1修复: 使用 hit/is_correct 替代 actual_winner==predicted_winner'
        }

    # ============================================
    # 进化执行
    # ============================================

    def evolve(self, force: bool = False) -> Dict:
        """执行一轮进化

        v2.0 增强：
        - 轮次自适应系数校准
        - 回测验证
        - 过拟合检测与警告

        Args:
            force: 强制进化（即使数据不足）

        Returns:
            进化报告
        """
        reviews = self.load_reviews()

        if len(reviews) < 3 and not force:
            return {
                'evolved': False,
                'reason': f'复盘数据不足（当前{len(reviews)}场，至少需要3场）',
                'metrics': self.compute_accuracy_metrics(reviews)
            }

        old_params = dict(self.state['current_params'])
        old_round_coefficients = json.loads(json.dumps(self.state['round_coefficients']))
        changes = {}
        warnings = []

        # 计算当前指标
        metrics = self.compute_accuracy_metrics(reviews)

        # 1. 校准Elo权重
        new_elo_w = self.calibrate_elo_weight(reviews)
        if new_elo_w != old_params['ELO_WEIGHT']:
            changes['ELO_WEIGHT'] = {
                'old': old_params['ELO_WEIGHT'],
                'new': new_elo_w,
                'reason': f"Elo准确率与整体准确率的偏差驱动调整"
            }
            self.state['current_params']['ELO_WEIGHT'] = new_elo_w
            self.state['current_params']['POISSON_WEIGHT'] = round(1 - new_elo_w, 2)

        # 2. v2.0: 轮次自适应系数校准
        new_round_coefficients = self.calibrate_round_coefficients(reviews)
        round_changes = {}
        for rd_name in new_round_coefficients:
            if rd_name in self.state['round_coefficients']:
                diffs = {}
                for k in ['fav_discount', 'underdog_boost', 'draw_boost']:
                    old_val = self.state['round_coefficients'][rd_name][k]
                    new_val = new_round_coefficients[rd_name][k]
                    if abs(new_val - old_val) > 0.01:
                        diffs[k] = {'old': old_val, 'new': new_val}
                if diffs:
                    round_changes[rd_name] = diffs

        if round_changes:
            changes['round_coefficients'] = {
                'old': json.loads(json.dumps(self.state['round_coefficients'])),
                'new': new_round_coefficients,
                'diffs': round_changes,
                'reason': '基于各轮次独立复盘数据校准'
            }
            self.state['round_coefficients'] = new_round_coefficients

        # 3. v2.0: 过拟合检测
        if round_changes:
            detected = self._detect_overfitting(
                old_round_coefficients, new_round_coefficients, reviews
            )
            warnings.extend(detected)
            self.state['overfitting_warnings'].extend(detected)

        # 4. 校准K值
        new_k = self.calibrate_k_factor(reviews)
        if new_k != old_params['K_FACTOR']:
            changes['K_FACTOR'] = {
                'old': old_params['K_FACTOR'],
                'new': new_k,
                'reason': f"基于{metrics['overall_accuracy']}%整体准确率调整Elo学习率"
            }
            self.state['current_params']['K_FACTOR'] = new_k

        # 5. v2.0: 回测验证
        backtest_result = None
        if len(reviews) >= 3:
            backtest_result = self.backtest(reviews)

        # 记录进化事件
        evolution_event = {
            'timestamp': datetime.now().isoformat(),
            'evolution_number': self.state['evolution_count'] + 1,
            'reviews_analyzed': len(reviews),
            'pre_metrics': metrics,
            'changes': changes,
            'warnings': warnings,
            'backtest': backtest_result,
            'post_params': dict(self.state['current_params']),
            'post_round_coefficients': json.loads(json.dumps(self.state['round_coefficients']))
        }

        self.state['evolution_count'] += 1
        self.state['param_history'].append(evolution_event)
        self.state['accuracy_timeline'].append({
            'evolution': self.state['evolution_count'],
            'accuracy': metrics['overall_accuracy'],
            'recent_accuracy': metrics.get('recent_accuracy', 0),
            'timestamp': datetime.now().isoformat()
        })

        self._save_state()

        # 应用参数到运行环境
        self._apply_params()

        return {
            'evolved': len(changes) > 0,
            'evolution_number': self.state['evolution_count'],
            'reviews_analyzed': len(reviews),
            'changes': changes,
            'pre_metrics': metrics,
            'warnings': warnings,
            'backtest': backtest_result,
            'round_coefficients': self.state['round_coefficients'],
            'trend': metrics.get('trend', 'stable')
        }

    def _apply_params(self):
        """将进化后的参数应用到预测引擎"""
        import prediction_engine as pe
        params = self.state['current_params']
        pe.LEAGUE_AVG_GOALS = params['LEAGUE_AVG_GOALS']
        pe.ELO_WEIGHT = params['ELO_WEIGHT']
        pe.POISSON_WEIGHT = params['POISSON_WEIGHT']

        # v2.0: 注入轮次系数到引擎
        if hasattr(pe, 'FootballPredictionEngine') and hasattr(self, 'engine'):
            self.engine._round_coefficients = self.state['round_coefficients']

    # ============================================
    # 进化可视化
    # ============================================

    def get_evolution_timeline(self) -> List[Dict]:
        """获取进化时间线"""
        return self.state.get('accuracy_timeline', [])

    def get_parameter_history(self) -> List[Dict]:
        """获取参数变更历史"""
        return self.state.get('param_history', [])

    def get_warnings(self) -> List[str]:
        """获取过拟合警告历史"""
        return self.state.get('overfitting_warnings', [])

    def generate_evolution_report(self) -> str:
        """生成人类可读的进化报告（v2.1增强版）"""
        metrics = self.compute_accuracy_metrics()
        timeline = self.get_evolution_timeline()
        params = self.state['current_params']
        round_coeffs = self.state['round_coefficients']
        warnings = self.get_warnings()
        backtest = self.backtest()

        # 轮次系数表格
        round_rows = ""
        for rd, coeffs in round_coeffs.items():
            round_name = {
                'group_stage_round1': 'R1·首轮',
                'group_stage_round2': 'R2·次轮',
                'group_stage_round3': 'R3·末轮',
                'knockout_stage': 'KO·淘汰'
            }.get(rd, rd)
            round_rows += f"  {round_name:12s} |  ×{coeffs['fav_discount']:.2f} | {coeffs['underdog_boost']:+.2f} | {coeffs['draw_boost']:+.2f}\n"

        # 类型准确率
        type_rows = ""
        for t, acc in metrics.get('by_type', {}).items():
            type_name = {'win_lose_draw': '胜平负', 'score': '比分', 'total_goals': '总进球'}.get(t, t)
            type_rows += f"  {type_name}: {acc}%\n"

        # 过拟合警告
        warning_section = ""
        if warnings:
            warning_section = "\n⚠️ 过拟合检测:\n" + "\n".join(f"  {w}" for w in warnings[-5:])

        report = f"""
═══════════════════════════════════════════
     FIFA预测计算器 — 自我进化报告 v2.1
═══════════════════════════════════════════

📊 准确率概览
  总复盘场次: {metrics.get('total', 0)}
  整体准确率: {metrics.get('overall_accuracy', 'N/A')}%
  近期准确率 (最近{metrics.get('window_size', 0)}场): {metrics.get('recent_accuracy', 'N/A')}%
  趋势: {metrics.get('trend', 'N/A')}

📈 类型准确率
{type_rows}
📋 评级分布
  A: {metrics.get('grade_distribution', {}).get('A', 0)} | B: {metrics.get('grade_distribution', {}).get('B', 0)} | C: {metrics.get('grade_distribution', {}).get('C', 0)} | D: {metrics.get('grade_distribution', {}).get('D', 0)} | F: {metrics.get('grade_distribution', {}).get('F', 0)}

🔧 基础参数
  ELO_WEIGHT: {params['ELO_WEIGHT']}
  POISSON_WEIGHT: {params['POISSON_WEIGHT']}
  K_FACTOR: {params['K_FACTOR']}

🎯 轮次自适应系数
  轮次          | 强队系数 | 弱队加成 | 平局调整
{"-"*50}
{round_rows}
📊 回测验证
  数据样本: {backtest.get('sample_count', 0)}场
  方向准确率: {backtest.get('direction_accuracy', 'N/A')}%
  xG偏差: {backtest.get('avg_xg_error', 'N/A')}
{warning_section}
🔄 累计进化次数: {self.state['evolution_count']}
═══════════════════════════════════════════

💡 v2.1 修复: 准确率计算使用 hit/is_correct 替代 actual_winner/predicted_winner
"""
        return report


if __name__ == "__main__":
    skill_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    engine = EvolutionEngine(skill_dir)

    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--evolve':
        result = engine.evolve(force=True)
        print(f"进化结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
    elif len(sys.argv) > 1 and sys.argv[1] == '--report':
        print(engine.generate_evolution_report())
    elif len(sys.argv) > 1 and sys.argv[1] == '--backtest':
        result = engine.backtest()
        print(f"回测结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
    else:
        metrics = engine.compute_accuracy_metrics()
        print(f"当前指标: {json.dumps(metrics, ensure_ascii=False, indent=2)}")
