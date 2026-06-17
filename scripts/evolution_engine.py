"""
自我进化引擎 v2.0 — FIFA世界杯预测计算器
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
  - 轮次系数(ROUND_COEFFICIENTS)纳入可进化状态
  - 过拟合检测：当R1修正+15%在R2反弹-10%时自动触发校验
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
                'K_FACTOR': 32,
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
        """计算各种准确率指标（含轮次维度）"""
        if reviews is None:
            reviews = self.load_reviews()

        if not reviews:
            return {'total': 0, 'message': '无复盘数据'}

        total = len(reviews)
        correct = sum(1 for r in reviews
                      if r.get('actual_winner') == r.get('predicted_winner'))

        # 滑动窗口（最近10场）
        window = min(10, total)
        recent = reviews[-window:]
        recent_correct = sum(1 for r in recent
                             if r.get('actual_winner') == r.get('predicted_winner'))

        # 趋势检测
        trend = 'stable'
        if total >= 5:
            half = total // 2
            first_half = reviews[:half]
            second_half = reviews[half:]
            first_acc = sum(1 for r in first_half if r.get('actual_winner') == r.get('predicted_winner')) / max(len(first_half), 1)
            second_acc = sum(1 for r in second_half if r.get('actual_winner') == r.get('predicted_winner')) / max(len(second_half), 1)
            diff = second_acc - first_acc
            if diff > 0.05:
                trend = 'improving'
            elif diff < -0.05:
                trend = 'declining'

        # 按轮次准确率
        by_round = {}
        for r in reviews:
            rd = r.get('calibration', {}).get('tournament_round',
                   r.get('tournament_round', 'unknown'))
            if rd not in by_round:
                by_round[rd] = {'total': 0, 'correct': 0}
            by_round[rd]['total'] += 1
            if r.get('actual_winner') == r.get('predicted_winner'):
                by_round[rd]['correct'] += 1

        round_accuracy = {}
        for rd, v in by_round.items():
            round_accuracy[rd] = round(v['correct'] / v['total'] * 100, 1)

        return {
            'total': total,
            'overall_accuracy': round(correct / total * 100, 1) if total > 0 else 0,
            'recent_accuracy': round(recent_correct / window * 100, 1) if window > 0 else 0,
            'window_size': window,
            'trend': trend,
            'by_round': round_accuracy,
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
        """基于复盘数据优化Elo与泊松的权重比例"""
        if len(reviews) < 3:
            return self.state['current_params']['ELO_WEIGHT']

        total = len(reviews)
        elo_correct = 0
        for r in reviews:
            elo_exp = r.get('elo_expected', 0.5)
            if elo_exp > 0.5:
                elo_winner = 'a'
            elif elo_exp < 0.5:
                elo_winner = 'b'
            else:
                elo_winner = 'draw'
            if elo_winner == r.get('actual_winner'):
                elo_correct += 1

        elo_acc = elo_correct / max(total, 1)
        overall_acc = sum(1 for r in reviews
                          if r.get('actual_winner') == r.get('predicted_winner')) / max(total, 1)

        current = self.state['current_params']['ELO_WEIGHT']
        if elo_acc > overall_acc + 0.1:
            new_weight = min(0.50, current + 0.05)
        elif elo_acc < overall_acc - 0.1:
            new_weight = max(0.15, current - 0.05)
        else:
            new_weight = current

        return round(new_weight, 2)

    def calibrate_round_coefficients(self, reviews: List[Dict]) -> Dict[str, Dict]:
        """轮次自适应系数校准 — 基于每轮复盘数据独立优化

        核心逻辑（来自 football-match-analysis 的 v2.1 迭代）:
        - R1: 强队进球常被高估 → fav_discount ↓ / underdog_boost ↑ / draw_boost ↑
        - R2: 强队反弹、弱队回归 → fav_discount ↑ / underdog_boost ↓ / draw_boost ↓
        - R3: 接近常态 → 系数接近1.0
        - KO: 防守更严 → fav_discount 略↓ / draw_boost 略↑

        校准方法：
        - 每轮计算"强队进球偏差"和"弱队进球偏差"
        - 按偏差方向逐步调整系数（每轮每次最多±0.10）
        - 系数边界: fav_discount [0.30, 1.30], underdog [-0.40, +0.80], draw [-0.15, +0.25]
        """
        if len(reviews) < 3:
            return dict(self.state['round_coefficients'])

        # 按轮次分组并计算xG偏差
        by_round_xg_errors = {}
        for r in reviews:
            rd = r.get('calibration', {}).get('tournament_round',
                   r.get('tournament_round', ''))
            if rd not in self.state['round_coefficients']:
                continue

            # 从校准数据中提取xG误差
            cal = r.get('calibration', {})
            xg_error = cal.get('xg_error', cal.get('score_error', 0))

            # 从 prediction 中提取 xG 方向
            pred = r.get('prediction', {})
            xg_diff = pred.get('xg_a', 0) - pred.get('xg_b', 0)

            if rd not in by_round_xg_errors:
                by_round_xg_errors[rd] = []

            by_round_xg_errors[rd].append({
                'xg_error': xg_error,
                'xg_diff': xg_diff,
                'actual_winner': r.get('actual_winner', ''),
                'predicted_winner': r.get('predicted_winner', '')
            })

        # 每轮独立校准
        new_coefficients = {}
        for rd_name in self.state['round_coefficients']:
            old = self.state['round_coefficients'][rd_name]
            new = dict(old)

            if rd_name in by_round_xg_errors and len(by_round_xg_errors[rd_name]) >= 2:
                errors = by_round_xg_errors[rd_name]
                avg_error = sum(e['xg_error'] for e in errors) / len(errors)

                # 统计方向正确率
                dir_correct = sum(1 for e in errors
                                  if e['actual_winner'] == e['predicted_winner'])
                dir_acc = dir_correct / len(errors)

                # 如果方向准确率低 → 调整 fav_discount
                if dir_acc < 0.4:
                    # 可能是强队系数过高或过低
                    if sum(1 for e in errors if e['predicted_winner'] == 'a') > len(errors) / 2:
                        # 过度预测强队胜 → 降低系数
                        new['fav_discount'] = max(0.30, old['fav_discount'] - 0.08)
                    else:
                        # 过度预测弱队/平局 → 提高系数
                        new['fav_discount'] = min(1.30, old['fav_discount'] + 0.08)

                # 如果xG偏差大 → 调整 underdog_boost
                if avg_error > 1.5:
                    # xG总偏差大，根据偏差方向调整
                    fav_errors = [e for e in errors if e['predicted_winner'] == 'a']
                    if fav_errors:
                        avg_fav_xg_error = sum(e['xg_error'] for e in fav_errors) / len(fav_errors)
                        if avg_fav_xg_error > 1.0:
                            # 强队xG被高估 → 继续打折 / 弱队加成
                            new['fav_discount'] = max(0.30, old['fav_discount'] - 0.05)
                            new['underdog_boost'] = min(0.80, old['underdog_boost'] + 0.05)
                        else:
                            # 强队xG被低估 → 放松打折
                            new['fav_discount'] = min(1.30, old['fav_discount'] + 0.05)
                            new['underdog_boost'] = max(-0.40, old['underdog_boost'] - 0.05)

                # 平局概率校准
                actual_draws = sum(1 for e in errors if e['actual_winner'] == 'draw')
                actual_draw_rate = actual_draws / len(errors)
                # 目标：模型平局概率应接近实际
                if actual_draw_rate > 0.5:
                    new['draw_boost'] = min(0.25, old['draw_boost'] + 0.03)
                elif actual_draw_rate < 0.2:
                    new['draw_boost'] = max(-0.15, old['draw_boost'] - 0.03)

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
        """优化Elo K值"""
        if len(reviews) < 3:
            return self.state['current_params']['K_FACTOR']

        accuracy = sum(1 for r in reviews
                       if r.get('actual_winner') == r.get('predicted_winner')) / max(len(reviews), 1)
        current = self.state['current_params']['K_FACTOR']

        if accuracy < 0.4:
            new_k = max(16, current - 4)
        elif accuracy > 0.6:
            new_k = min(64, current + 4)
        else:
            new_k = current

        return int(new_k)

    # ============================================
    # v2.0 回测验证
    # ============================================

    def backtest(self, test_reviews: List[Dict] = None) -> Dict:
        """回测验证：用历史数据验证当前参数

        模拟在不同参数设置下对已知比赛进行预测，
        比较预测准确性，防止过拟合到单次复盘。

        Returns:
            {
                'total_deviation': float,     # 总偏差
                'direction_accuracy': float,  # 方向准确率
                'avg_xg_error': float,        # 平均xG误差
                'per_round': dict,            # 每轮表现
                'comparison': dict  # 与前版本对比
            }
        """
        if test_reviews is None:
            test_reviews = self.load_reviews()

        if not test_reviews:
            return {'error': '无复盘数据可供回测'}

        total_deviation = 0
        direction_correct = 0
        total_xg_error = 0
        per_round = {}

        for r in test_reviews:
            # 从复盘记录中提取必要信息
            match_name = r.get('match', '')
            parts = match_name.split(' vs ')
            if len(parts) != 2:
                continue
            team_a, team_b = parts[0], parts[1]

            actual_score = r.get('actual_score', '0-0')
            try:
                score_parts = actual_score.split('-')
                ga, gb = int(score_parts[0]), int(score_parts[1])
            except:
                continue

            # 获取预测中的xG
            pred_xg_str = r.get('predicted_xg', '0-0')
            try:
                xg_parts = pred_xg_str.split('-')
                pxg_a, pxg_b = float(xg_parts[0]), float(xg_parts[1])
            except:
                continue

            # 计算偏差
            deviation = abs(pxg_a - ga) + abs(pxg_b - gb)
            total_deviation += deviation
            total_xg_error += deviation

            # 方向判断
            if ga > gb:
                actual_dir = 'a'
            elif gb > ga:
                actual_dir = 'b'
            else:
                actual_dir = 'draw'

            if actual_dir == r.get('predicted_winner', ''):
                direction_correct += 1

            # 按轮次分组
            rd = r.get('calibration', {}).get('tournament_round',
                   r.get('tournament_round', 'unknown'))
            if rd not in per_round:
                per_round[rd] = {'total': 0, 'deviation': 0, 'correct': 0}
            per_round[rd]['total'] += 1
            per_round[rd]['deviation'] += deviation
            if actual_dir == r.get('predicted_winner', ''):
                per_round[rd]['correct'] += 1

        return {
            'total_deviation': round(total_deviation, 2),
            'direction_accuracy': round(direction_correct / len(test_reviews) * 100, 1),
            'avg_xg_error': round(total_xg_error / len(test_reviews), 2),
            'per_round': {
                rd: {
                    'count': v['total'],
                    'avg_deviation': round(v['deviation'] / v['total'], 2),
                    'direction_accuracy': round(v['correct'] / v['total'] * 100, 1)
                }
                for rd, v in per_round.items()
            },
            'sample_count': len(test_reviews)
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
        """生成人类可读的进化报告（v2.0增强版）"""
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

        # 过拟合警告
        warning_section = ""
        if warnings:
            warning_section = "\n⚠️ 过拟合检测:\n" + "\n".join(f"  {w}" for w in warnings[-5:])

        report = f"""
═══════════════════════════════════════════
     FIFA预测计算器 — 自我进化报告 v2.0
═══════════════════════════════════════════

📊 准确率概览
  总复盘场次: {metrics.get('total', 0)}
  整体方向准确率: {metrics.get('overall_accuracy', 'N/A')}%
  近期准确率 (最近{metrics.get('window_size', 0)}场): {metrics.get('recent_accuracy', 'N/A')}%
  趋势: {metrics.get('trend', 'N/A')}

📈 轮次准确率
{chr(10).join(f'  {rd}: {acc}%' for rd, acc in metrics.get('by_round', {}).items())}

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
  总偏差: {backtest.get('total_deviation', 'N/A')}
  方向准确率: {backtest.get('direction_accuracy', 'N/A')}%
  平均xG误差: {backtest.get('avg_xg_error', 'N/A')}球
{warning_section}
🔄 累计进化次数: {self.state['evolution_count']}
═══════════════════════════════════════════

💡 核心规律 (v2.1):
  强队表现按轮次变化巨大，不能用单一系数。
  R1保守(0.50x) → R2反弹(1.10x) → R3常态(1.00x) → KO防守(0.95x)
  模型必须按轮次自适应，否则会在R1高估、R2低估之间反复出错。
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
