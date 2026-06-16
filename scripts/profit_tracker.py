"""
收益追踪器 v1.0 — FIFA世界杯预测计算器
功能：
  1. 记录每场预测的虚拟投注结果
  2. 计算ROI和累计收益
  3. Kelly仓位优化建议
  4. 押注策略回测
  5. 收益最大化分析
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from prediction_engine import FootballPredictionEngine


class ProfitTracker:
    """收益追踪器 — 追踪预测的虚拟收益，优化押注策略"""
    
    def __init__(self, skill_dir: str):
        self.skill_dir = skill_dir
        self.data_dir = os.path.join(skill_dir, 'data')
        self.logs_dir = os.path.join(skill_dir, 'logs')
        self.track_path = os.path.join(self.logs_dir, 'profit_track.jsonl')
        self.state_path = os.path.join(self.logs_dir, 'profit_state.json')
        self.engine = FootballPredictionEngine(data_dir=self.data_dir)
        self.state = self._load_state()
    
    def _load_state(self) -> Dict:
        if os.path.exists(self.state_path):
            with open(self.state_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            'initial_bankroll': 10000,  # 初始资金1万单位
            'current_bankroll': 10000,
            'total_bets': 0,
            'total_won': 0,
            'total_lost': 0,
            'total_profit': 0,
            'peak_bankroll': 10000,
            'max_drawdown': 0,
            'created_at': datetime.now().isoformat()
        }
    
    def _save_state(self):
        os.makedirs(self.logs_dir, exist_ok=True)
        with open(self.state_path, 'w', encoding='utf-8') as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)
    
    def load_tracks(self) -> List[Dict]:
        if not os.path.exists(self.track_path):
            return []
        tracks = []
        with open(self.track_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    tracks.append(json.loads(line))
        return tracks
    
    # ============================================
    # 投注模拟
    # ============================================
    
    def simulate_bet(self, team_a: str, team_b: str,
                     prediction: Dict, odds: Dict,
                     bet_strategy: str = 'kelly_half',
                     actual_score: Tuple[int, int] = None) -> Dict:
        """模拟一次投注
        
        Args:
            team_a, team_b: 球队名
            prediction: 预测结果
            odds: 赔率 {'home': 2.5, 'draw': 3.2, 'away': 2.8}
            bet_strategy: 'kelly_half' | 'kelly_full' | 'fixed_2pct' | 'value_only'
            actual_score: 实际比分，用于结算
        
        Returns:
            投注记录
        """
        final = prediction['final']
        
        # 选择投注方向
        best_key = max(final, key=final.get)
        direction_map = {'win_a': 'home', 'win_b': 'away', 'draw': 'draw'}
        bet_direction = direction_map.get(best_key, 'draw')
        model_prob = final[best_key] / 100
        
        bet_odds = odds.get(bet_direction, 3.0)
        
        # 计算投注金额
        bankroll = self.state['current_bankroll']
        
        if bet_strategy == 'kelly_half':
            kelly_pct = self.engine.kelly(model_prob, bet_odds, 0.5)
            stake = bankroll * kelly_pct
        elif bet_strategy == 'kelly_full':
            kelly_pct = self.engine.kelly(model_prob, bet_odds, 1.0)
            stake = bankroll * kelly_pct
        elif bet_strategy == 'fixed_2pct':
            stake = bankroll * 0.02
        elif bet_strategy == 'value_only':
            # 仅当有正期望值时投注
            ev = model_prob * bet_odds - 1
            if ev <= 0:
                stake = 0
            else:
                kelly_pct = self.engine.kelly(model_prob, bet_odds, 0.25)
                stake = bankroll * kelly_pct
        else:
            stake = bankroll * 0.02
        
        # 结算
        result = 'pending'
        profit = 0
        if actual_score:
            ga, gb = actual_score
            if ga > gb:
                actual_winner = 'home'
            elif gb > ga:
                actual_winner = 'away'
            else:
                actual_winner = 'draw'
            
            if bet_direction == actual_winner and stake > 0:
                result = 'won'
                profit = stake * (bet_odds - 1)
            elif stake > 0:
                result = 'lost'
                profit = -stake
            else:
                result = 'no_bet'
                profit = 0
            
            # 更新状态
            self._update_state(profit)
        
        record = {
            'timestamp': datetime.now().isoformat(),
            'match': f"{team_a} vs {team_b}",
            'bet_direction': bet_direction,
            'model_prob': round(model_prob * 100, 1),
            'odds': bet_odds,
            'stake': round(stake, 2),
            'strategy': bet_strategy,
            'result': result,
            'profit': round(profit, 2),
            'bankroll_after': round(self.state['current_bankroll'], 2)
        }
        
        if actual_score:
            record['actual_score'] = f"{actual_score[0]}-{actual_score[1]}"
        
        # 持久化
        self._append_track(record)
        self._save_state()
        
        return record
    
    def _update_state(self, profit: float):
        """更新收益状态"""
        self.state['total_bets'] += 1
        self.state['current_bankroll'] += profit
        
        if profit > 0:
            self.state['total_won'] += 1
            self.state['total_profit'] += profit
        elif profit < 0:
            self.state['total_lost'] += 1
            self.state['total_profit'] += profit
        
        # 跟踪峰值
        if self.state['current_bankroll'] > self.state['peak_bankroll']:
            self.state['peak_bankroll'] = self.state['current_bankroll']
        
        # 跟踪最大回撤
        drawdown = (self.state['peak_bankroll'] - self.state['current_bankroll']) / self.state['peak_bankroll']
        if drawdown > self.state['max_drawdown']:
            self.state['max_drawdown'] = round(drawdown, 4)
    
    def _append_track(self, record: Dict):
        os.makedirs(self.logs_dir, exist_ok=True)
        with open(self.track_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
    
    # ============================================
    # 收益分析
    # ============================================
    
    def get_profit_report(self) -> Dict:
        """生成收益报告"""
        tracks = self.load_tracks()
        state = self.state
        
        if not tracks:
            return {'message': '暂无投注记录', 'bankroll': state['current_bankroll']}
        
        won = [t for t in tracks if t['result'] == 'won']
        lost = [t for t in tracks if t['result'] == 'lost']
        settled = [t for t in tracks if t['result'] in ('won', 'lost')]
        
        total_staked = sum(t['stake'] for t in settled)
        total_return = sum(t['profit'] for t in settled)
        
        roi = (total_return / total_staked * 100) if total_staked > 0 else 0
        win_rate = (len(won) / len(settled) * 100) if settled else 0
        
        # 按策略分组
        by_strategy = {}
        for t in settled:
            s = t['strategy']
            if s not in by_strategy:
                by_strategy[s] = {'bets': 0, 'won': 0, 'profit': 0, 'staked': 0}
            by_strategy[s]['bets'] += 1
            by_strategy[s]['staked'] += t['stake']
            by_strategy[s]['profit'] += t['profit']
            if t['result'] == 'won':
                by_strategy[s]['won'] += 1
        
        for s in by_strategy:
            by_strategy[s]['roi'] = round(
                by_strategy[s]['profit'] / by_strategy[s]['staked'] * 100, 1
            ) if by_strategy[s]['staked'] > 0 else 0
            by_strategy[s]['win_rate'] = round(
                by_strategy[s]['won'] / by_strategy[s]['bets'] * 100, 1
            ) if by_strategy[s]['bets'] > 0 else 0
        
        # 收益曲线（累计）
        cumulative = []
        running = state['initial_bankroll']
        for t in tracks:
            if t['result'] in ('won', 'lost'):
                running += t['profit']
            cumulative.append({
                'match': t['match'],
                'profit': t['profit'],
                'bankroll': round(running, 2)
            })
        
        return {
            'initial_bankroll': state['initial_bankroll'],
            'current_bankroll': round(state['current_bankroll'], 2),
            'total_profit': round(state['total_profit'], 2),
            'roi': round(roi, 1),
            'total_bets': state['total_bets'],
            'settled_bets': len(settled),
            'win_rate': round(win_rate, 1),
            'won': len(won),
            'lost': len(lost),
            'peak_bankroll': round(state['peak_bankroll'], 2),
            'max_drawdown': round(state['max_drawdown'] * 100, 1),
            'by_strategy': by_strategy,
            'cumulative': cumulative[-20:] if cumulative else []  # 最近20场
        }
    
    # ============================================
    # 策略优化建议
    # ============================================
    
    def optimize_strategy(self) -> Dict:
        """基于历史数据推荐最优押注策略"""
        report = self.get_profit_report()
        by_strategy = report.get('by_strategy', {})
        
        if not by_strategy:
            return {'recommendation': '数据不足，建议使用kelly_half策略'}
        
        # 选择ROI最高的策略
        best_strategy = max(by_strategy.items(),
                           key=lambda x: x[1].get('roi', -999))
        
        recommendations = []
        
        # 分析胜率vsROI
        if report.get('win_rate', 0) > 50 and report.get('roi', 0) > 5:
            recommendations.append("当前策略盈利能力良好，建议维持")
        elif report.get('win_rate', 0) > 50 and report.get('roi', 0) < 0:
            recommendations.append("胜率尚可但ROI为负，建议检查赔率选择和投注金额管理")
        elif report.get('win_rate', 0) < 40 and report.get('roi', 0) > 10:
            recommendations.append("低胜率高ROI模式：预测捕捉到了高赔率价值，建议继续value_only策略")
        
        # 回撤控制
        if report.get('max_drawdown', 0) > 20:
            recommendations.append(f"最大回撤{report['max_drawdown']}%过高，建议降低单次投注比例至1%或采用凯利半仓")
        
        return {
            'best_strategy': best_strategy[0],
            'best_roi': best_strategy[1].get('roi', 0),
            'current_roi': report.get('roi', 0),
            'max_drawdown': report.get('max_drawdown', 0),
            'recommendations': recommendations
        }
    
    def reset(self, new_bankroll: float = 10000):
        """重置追踪器"""
        self.state = {
            'initial_bankroll': new_bankroll,
            'current_bankroll': new_bankroll,
            'total_bets': 0,
            'total_won': 0,
            'total_lost': 0,
            'total_profit': 0,
            'peak_bankroll': new_bankroll,
            'max_drawdown': 0,
            'created_at': datetime.now().isoformat()
        }
        self._save_state()
        # 清空记录
        if os.path.exists(self.track_path):
            os.remove(self.track_path)


if __name__ == "__main__":
    skill_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    tracker = ProfitTracker(skill_dir)
    
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--report':
        report = tracker.get_profit_report()
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif len(sys.argv) > 1 and sys.argv[1] == '--optimize':
        opt = tracker.optimize_strategy()
        print(json.dumps(opt, ensure_ascii=False, indent=2))
    elif len(sys.argv) > 1 and sys.argv[1] == '--reset':
        tracker.reset()
        print("收益追踪已重置")
    else:
        report = tracker.get_profit_report()
        print(f"当前资金: {report.get('current_bankroll', 'N/A')} | ROI: {report.get('roi', 'N/A')}%")
