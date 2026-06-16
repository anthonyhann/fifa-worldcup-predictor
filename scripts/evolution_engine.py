"""
自我进化引擎 v1.0 — FIFA世界杯预测计算器
功能：
  1. 追踪预测准确率变化趋势
  2. 基于复盘数据自动校准核心参数
  3. 自适应Elo K值调整
  4. 修正因子动态优化
  5. 进化事件日志
"""

import json
import os
import math
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from prediction_engine import FootballPredictionEngine, LEAGUE_AVG_GOALS, ELO_WEIGHT, POISSON_WEIGHT


class EvolutionEngine:
    """自我进化引擎 — 基于复盘数据不断优化预测模型参数"""
    
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
            'version': '1.0',
            'created_at': datetime.now().isoformat(),
            'evolution_count': 0,
            'param_history': [],
            'accuracy_timeline': [],
            'current_params': {
                'LEAGUE_AVG_GOALS': LEAGUE_AVG_GOALS,
                'ELO_WEIGHT': 0.30,
                'POISSON_WEIGHT': 0.70,
                'K_FACTOR': 32,
                'OPENER_DRAW_BOOST': 0.15,
                'FAV_GOAL_DISCOUNT': 0.50,
                'UNDERDOG_GOAL_BOOST': 0.40,
                'DEFENSE_REGRESSION': 0.30,
                'VALUE_THRESHOLD': 3.0
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
    
    # ============================================
    # 准确率追踪
    # ============================================
    
    def compute_accuracy_metrics(self, reviews: List[Dict] = None) -> Dict:
        """计算各种准确率指标"""
        if reviews is None:
            reviews = self.load_reviews()
        
        if not reviews:
            return {'total': 0, 'message': '无复盘数据'}
        
        total = len(reviews)
        correct = sum(1 for r in reviews
                      if r['actual_winner'] == r['predicted_winner'])
        
        # 滑动窗口（最近10场）
        window = min(10, total)
        recent = reviews[-window:]
        recent_correct = sum(1 for r in recent
                             if r['actual_winner'] == r['predicted_winner'])
        
        # 趋势检测
        trend = 'stable'
        if total >= 5:
            first_half = reviews[:total//2]
            second_half = reviews[total//2:]
            first_acc = sum(1 for r in first_half if r['actual_winner'] == r['predicted_winner']) / len(first_half)
            second_acc = sum(1 for r in second_half if r['actual_winner'] == r['predicted_winner']) / len(second_half)
            diff = second_acc - first_acc
            if diff > 0.05:
                trend = 'improving'
            elif diff < -0.05:
                trend = 'declining'
        
        return {
            'total': total,
            'overall_accuracy': round(correct / total * 100, 1),
            'recent_accuracy': round(recent_correct / window * 100, 1),
            'window_size': window,
            'trend': trend,
            'avg_score': round(sum(r['scores']['total'] for r in reviews) / total, 1),
            'grade_distribution': self._compute_grades(reviews)
        }
    
    def _compute_grades(self, reviews: List[Dict]) -> Dict:
        grades = {'A': 0, 'B': 0, 'C': 0, 'D': 0, 'F': 0}
        for r in reviews:
            g = r['scores']['grade'][0]
            if g in grades:
                grades[g] += 1
        return grades
    
    # ============================================
    # 参数自动校准
    # ============================================
    
    def calibrate_elo_weight(self, reviews: List[Dict]) -> float:
        """基于复盘数据优化Elo与泊松的权重比例"""
        if len(reviews) < 3:
            return self.state['current_params']['ELO_WEIGHT']
        
        # 分析Elo预测和泊松预测各自的准确率
        # 如果Elo连续正确而泊松错 → 提高ELO_WEIGHT
        # 如果泊松连续正确而Elo错 → 降低ELO_WEIGHT
        total = len(reviews)
        elo_correct = 0
        for r in reviews:
            # Elo预测方向
            elo_exp = r.get('elo_expected', 0.5)
            if elo_exp > 0.5:
                elo_winner = 'a'
            elif elo_exp < 0.5:
                elo_winner = 'b'
            else:
                elo_winner = 'draw'
            if elo_winner == r['actual_winner']:
                elo_correct += 1
        
        elo_acc = elo_correct / total
        overall_acc = sum(1 for r in reviews if r['actual_winner'] == r['predicted_winner']) / total
        
        # 如果Elo准确率高于整体，提高Elo权重
        current = self.state['current_params']['ELO_WEIGHT']
        if elo_acc > overall_acc + 0.1:
            new_weight = min(0.50, current + 0.05)
        elif elo_acc < overall_acc - 0.1:
            new_weight = max(0.15, current - 0.05)
        else:
            new_weight = current
        
        return round(new_weight, 2)
    
    def calibrate_draw_boost(self, reviews: List[Dict]) -> float:
        """优化首轮平局加成参数"""
        if len(reviews) < 3:
            return self.state['current_params']['OPENER_DRAW_BOOST']
        
        # 统计首轮比赛的平局实际发生率
        opener_draws = 0
        opener_total = 0
        for r in reviews:
            if 'group_stage_round1' in str(r.get('tournament_round', '')):
                opener_total += 1
                if r['actual_winner'] == 'draw':
                    opener_draws += 1
        
        current = self.state['current_params']['OPENER_DRAW_BOOST']
        
        if opener_total >= 2:
            actual_draw_rate = opener_draws / opener_total
            # 目标：首轮预测平局概率应接近实际平局率
            if actual_draw_rate > 0.4:  # 实际平局率高
                new_boost = min(0.25, current + 0.03)
            elif actual_draw_rate < 0.2:  # 实际平局率低
                new_boost = max(0.05, current - 0.03)
            else:
                new_boost = current
        else:
            new_boost = current
        
        return round(new_boost, 2)
    
    def calibrate_goal_discount(self, reviews: List[Dict]) -> Tuple[float, float]:
        """优化首轮进球修正系数"""
        if len(reviews) < 3:
            return (
                self.state['current_params']['FAV_GOAL_DISCOUNT'],
                self.state['current_params']['UNDERDOG_GOAL_BOOST']
            )
        
        # 分析首轮强队实际进球 vs xG
        opener_xg_errors = []
        for r in reviews:
            if 'group_stage_round1' in str(r.get('tournament_round', '')):
                error = r.get('calibration', {}).get('score_error', 0)
                if error > 0:
                    opener_xg_errors.append(error)
        
        fav_discount = self.state['current_params']['FAV_GOAL_DISCOUNT']
        underdog_boost = self.state['current_params']['UNDERDOG_GOAL_BOOST']
        
        if opener_xg_errors:
            avg_error = sum(opener_xg_errors) / len(opener_xg_errors)
            if avg_error > 1.5:
                # 强队xG仍高估，进一步打折
                fav_discount = max(0.30, fav_discount - 0.10)
                underdog_boost = min(0.80, underdog_boost + 0.10)
            elif avg_error < 0.5:
                # xG预测过好，可以略微放松修正
                fav_discount = min(0.70, fav_discount + 0.05)
                underdog_boost = max(0.20, underdog_boost - 0.05)
        
        return round(fav_discount, 2), round(underdog_boost, 2)
    
    def calibrate_k_factor(self, reviews: List[Dict]) -> int:
        """优化Elo K值"""
        if len(reviews) < 3:
            return self.state['current_params']['K_FACTOR']
        
        # K值影响Elo更新速度。如果预测方向频繁变化但准确率低，降低K值
        # 如果预测方向稳定但准确率高，可维持或略微提高
        accuracy = sum(1 for r in reviews if r['actual_winner'] == r['predicted_winner']) / len(reviews)
        current = self.state['current_params']['K_FACTOR']
        
        if accuracy < 0.4:
            new_k = max(16, current - 4)  # 准确率低，减小波动
        elif accuracy > 0.6:
            new_k = min(64, current + 4)  # 准确率高，可加速学习
        else:
            new_k = current
        
        return int(new_k)
    
    # ============================================
    # 进化执行
    # ============================================
    
    def evolve(self, force: bool = False) -> Dict:
        """执行一轮进化
        
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
        changes = {}
        
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
        
        # 2. 校准首轮平局加成
        new_draw_boost = self.calibrate_draw_boost(reviews)
        if new_draw_boost != old_params['OPENER_DRAW_BOOST']:
            changes['OPENER_DRAW_BOOST'] = {
                'old': old_params['OPENER_DRAW_BOOST'],
                'new': new_draw_boost,
                'reason': '首轮平局实际发生率与预测偏差驱动调整'
            }
            self.state['current_params']['OPENER_DRAW_BOOST'] = new_draw_boost
        
        # 3. 校准进球修正
        new_fav_disc, new_und_boost = self.calibrate_goal_discount(reviews)
        if new_fav_disc != old_params['FAV_GOAL_DISCOUNT']:
            changes['FAV_GOAL_DISCOUNT'] = {
                'old': old_params['FAV_GOAL_DISCOUNT'],
                'new': new_fav_disc,
                'reason': '首轮强队xG偏差驱动调整'
            }
            self.state['current_params']['FAV_GOAL_DISCOUNT'] = new_fav_disc
        if new_und_boost != old_params['UNDERDOG_GOAL_BOOST']:
            changes['UNDERDOG_GOAL_BOOST'] = {
                'old': old_params['UNDERDOG_GOAL_BOOST'],
                'new': new_und_boost,
                'reason': '首轮弱队进球偏差驱动调整'
            }
            self.state['current_params']['UNDERDOG_GOAL_BOOST'] = new_und_boost
        
        # 4. 校准K值
        new_k = self.calibrate_k_factor(reviews)
        if new_k != old_params['K_FACTOR']:
            changes['K_FACTOR'] = {
                'old': old_params['K_FACTOR'],
                'new': new_k,
                'reason': f"基于{metrics['overall_accuracy']}%整体准确率调整Elo学习率"
            }
            self.state['current_params']['K_FACTOR'] = new_k
        
        # 记录进化事件
        evolution_event = {
            'timestamp': datetime.now().isoformat(),
            'evolution_number': self.state['evolution_count'] + 1,
            'reviews_analyzed': len(reviews),
            'pre_metrics': metrics,
            'changes': changes,
            'post_params': dict(self.state['current_params'])
        }
        
        self.state['evolution_count'] += 1
        self.state['param_history'].append(evolution_event)
        self.state['accuracy_timeline'].append({
            'evolution': self.state['evolution_count'],
            'accuracy': metrics['overall_accuracy'],
            'recent_accuracy': metrics['recent_accuracy'],
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
            'current_params': dict(self.state['current_params']),
            'trend': metrics['trend']
        }
    
    def _apply_params(self):
        """将进化后的参数应用到预测引擎（通过monkey-patching方式）"""
        import prediction_engine as pe
        params = self.state['current_params']
        pe.LEAGUE_AVG_GOALS = params['LEAGUE_AVG_GOALS']
        pe.ELO_WEIGHT = params['ELO_WEIGHT']
        pe.POISSON_WEIGHT = params['POISSON_WEIGHT']
        # 其他参数通过corrections.json管理
    
    # ============================================
    # 进化可视化
    # ============================================
    
    def get_evolution_timeline(self) -> List[Dict]:
        """获取进化时间线"""
        return self.state.get('accuracy_timeline', [])
    
    def get_parameter_history(self) -> List[Dict]:
        """获取参数变更历史"""
        return self.state.get('param_history', [])
    
    def generate_evolution_report(self) -> str:
        """生成人类可读的进化报告"""
        metrics = self.compute_accuracy_metrics()
        timeline = self.get_evolution_timeline()
        params = self.state['current_params']
        
        report = f"""
═══════════════════════════════════════════
        FIFA预测计算器 — 自我进化报告
═══════════════════════════════════════════

📊 准确率概览
  总复盘场次: {metrics.get('total', 0)}
  整体方向准确率: {metrics.get('overall_accuracy', 'N/A')}%
  近期准确率 (最近{metrics.get('window_size', 0)}场): {metrics.get('recent_accuracy', 'N/A')}%
  平均评分: {metrics.get('avg_score', 'N/A')}/100
  趋势: {metrics.get('trend', 'N/A')}

📈 评级分布
  A: {metrics.get('grade_distribution', {}).get('A', 0)}场
  B: {metrics.get('grade_distribution', {}).get('B', 0)}场
  C: {metrics.get('grade_distribution', {}).get('C', 0)}场
  D: {metrics.get('grade_distribution', {}).get('D', 0)}场
  F: {metrics.get('grade_distribution', {}).get('F', 0)}场

🔧 当前参数
  ELO_WEIGHT: {params['ELO_WEIGHT']}
  POISSON_WEIGHT: {params['POISSON_WEIGHT']}
  K_FACTOR: {params['K_FACTOR']}
  OPENER_DRAW_BOOST: {params['OPENER_DRAW_BOOST']}
  FAV_GOAL_DISCOUNT: {params['FAV_GOAL_DISCOUNT']}
  UNDERDOG_GOAL_BOOST: {params['UNDERDOG_GOAL_BOOST']}

🔄 累计进化次数: {self.state['evolution_count']}
═══════════════════════════════════════════
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
    else:
        metrics = engine.compute_accuracy_metrics()
        print(f"当前指标: {json.dumps(metrics, ensure_ascii=False, indent=2)}")
