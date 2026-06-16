"""
实时数据获取与整合层 v1.0
统一封装 BSD API 的阵容/伤停/赔率数据，提供预测引擎可用的结构化输出
"""

import json
import os
import time
from typing import Dict, List, Optional, Tuple

from bsd_client import BSDClient


class LiveDataFetcher:
    """实时数据统一获取层

    整合三路数据:
    1. 首发阵容 (lineups)        → 影响 xG 和战术分析
    2. 伤停报告 (injuries)       → 影响 Elo 和球队实力评估
    3. 实时赔率 (odds)           → 影响价值检测和 Kelly 仓位
    """

    def __init__(self, api_key: str = None, cache_dir: str = None):
        self.client = BSDClient(api_key=api_key, cache_dir=cache_dir)
        self._data_dir = cache_dir or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), '..', 'data'
        )

    @property
    def is_available(self) -> bool:
        return bool(self.client.api_key)

    # ============================================
    # 阵容获取
    # ============================================

    def get_lineups(self, home_team: str, away_team: str,
                    match_id: int = None) -> Dict:
        """获取首发阵容，含降级处理

        Returns:
            {
                'available': bool,
                'has_official': bool,     # 是否为官方公布的首发
                'home': { 'formation': str, 'startXI': list, 'player_count': int },
                'away': { 'formation': str, 'startXI': list, 'player_count': int },
                'fetched_at': str,
                'source': 'BSD' | 'cache' | 'unavailable'
            }
        """
        result = {
            'available': False,
            'has_official': False,
            'home': None,
            'away': None,
            'source': 'unavailable'
        }

        if not self.is_available:
            return result

        try:
            if match_id:
                raw = self.client.get_lineups(match_id=match_id)
            else:
                raw = self.client.get_lineups(
                    home_team=home_team, away_team=away_team
                )
        except RuntimeError:
            return result

        if raw and raw.get('available'):
            result.update({
                'available': True,
                'has_official': True,
                'home': raw.get('home'),
                'away': raw.get('away'),
                'fetched_at': raw.get('fetched_at'),
                'source': 'BSD'
            })

        return result

    # ============================================
    # 伤停获取
    # ============================================

    def get_injuries(self, home_team: str, away_team: str,
                     match_id: int = None) -> Dict:
        """获取伤停报告

        Returns:
            {
                'available': bool,
                'home': [{'name': str, 'reason': str, 'status': 'Out'|'Doubtful'|'Suspended'}],
                'away': [...],
                'home_out_count': int,    # 确认缺阵人数
                'away_out_count': int,
                'home_doubtful_count': int,
                'away_doubtful_count': int,
                'impact_summary': str     # 伤停影响简述
            }
        """
        result = {
            'available': False,
            'home': [],
            'away': [],
            'home_out_count': 0,
            'away_out_count': 0,
            'home_doubtful_count': 0,
            'away_doubtful_count': 0,
            'impact_summary': ''
        }

        if not self.is_available:
            return result

        try:
            if match_id:
                raw = self.client.get_injuries(match_id=match_id)
            else:
                raw = self.client.get_injuries(
                    home_team=home_team, away_team=away_team
                )
        except RuntimeError:
            return result

        if raw and raw.get('available'):
            result['available'] = True
            result['home'] = raw.get('home', [])
            result['away'] = raw.get('away', [])
            result['fetched_at'] = raw.get('fetched_at')

            for side in ('home', 'away'):
                for p in result[side]:
                    status = p.get('status', '').lower()
                    if status == 'out' or status == 'suspended':
                        result[f'{side}_out_count'] += 1
                    elif status == 'doubtful':
                        result[f'{side}_doubtful_count'] += 1

            # 伤停影响简述
            parts = []
            if result['home_out_count']:
                parts.append(f"{home_team}缺阵{result['home_out_count']}人")
            if result['away_out_count']:
                parts.append(f"{away_team}缺阵{result['away_out_count']}人")
            if not parts:
                parts.append("双方主力齐整")
            result['impact_summary'] = '，'.join(parts)

        return result

    # ============================================
    # 赔率获取
    # ============================================

    def get_odds(self, home_team: str, away_team: str,
                 match_id: int = None) -> Dict:
        """获取实时赔率（BSD 源）

        Returns:
            {
                'available': bool,
                'home': float, 'draw': float, 'away': float,
                'implied_home': float, 'implied_draw': float, 'implied_away': float,
                'vig': float,
                'source': 'BSD' | 'unavailable'
            }
        """
        result = {
            'available': False,
            'home': None, 'draw': None, 'away': None,
            'implied_home': None, 'implied_draw': None, 'implied_away': None,
            'vig': None,
            'source': 'unavailable'
        }

        if not self.is_available:
            return result

        try:
            if match_id:
                raw = self.client.get_odds(match_id=match_id)
            else:
                raw = self.client.get_odds(
                    home_team=home_team, away_team=away_team
                )
        except RuntimeError:
            return result

        if raw and raw.get('home'):
            result['available'] = True
            result['home'] = raw['home']
            result['draw'] = raw['draw']
            result['away'] = raw['away']
            result['source'] = 'BSD'

            # 计算隐含概率（去 vig）
            imp = [1.0 / raw[k] for k in ('home', 'draw', 'away')]
            total = sum(imp)
            result['implied_home'] = round(imp[0] / total * 100, 1)
            result['implied_draw'] = round(imp[1] / total * 100, 1)
            result['implied_away'] = round(imp[2] / total * 100, 1)
            result['vig'] = round((total - 1) * 100, 1)

        return result

    # ============================================
    # 全量数据获取（一次调用拿到全部）
    # ============================================

    def get_full_match_data(self, home_team: str, away_team: str,
                            match_id: int = None) -> Dict:
        """获取单场比赛的全部实时数据

        Returns:
            {
                'lineups': {...},
                'injuries': {...},
                'odds': {...},
                'fetched_at': str
            }
        """
        return {
            'lineups': self.get_lineups(home_team, away_team, match_id),
            'injuries': self.get_injuries(home_team, away_team, match_id),
            'odds': self.get_odds(home_team, away_team, match_id),
            'fetched_at': time.strftime('%Y-%m-%d %H:%M:%S')
        }

    # ============================================
    # 数据健康检查
    # ============================================

    def health_check(self) -> Dict:
        """检查 BSD API 连通性"""
        if not self.is_available:
            return {'status': 'no_key', 'message': 'BSD_API_KEY 未配置'}

        try:
            events = self.client.get_events()
            return {
                'status': 'ok',
                'matches_available': len(events),
                'message': f'正常，可获取 {len(events)} 场比赛数据'
            }
        except RuntimeError as e:
            return {'status': 'error', 'message': str(e)}


