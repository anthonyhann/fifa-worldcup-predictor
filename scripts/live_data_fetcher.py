"""
实时数据获取与整合层 v2.0
数据源切换: BSD API → worldcup2026 API (开源免费) + WebSearch 消息面
整合三路数据:
1. 实时比分 (worldcup2026)  → 赛后复盘的权威比分来源
2. 首发阵容 (WebSearch)     → 来自新闻搜索的阵容/伤停信息
3. 实时赔率 (odds_fetcher)  → 博彩网站赔率抓取
"""

import json
import os
import time
from typing import Dict, List, Optional, Tuple

from wc2026_client import WC2026Client


class LiveDataFetcher:
    """实时数据统一获取层 v2.0

    数据来源:
    - worldcup2026 API: 实时比分、进球者、赛程、积分榜 (免 Key)
    - WebSearch: 首发阵容、伤停报告（通过 research_data 参数传入）
    - odds_fetcher: 赔率（独立模块）
    """

    def __init__(self, cache_dir: str = None):
        self.wc_client = WC2026Client(cache_dir=cache_dir)
        self._data_dir = cache_dir or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), '..', 'data'
        )

    @property
    def is_available(self) -> bool:
        """worldcup2026 API 是否可用（总是尝试连接，首次自动注册）"""
        return self.wc_client.is_available

    # ============================================
    # 实时比分（worldcup2026 API — 核心能力）
    # ============================================

    def get_live_score(self, home_team: str, away_team: str) -> Dict:
        """获取实时比分（用于赛后复盘）

        Returns:
            {
                'available': bool,
                'home_score': int,
                'away_score': int,
                'home_scorers': [{'name': str, 'time': int}],
                'away_scorers': [{'name': str, 'time': int}],
                'status': 'upcoming' | 'live' | 'finished',
                'time_elapsed': str,
                'fetched_at': str,
                'source': 'worldcup2026'
            }
        """
        result = {
            'available': False,
            'home_score': None,
            'away_score': None,
            'home_scorers': [],
            'away_scorers': [],
            'status': 'upcoming',
            'time_elapsed': '',
            'source': 'unavailable'
        }

        if not self.is_available:
            return result

        raw = self.wc_client.get_live_score(home_team, away_team)
        if raw:
            result.update(raw)
            result['available'] = True
            result['source'] = 'worldcup2026'

        return result

    def get_all_games(self) -> List[Dict]:
        """获取全部比赛"""
        if not self.is_available:
            return []
        return self.wc_client.get_games()

    # ============================================
    # 积分榜（worldcup2026 API）
    # ============================================

    def get_group_standings(self) -> Dict[str, List[Dict]]:
        """获取按小组名索引的积分榜"""
        if not self.is_available:
            return {}
        return self.wc_client.get_standings_dict()

    def get_match_context(self, home_team: str, away_team: str) -> Dict:
        """获取比赛的赛事上下文（小组+积分榜+出线形势）

        Returns:
            {
                'group': str,
                'matchday': int,
                'stadium': str,
                'home_standings': {...},
                'away_standings': {...},
                'importance': 'high' | 'medium' | 'low'
            }
        """
        result = {
            'group': None,
            'matchday': None,
            'stadium': None,
            'home_standings': None,
            'away_standings': None,
            'importance': 'medium'
        }

        if not self.is_available:
            return result

        game = self.wc_client.find_game(home_team, away_team)
        if game:
            result['group'] = game.get('group')
            result['matchday'] = game.get('matchday')
            stalist = self.wc_client.get_stadiums()
            sid = game.get('stadium_id')
            if sid and stalist:
                for s in stalist:
                    if s.get('id') == sid or s.get('stadium_id') == sid:
                        result['stadium'] = s.get('name', s.get('name_en', ''))
                        break

        # 积分榜对比
        standings = self.get_group_standings()
        gname = result['group']
        if gname and gname in standings:
            teams = standings[gname]
            for t in teams:
                tn = (t.get('name_en') or t.get('name') or t.get('team') or '').lower()
                if home_team.lower() in tn:
                    result['home_standings'] = t
                if away_team.lower() in tn:
                    result['away_standings'] = t

        # 重要性判定
        if result.get('matchday') in [2, 3]:
            result['importance'] = 'high'
        elif result.get('matchday') == 1:
            result['importance'] = 'medium'

        return result

    # ============================================
    # 阵容获取（WebSearch — 通过 research_data 传入）
    # ============================================

    def get_lineups(self, home_team: str, away_team: str,
                    research_data: Dict = None) -> Dict:
        """获取首发阵容（优先使用 WebSearch 收集的数据）

        Args:
            research_data: WebSearch 收集的结构化消息面数据
                {
                    'lineups': {
                        'home': {'formation': '4-3-3', 'startXI': [...]},
                        'away': {...}
                    }
                }

        Returns:
            {
                'available': bool,
                'has_official': bool,
                'home': { 'formation': str, 'startXI': list },
                'away': { 'formation': str, 'startXI': list },
                'source': 'websearch' | 'unavailable'
            }
        """
        result = {
            'available': False,
            'has_official': True,  # WebSearch 来源的新闻通常是确认阵容
            'home': None,
            'away': None,
            'source': 'unavailable'
        }

        if research_data and 'lineups' in research_data:
            rd = research_data['lineups']
            result['home'] = rd.get('home') or rd.get(home_team)
            result['away'] = rd.get('away') or rd.get(away_team)
            if result['home'] or result['away']:
                result['available'] = True
                result['source'] = 'websearch'

        return result

    # ============================================
    # 伤停获取（WebSearch — 通过 research_data 传入）
    # ============================================

    def get_injuries(self, home_team: str, away_team: str,
                     research_data: Dict = None) -> Dict:
        """获取伤停报告

        Args:
            research_data: WebSearch 收集的结构化消息面数据
                {
                    'injuries': {
                        'home': [{name, reason, status}],
                        'away': [...]
                    }
                }

        Returns:
            {
                'available': bool,
                'home': [...], 'away': [...],
                'home_out_count': int, 'away_out_count': int,
                'impact_summary': str
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

        if research_data and 'injuries' in research_data:
            rd = research_data['injuries']
            result['home'] = rd.get('home', []) or []
            result['away'] = rd.get('away', []) or []
            result['available'] = bool(result['home'] or result['away'])

            for side in ('home', 'away'):
                for p in result[side]:
                    status = (p.get('status') or '').lower()
                    if status in ('out', 'suspended'):
                        result[f'{side}_out_count'] += 1
                    elif status == 'doubtful':
                        result[f'{side}_doubtful_count'] += 1

            parts = []
            if result['home_out_count']:
                parts.append(f"{home_team}缺阵{result['home_out_count']}人")
            if result['away_out_count']:
                parts.append(f"{away_team}缺阵{result['away_out_count']}人")
            if result['home_doubtful_count']:
                parts.append(f"{home_team}{result['home_doubtful_count']}人存疑")
            if result['away_doubtful_count']:
                parts.append(f"{away_team}{result['away_doubtful_count']}人存疑")
            if not parts:
                parts.append("双方主力齐整")
            result['impact_summary'] = '，'.join(parts)

        return result

    # ============================================
    # 赔率获取（独立 — 从 odds_fetcher 传入）
    # ============================================

    def get_odds(self, home_team: str, away_team: str,
                 odds_data: Dict = None) -> Dict:
        """获取赔率（从 odds_fetcher 或 WebSearch 传入）

        Returns:
            {
                'available': bool,
                'home': float, 'draw': float, 'away': float,
                'implied_home': float, 'implied_draw': float, 'implied_away': float,
                'vig': float,
                'source': 'odds_fetcher' | 'unavailable'
            }
        """
        result = {
            'available': False,
            'home': None, 'draw': None, 'away': None,
            'implied_home': None, 'implied_draw': None, 'implied_away': None,
            'vig': None,
            'source': 'unavailable'
        }

        if odds_data and odds_data.get('home'):
            result['available'] = True
            result['home'] = odds_data['home']
            result['draw'] = odds_data['draw']
            result['away'] = odds_data['away']
            result['source'] = 'odds_fetcher'

            # 计算隐含概率（去 vig）
            imp = [1.0 / odds_data[k] for k in ('home', 'draw', 'away')]
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
                            research_data: Dict = None,
                            odds_data: Dict = None) -> Dict:
        """获取单场比赛的全部实时数据

        Returns:
            {
                'scores': {...},       # worldcup2026 API
                'lineups': {...},      # WebSearch
                'injuries': {...},     # WebSearch
                'odds': {...},         # odds_fetcher
                'context': {...},      # worldcup2026 API (小组/积分榜)
                'fetched_at': str
            }
        """
        return {
            'scores': self.get_live_score(home_team, away_team),
            'lineups': self.get_lineups(home_team, away_team, research_data),
            'injuries': self.get_injuries(home_team, away_team, research_data),
            'odds': self.get_odds(home_team, away_team, odds_data),
            'context': self.get_match_context(home_team, away_team),
            'fetched_at': time.strftime('%Y-%m-%d %H:%M:%S')
        }

    # ============================================
    # 赛后复盘专用：拉开奖结果
    # ============================================

    def get_match_result(self, home_team: str, away_team: str) -> Dict:
        """获取比赛最终结果（赛后复盘用，仅返回真正有比分的比赛）

        Returns:
            {
                'available': bool,
                'home_score': int, 'away_score': int,
                'winner': 'home' | 'away' | 'draw' | None,
                'home_scorers': [...], 'away_scorers': [...],
                'source': 'worldcup2026'
            }
        """
        score = self.get_live_score(home_team, away_team)
        if not score['available'] or score['status'] != 'finished':
            return {'available': False, 'source': 'unavailable'}

        hs = score.get('home_score', 0) or 0
        aws = score.get('away_score', 0) or 0

        # 仅当有真实比分时才返回
        if hs == 0 and aws == 0:
            return {'available': False, 'source': 'unavailable', 
                    'reason': 'no_score_data'}

        winner = None
        if hs > aws:
            winner = 'home'
        elif aws > hs:
            winner = 'away'
        else:
            winner = 'draw'

        return {
            'available': True,
            'home_score': hs,
            'away_score': aws,
            'winner': winner,
            'home_scorers': score.get('home_scorers', []),
            'away_scorers': score.get('away_scorers', []),
            'fetched_at': time.strftime('%Y-%m-%d %H:%M:%S'),
            'source': 'worldcup2026'
        }

    # ============================================
    # 数据健康检查
    # ============================================

    def health_check(self) -> Dict:
        """检查 worldcup2026 API 连通性"""
        if not self.is_available:
            return {
                'status': 'no_connection',
                'message': 'worldcup2026 API 不可用，请检查 https://worldcup26.ir/health',
                'detail': 'API 免 Key，首次运行自动注册'
            }

        games = self.get_all_games()
        groups = self.get_group_standings()

        return {
            'status': 'ok',
            'matches_cached': len(games),
            'groups_available': len(groups),
            'message': f'正常，{len(groups)} 组积分榜 + 近期比分可用',
            'source': 'worldcup2026 (免认证)'
        }


if __name__ == '__main__':
    fetcher = LiveDataFetcher()

    print("=== LiveDataFetcher v2.1 自检 ===\n")

    # 健康检查
    health = fetcher.health_check()
    print(f"worldcup2026 API: {health['status']} — {health['message']}")
    print(f"  source: {health.get('source', '?')}")

    if health['status'] != 'ok':
        print("\n⚠️ worldcup2026 API 暂不可用")
        print("   API 地址: https://worldcup26.ir")
        print("   GET端点免认证")
        print("   消息面数据（WebSearch）仍可正常工作")
    else:
        # 测试积分榜
        print("\n--- 积分榜 ---")
        standings = fetcher.get_group_standings()
        for g, teams in sorted(standings.items())[:3]:
            print(f"  Group {g}:")
            for t in teams[:2]:
                name = t.get('_name', t.get('name_en', '?'))
                pts = t.get('pts', t.get('points', '?'))
                print(f"    {name}: {pts} pts")

        # 测试实时比分
        print("\n--- 实时比分测试 ---")
        score = fetcher.get_live_score('Argentina', 'Austria')
        if score['available']:
            print(f"  Argentina vs Austria: {score['home_score']}-{score['away_score']} [{score['status']}]")
        else:
            print(f"  Argentina vs Austria: 比赛未开始或未找到")

        # 测试赛后复盘
        print("\n--- 赛后复盘数据 ---")
        result = fetcher.get_match_result('Argentina', 'Algeria')
        if result['available']:
            print(f"  Argentina vs Algeria: {result['home_score']}-{result['away_score']} (胜者: {result['winner']})")
            if result.get('home_scorers'):
                scorers = ', '.join(s.get('name','?') for s in result['home_scorers'])
                print(f"    进球: {scorers}")
        else:
            print(f"  Argentina vs Algeria: 数据未获取")
