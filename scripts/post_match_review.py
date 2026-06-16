"""
赛后复盘引擎 v1.0 — FIFA世界杯预测计算器
功能：
  1. 联网搜索真实比赛结果
  2. 对比预测与实际结果
  3. 多维度评分 (方向/比分/xG/赔率建议)
  4. 生成复盘报告
  5. 驱动进化引擎参数校准
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from prediction_engine import FootballPredictionEngine


class PostMatchReviewer:
    """赛后复盘引擎 — 联网搜索真实比赛结果，与预测对比，生成复盘报告"""
    
    def __init__(self, skill_dir: str):
        self.skill_dir = skill_dir
        self.data_dir = os.path.join(skill_dir, 'data')
        self.logs_dir = os.path.join(skill_dir, 'logs')
        self.engine = FootballPredictionEngine(data_dir=self.data_dir)
        self.review_log = []
    
    # ============================================
    # 真实结果搜索与解析
    # ============================================
    
    @staticmethod
    def build_search_query(team_a: str, team_b: str, match_date: str = None) -> str:
        """构建搜索引擎查询语句"""
        base = f"{team_a} {team_b} 比分 比赛结果"
        if match_date:
            base += f" {match_date}"
        return base
    
    @staticmethod
    def parse_result_from_text(text: str, team_a: str, team_b: str) -> Optional[Dict]:
        """从搜索文本中解析比赛结果
        
        支持格式:
          - "巴西 2-1 摩洛哥"
          - "Brazil 2-1 Morocco"
          - "比分: 2:1"
        
        Returns:
            {'score_a': int, 'score_b': int, 'winner': str} or None
        """
        import re
        
        # 模式1: "队名 数字-数字 队名"
        pattern1 = re.compile(rf'{team_a}.*?(\d+)\s*[-:]\s*(\d+).*?{team_b}')
        m = pattern1.search(text)
        if m:
            return {
                'score_a': int(m.group(1)),
                'score_b': int(m.group(2)),
                'source': 'text_parse',
                'confidence': 'medium'
            }
        
        # 模式2: 反向顺序
        pattern2 = re.compile(rf'{team_b}.*?(\d+)\s*[-:]\s*(\d+).*?{team_a}')
        m = pattern2.search(text)
        if m:
            return {
                'score_a': int(m.group(2)),
                'score_b': int(m.group(1)),
                'source': 'text_parse_reverse',
                'confidence': 'medium'
            }
        
        # 模式3: 纯比分 "X-Y" 或 "X:Y" 上下文中有队名
        pattern3 = re.compile(r'(\d+)\s*[-:]\s*(\d+)')
        matches = pattern3.findall(text)
        if matches and (team_a in text or team_b in text):
            # 取第一个比分
            return {
                'score_a': int(matches[0][0]),
                'score_b': int(matches[0][1]),
                'source': 'score_only',
                'confidence': 'low'
            }
        
        return None
    
    # ============================================
    # 复盘评分
    # ============================================
    
    def score_prediction(self, prediction: Dict, actual: Dict) -> Dict:
        """多维评分：方向30分 + 比分30分 + xG 20分 + 赔率建议20分 = 100分"""
        scores = {}
        
        # 1. 方向评分 (30分)
        ga, gb = actual['score_a'], actual['score_b']
        if ga > gb:
            actual_winner = 'a'
        elif gb > ga:
            actual_winner = 'b'
        else:
            actual_winner = 'draw'
        
        final = prediction['final']
        pred_winner = max(final, key=final.get)
        pred_map = {'win_a': 'a', 'win_b': 'b', 'draw': 'draw'}
        predicted_dir = pred_map.get(pred_winner, 'draw')
        
        if actual_winner == predicted_dir:
            scores['direction'] = 30
        elif actual_winner == 'draw' or predicted_dir == 'draw':
            scores['direction'] = 10  # 至少预测到了平局可能性
        else:
            scores['direction'] = 0
        
        # 2. 比分评分 (30分)
        pred_scores = prediction.get('top_scores', [])
        actual_score_str = f"{ga}-{gb}"
        best_score_prob = 0
        for score, prob in pred_scores:
            if score == actual_score_str:
                best_score_prob = prob
                break
        
        if best_score_prob > 0:
            scores['score'] = min(30, int(best_score_prob * 3))
        else:
            # 检查是否在top5中预测了相近比分
            actual_total = ga + gb
            for score, prob in pred_scores:
                parts = score.split('-')
                if len(parts) == 2:
                    pred_total = int(parts[0]) + int(parts[1])
                    if abs(pred_total - actual_total) <= 1:
                        best_score_prob = prob * 0.5
                        break
            scores['score'] = max(5, min(20, int(best_score_prob * 2))) if best_score_prob > 0 else 5
        
        # 3. xG评分 (20分)
        xg_error = abs(prediction['xg_a'] - ga) + abs(prediction['xg_b'] - gb)
        if xg_error < 0.5:
            scores['xg'] = 20
        elif xg_error < 1.0:
            scores['xg'] = 15
        elif xg_error < 2.0:
            scores['xg'] = 10
        else:
            scores['xg'] = 5
        
        # 4. 赔率建议评分 (20分)
        # 如果给出了赔率分析且价值信号正确，得高分
        odds_score = 0
        if actual_winner == predicted_dir:
            model_prob = final[pred_winner] / 100
            if model_prob < 0.4:
                odds_score = 20  # 预测对了低概率事件=高价值
            elif model_prob < 0.6:
                odds_score = 15
            else:
                odds_score = 10  # 预测对了高概率事件=基本分
        elif actual_winner == 'draw' and 'draw' in final and final['draw'] > 25:
            odds_score = 10  # 虽然方向错了，但平局信号被部分捕捉
        else:
            odds_score = 0
        
        scores['odds'] = odds_score
        scores['total'] = sum(scores.values())
        
        # 评级
        if scores['total'] >= 80:
            scores['grade'] = 'A - 精准预测'
        elif scores['total'] >= 60:
            scores['grade'] = 'B - 方向正确'
        elif scores['total'] >= 40:
            scores['grade'] = 'C - 部分准确'
        elif scores['total'] >= 20:
            scores['grade'] = 'D - 偏差较大'
        else:
            scores['grade'] = 'F - 预测失败'
        
        return scores
    
    # ============================================
    # v3.0 阵容/伤停复盘维度
    # ============================================
    
    def score_live_context(self, live_data: Dict, actual_score: Tuple[int,int]) -> Dict:
        """评估实时数据（阵容/伤停）对预测的加成效果
        
        Returns:
            {'bonus': int, 'notes': str} — 加成分数（0-10）和说明
        """
        if not live_data or not live_data.get('used'):
            return {'bonus': 0, 'notes': '未使用实时数据'}
        
        bonus = 0
        notes = []
        
        # 伤病信息可用且影响显著
        injuries = live_data.get('injuries', {})
        if injuries.get('available'):
            summary = injuries.get('summary', '')
            note_key = 'injuries'
            if summary:
                notes.append(f"伤停: {summary}")
            bonus += 3
        
        # 阵容信息可用
        lineups = live_data.get('lineups', {})
        if lineups.get('available') and lineups.get('has_official'):
            notes.append("官方首发已获取")
            bonus += 2
        
        # 如果实时数据帮助修正了预测方向，额外加分
        # (通过对比 live_data 中的 Elo 调整是否趋近真实结果)
        elo_adj = live_data.get('elo_adjusted')
        elo_orig = live_data.get('elo_original')
        if elo_adj and elo_orig:
            ga, gb = actual_score
            if ga > gb:
                actual_favors_a = True
            elif gb > ga:
                actual_favors_a = False
            else:
                actual_favors_a = None
            
            if actual_favors_a is not None:
                # 调整是否更接近真实实力差
                orig_diff = elo_orig[0] - elo_orig[1]
                adj_diff = elo_adj[0] - elo_adj[1]
                
                if actual_favors_a and adj_diff < orig_diff:
                    # 真实A赢，但A被伤病降级→说明调整后更保守=合理
                    notes.append("伤病修正方向合理")
                    bonus += 2
                elif not actual_favors_a and adj_diff > orig_diff:
                    notes.append("伤病修正方向合理")
                    bonus += 2
        
        return {
            'bonus': min(bonus, 10),
            'notes': '; '.join(notes) if notes else '无特殊加成'
        }
    
    # ============================================
    # 复盘执行（增强版）
    # ============================================
    
    def review_match(self, team_a: str, team_b: str,
                     actual_score: Tuple[int, int],
                     prediction: Dict,
                     odds_data: Optional[Dict] = None,
                     match_context: Optional[Dict] = None,
                     live_data: Optional[Dict] = None) -> Dict:
        """执行单场复盘（v3.0 含实时数据维度）
        
        Args:
            team_a, team_b: 球队名
            actual_score: (进球a, 进球b)
            prediction: 预测结果字典
            odds_data: 赔率数据(可选)
            match_context: 比赛上下文(可选)
        
        Returns:
            完整复盘报告
        """
        ga, gb = actual_score
        
        # 评分
        scores = self.score_prediction(prediction, {
            'score_a': ga, 'score_b': gb
        })
        
        # Elo校准数据
        if ga > gb:
            result_a = 1.0
        elif ga == gb:
            result_a = 0.5
        else:
            result_a = 0.0
        
        old_elo_a = self.engine.elo_ratings.get(team_a, 1500)
        old_elo_b = self.engine.elo_ratings.get(team_b, 1500)
        
        calibration = self.engine.calibrate_from_result(
            team_a, team_b, actual_score, prediction
        )
        
        # 更新Elo
        new_elo_a, new_elo_b = self.engine.update_elo(team_a, team_b, result_a)
        
        # 更新球队统计
        self.engine.update_team_stats(team_a, ga, gb)
        self.engine.update_team_stats(team_b, gb, ga)
        
        # 保存更新后的数据
        self.engine.save_elo_data(self.data_dir)
        self.engine.save_team_stats(self.data_dir)
        
        # 构建复盘报告
        review = {
            'timestamp': datetime.now().isoformat(),
            'match': f"{team_a} vs {team_b}",
            'actual_score': f"{ga}-{gb}",
            'predicted_winner': calibration['predicted_winner'],
            'actual_winner': calibration['actual_winner'],
            'prediction_final': prediction['final'],
            'predicted_xg': f"{prediction['xg_a']}-{prediction['xg_b']}",
            'scores': scores,
            'calibration': calibration,
            'elo_changes': {
                team_a: f"{old_elo_a} -> {new_elo_a} ({'+' if new_elo_a > old_elo_a else ''}{new_elo_a - old_elo_a})",
                team_b: f"{old_elo_b} -> {new_elo_b} ({'+' if new_elo_b > old_elo_b else ''}{new_elo_b - old_elo_b})"
            },
            'evolution_actions': self._generate_evolution_actions(calibration, scores, prediction)
        }
        
        # v3.0: 实时数据维度评分
        if live_data:
            live_score = self.score_live_context(live_data, actual_score)
            review['live_context'] = live_score
            # 将加成分数合并到总分
            review['scores']['live_bonus'] = live_score['bonus']
            review['scores']['total_with_live'] = review['scores']['total'] + live_score['bonus']
        
        # 记录到日志
        self.review_log.append(review)
        self._append_to_log(review)
        
        return review
    
    def _generate_evolution_actions(self, calibration: Dict, scores: Dict,
                                     prediction: Dict) -> List[str]:
        """根据复盘结果生成进化建议"""
        actions = []
        
        if not calibration['direction_correct']:
            actions.append("触发方向校准：检查Elo权重(ELO_WEIGHT)是否需要从0.30上调")
            if prediction.get('tournament_round') == 'group_stage_round1':
                actions.append("首轮预测失败：检查opener_draw_probability_boost是否需要从0.15上调")
        
        if calibration['score_error'] > 1.5:
            actions.append(f"触发xG校准：总进球偏差{calibration['score_error']:.1f}球，需调整LEAGUE_AVG_GOALS或球队攻防系数")
        
        if scores['xg'] <= 10:
            actions.append("触发xG模型校准：泊松λ参数可能需要基于最近比赛结果重新估计")
        
        if scores['total'] < 40:
            actions.append(f"触发综合校准：总分{scores['total']}/100，建议检查所有核心参数")
        
        if not actions:
            actions.append("无需进化操作，预测表现良好")
        
        return actions
    
    def _append_to_log(self, review: Dict):
        """追加复盘记录到日志文件"""
        log_path = os.path.join(self.logs_dir, 'review_log.jsonl')
        os.makedirs(self.logs_dir, exist_ok=True)
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(review, ensure_ascii=False) + '\n')
    
    def load_review_history(self) -> List[Dict]:
        """加载历史复盘记录"""
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
    # 统计报告
    # ============================================
    
    def get_accuracy_report(self) -> Dict:
        """生成准确率统计报告"""
        reviews = self.load_review_history()
        if not reviews:
            return {'message': '暂无复盘数据', 'total': 0}
        
        total = len(reviews)
        correct_direction = sum(1 for r in reviews
                                if r['actual_winner'] == r['predicted_winner'])
        
        avg_score = sum(r['scores']['total'] for r in reviews) / total
        
        grades = {}
        for r in reviews:
            g = r['scores']['grade'][0]  # A/B/C/D/F
            grades[g] = grades.get(g, 0) + 1
        
        # 按赛事轮次分组
        by_round = {}
        for r in reviews:
            rd = r.get('calibration', {}).get('tournament_round', 'unknown')
            if rd not in by_round:
                by_round[rd] = {'total': 0, 'correct': 0}
            by_round[rd]['total'] += 1
            if r['actual_winner'] == r['predicted_winner']:
                by_round[rd]['correct'] += 1
        
        return {
            'total_reviews': total,
            'direction_accuracy': round(correct_direction / total * 100, 1),
            'avg_score': round(avg_score, 1),
            'grade_distribution': grades,
            'by_round': {
                rd: {
                    'total': v['total'],
                    'accuracy': round(v['correct'] / v['total'] * 100, 1)
                }
                for rd, v in by_round.items()
            }
        }


if __name__ == "__main__":
    import sys
    skill_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    reviewer = PostMatchReviewer(skill_dir)
    
    if len(sys.argv) >= 4:
        team_a, team_b = sys.argv[1], sys.argv[2]
        score_a, score_b = int(sys.argv[3]), int(sys.argv[4])
        
        # 先用引擎预测
        engine = FootballPredictionEngine(data_dir=reviewer.data_dir)
        pred = engine.predict(team_a, team_b)
        
        # 执行复盘
        review = reviewer.review_match(team_a, team_b, (score_a, score_b), pred)
        
        print(f"\n{'='*60}")
        print(f"📋 赛后复盘: {team_a} {score_a}-{score_b} {team_b}")
        print(f"{'='*60}")
        print(f"预测方向: {review['predicted_winner']} | 实际: {review['actual_winner']}")
        print(f"评分: {review['scores']['total']}/100 ({review['scores']['grade']})")
        print(f"方向: {review['scores']['direction']}/30 | 比分: {review['scores']['score']}/30")
        print(f"xG: {review['scores']['xg']}/20 | 赔率: {review['scores']['odds']}/20")
        print(f"\nElo变化: {review['elo_changes']}")
        print(f"进化建议: {review['evolution_actions']}")
    else:
        # 显示统计
        report = reviewer.get_accuracy_report()
        print(f"复盘统计: {report}")