if __name__ == '__main__':
    fetcher = LiveDataFetcher()

    print("=== LiveDataFetcher 自检 ===\n")

    # 健康检查
    health = fetcher.health_check()
    print(f"BSD API: {health['status']} — {health['message']}")

    if health['status'] != 'ok':
        print("\n⚠️ 请先注册 BSD API 并设置环境变量:")
        print("  1. 访问 https://sports.bzzoiro.com/")
        print("  2. 获取 API Key")
        print("  3. export BSD_API_KEY='your_key'")
    else:
        # 测试全量数据获取
        events = fetcher.client.get_events()
        if events:
            first = events[0]
            home = first.get('home_team', '')
            away = first.get('away_team', '')
            print(f"\n首场比赛: {home} vs {away}")

            full = fetcher.get_full_match_data(home, away)
            print(f"  阵容: {'✅' if full['lineups']['available'] else '❌ 暂无'}")
            print(f"  伤停: {'✅' if full['injuries']['available'] else '❌ 暂无'}")
            if full['injuries']['available']:
                print(f"    {full['injuries']['impact_summary']}")
            print(f"  赔率: {'✅' if full['odds']['available'] else '❌ 暂无'}")
            if full['odds']['available']:
                print(f"    主{full['odds']['home']} 平{full['odds']['draw']} 客{full['odds']['away']}")
