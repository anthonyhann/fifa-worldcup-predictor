"""
赔率获取器 v2.0 — 双数据源支持
主源: BSD Free Football API (免费无限量)
备源: The Odds API (500次/月，交叉验证)
"""

import os
import json
from typing import Dict, List, Optional


class OddsFetcher:
    """赔率数据获取器（双源）"""
    
    BASE_URL = "https://api.the-odds-api.com/v4"
    
    def __init__(self, skill_id: int = None, bsd_api_key: str = None):
        self.bsd_key = bsd_api_key or os.getenv('BSD_API_KEY')
        
        if skill_id:
            self.odds_key = os.getenv(f"COZE_THE_ODDS_API_{skill_id}")
        else:
            self.odds_key = os.getenv("COZE_THE_ODDS_API_7645824779949260815")
        
        self._bsd_client = None
    
    @property
    def bsd_available(self) -> bool:
        return bool(self.bsd_key)
    
    @property
    def odds_available(self) -> bool:
        return bool(self.odds_key)
    
    def _get_bsd_client(self):
        if self._bsd_client is None and self.bsd_key:
            from bsd_client import BSDClient
            self._bsd_client = BSDClient(api_key=self.bsd_key)
        return self._bsd_client
    
    # ============================================
    # 赔率获取（BSD 优先）
    # ============================================
    
    def get_match_odds(self, home_team: str, away_team: str,
                       preferred_source: str = 'bsd') -> Optional[Dict]:
        """获取指定比赛的赔率（BSD 优先，降级到 The Odds API）"""
        result = {
            'home_team': home_team,
            'away_team': away_team,
            'source': None,
            'home': None, 'draw': None, 'away': None,
            'implied': None,
            'bsd': None,
            'the_odds': None
        }
        
        # 尝试 BSD
        if preferred_source in ('bsd', 'auto') and self.bsd_available:
            bsd = self._get_bsd_client()
            if bsd:
                try:
                    bsd_odds = bsd.get_odds(home_team=home_team, away_team=away_team)
                    if bsd_odds and bsd_odds.get('home'):
                        result['bsd'] = bsd_odds
                        result['source'] = 'BSD'
                        result['home'] = bsd_odds['home']
                        result['draw'] = bsd_odds['draw']
                        result['away'] = bsd_odds['away']
                        # 计算隐含概率
                        imp = [1.0/bsd_odds[k] for k in ('home','draw','away')]
                        total = sum(imp)
                        result['implied'] = {
                            'home': round(imp[0]/total*100, 1),
                            'draw': round(imp[1]/total*100, 1),
                            'away': round(imp[2]/total*100, 1),
                            'vig': round((total-1)*100, 1)
                        }
                except Exception:
                    pass
        
        # 尝试 The Odds API（交叉验证或降级）
        if self.odds_available:
            try:
                from coze_workload_identity import requests
                url = f"{self.BASE_URL}/sports/soccer_fifa_world_cup/odds/"
                params = {
                    "apiKey": self.odds_key,
                    "regions": "eu,us",
                    "markets": "h2h",
                    "oddsFormat": "decimal"
                }
                response = requests.get(url, params=params, timeout=30)
                if response.status_code == 200:
                    all_odds = response.json()
                    for match in all_odds:
                        ht = (match.get('home_team') or '').lower()
                        at = (match.get('away_team') or '').lower()
                        if home_team.lower() in ht and away_team.lower() in at:
                            avg = self.get_average_odds(match)
                            if avg:
                                result['the_odds'] = avg
                                if not result['source']:
                                    result['source'] = 'The Odds API'
                                    result['home'] = avg['prob_home']
                                    result['draw'] = avg['prob_draw']
                                    result['away'] = avg['prob_away']
                                    result['implied'] = {
                                        'home': avg['prob_home'],
                                        'draw': avg['prob_draw'],
                                        'away': avg['prob_away'],
                                        'vig': avg['vig']
                                    }
                                break
            except Exception:
                pass
        
        if not result['source']:
            return None
        
        return result
    
    # ============================================
    # 交叉验证
    # ============================================
    
    def verify_odds(self, home_team: str, away_team: str) -> Dict:
        """双源交叉验证赔率一致性
        
        Returns:
            {
                'bsd': {...},
                'the_odds': {...},
                'agreement': bool,       # 双源是否一致
                'max_deviation': float   # 最大偏差(%)
            }
        """
        result = self.get_match_odds(home_team, away_team)
        if not result:
            return {'agreement': False, 'reason': '无可用数据源'}
        
        both = result['bsd'] and result['the_odds']
        if not both:
            return {
                'agreement': True,
                'reason': f"仅{result['source']}可用",
                'single_source': result['source']
            }
        
        bsd_imp = result['bsd'].get('implied', result.get('implied', {}))
        to_imp = result['the_odds']
        
        dev_home = abs(bsd_imp.get('home', 0) - to_imp.get('prob_home', 0))
        dev_draw = abs(bsd_imp.get('draw', 0) - to_imp.get('prob_draw', 0))
        dev_away = abs(bsd_imp.get('away', 0) - to_imp.get('prob_away', 0))
        max_dev = max(dev_home, dev_draw, dev_away)
        
        return {
            'agreement': max_dev < 5.0,
            'max_deviation': round(max_dev, 1),
            'details': {
                'bsd': {'home': bsd_imp.get('home'), 'draw': bsd_imp.get('draw'), 'away': bsd_imp.get('away')},
                'the_odds': {'home': to_imp.get('prob_home'), 'draw': to_imp.get('prob_draw'), 'away': to_imp.get('prob_away')}
            }
        }
    
    # ============================================
    # The Odds API 方法（保留兼容）
    # ============================================
    
    def get_world_cup_odds(self, markets: str = "h2h",
                           regions: str = "eu,us") -> List[Dict]:
        if not self.odds_key:
            return []
        try:
            from coze_workload_identity import requests
            url = f"{self.BASE_URL}/sports/soccer_fifa_world_cup/odds/"
            params = {
                "apiKey": self.odds_key,
                "regions": regions,
                "markets": markets,
                "oddsFormat": "decimal"
            }
            response = requests.get(url, params=params, timeout=30)
            if response.status_code != 200:
                return []
            return response.json()
        except Exception:
            return []
    
    def get_average_odds(self, match_data: Dict) -> Dict:
        probs_home, probs_draw, probs_away = [], [], []
        home_team = match_data['home_team']
        away_team = match_data['away_team']
        
        for bookmaker in match_data.get('bookmakers', []):
            for market in bookmaker.get('markets', []):
                outcomes = {o['name']: o['price'] for o in market.get('outcomes', [])}
                home_key, away_key, draw_key = home_team, away_team, 'Draw'
                if home_key in outcomes and away_key in outcomes and draw_key in outcomes:
                    probs_home.append(1/outcomes[home_key])
                    probs_draw.append(1/outcomes[draw_key])
                    probs_away.append(1/outcomes[away_key])
        
        if not probs_home:
            return None
        
        total_raw = sum(probs_home)/len(probs_home) + sum(probs_draw)/len(probs_draw) + sum(probs_away)/len(probs_away)
        return {
            'home_team': home_team, 'away_team': away_team,
            'prob_home': round(sum(probs_home)/len(probs_home)/total_raw*100, 1),
            'prob_draw': round(sum(probs_draw)/len(probs_draw)/total_raw*100, 1),
            'prob_away': round(sum(probs_away)/len(probs_away)/total_raw*100, 1),
            'vig': round((total_raw-1)*100, 1),
            'num_bookmakers': len(probs_home)
        }
    
    def value_scan(self, model_predictions: List[Dict], threshold: float = 3.0) -> List[Dict]:
        all_odds = self.get_world_cup_odds()
        value_matches = []
        for match in all_odds:
            avg = self.get_average_odds(match)
            if not avg:
                continue
            for pred in model_predictions:
                if (pred['team_a'].lower() in avg['home_team'].lower() or
                    pred['team_b'].lower() in avg['home_team'].lower()):
                    market_prob = {'win_a': avg['prob_home'], 'draw': avg['prob_draw'], 'win_b': avg['prob_away']}
                    from prediction_engine import FootballPredictionEngine
                    engine = FootballPredictionEngine()
                    edges = engine.value_detection(pred['final'], market_prob, threshold)
                    has_value = any(v['is_value'] for v in edges.values())
                    if has_value:
                        value_matches.append({
                            'match': f"{avg['home_team']} vs {avg['away_team']}",
                            'market': market_prob, 'model': pred['final'], 'edges': edges
                        })
        return value_matches


if __name__ == "__main__":
    fetcher = OddsFetcher()
    
    print("=== 赔率数据源状态 ===")
    print(f"BSD API:       {'✅ 可用' if fetcher.bsd_available else '❌ 未配置 (注册: sports.bzzoiro.com)'}")
    print(f"The Odds API:  {'✅ 可用' if fetcher.odds_available else '❌ 未配置'}")
    
    if not fetcher.bsd_available and not fetcher.odds_available:
        print("\n⚠️ 请配置至少一个数据源:")
        print("  BSD:  export BSD_API_KEY='your_key'  (免费无限量，推荐)")
        print("  Odds: 已配置 COZE_THE_ODDS_API_* 环境变量")
