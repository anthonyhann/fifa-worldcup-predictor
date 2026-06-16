"""
BSD Free Football API 客户端 v1.0
封装 BSD API 的认证、请求、错误处理与本地缓存
API 地址: https://sports.bzzoiro.com/
"""

import json
import os
import time
import hashlib
from typing import Dict, List, Optional
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from urllib.parse import urlencode


class BSDClient:
    """BSD Free Football API 原始客户端"""

    BASE_URL = "https://sports.bzzoiro.com/api"
    WORLD_CUP_LEAGUE_ID = 27
    CACHE_TTL = {
        'lineups': 300,       # 阵容: 5分钟
        'injuries': 600,      # 伤停: 10分钟
        'odds': 60,           # 赔率: 1分钟
        'events': 30,         # 比分: 30秒
    }

    def __init__(self, api_key: str = None, cache_dir: str = None):
        self.api_key = api_key or os.getenv('BSD_API_KEY')
        self.cache_dir = cache_dir or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), '..', 'data'
        )
        self._cache_path = os.path.join(self.cache_dir, 'live_cache.json')
        self._cache = self._load_cache()

    # ============================================
    # 缓存层
    # ============================================

    def _load_cache(self) -> Dict:
        if os.path.exists(self._cache_path):
            try:
                with open(self._cache_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {}

    def _save_cache(self):
        os.makedirs(os.path.dirname(self._cache_path), exist_ok=True)
        with open(self._cache_path, 'w', encoding='utf-8') as f:
            json.dump(self._cache, f, ensure_ascii=False, indent=2)

    def _cache_key(self, endpoint: str, params: Dict = None) -> str:
        raw = endpoint
        if params:
            raw += '&'.join(f'{k}={v}' for k, v in sorted(params.items()))
        return hashlib.md5(raw.encode()).hexdigest()[:12]

    def _cache_get(self, key: str) -> Optional[Dict]:
        entry = self._cache.get(key)
        if not entry:
            return None
        if time.time() - entry.get('ts', 0) > entry.get('ttl', 60):
            return None
        return entry.get('data')

    def _cache_set(self, key: str, data: Dict, ttl: int):
        self._cache[key] = {'ts': time.time(), 'ttl': ttl, 'data': data}
        self._save_cache()

    # ============================================
    # HTTP 请求层
    # ============================================

    def _request(self, endpoint: str, params: Dict = None,
                 use_cache: bool = True, cache_ttl: int = 60) -> Dict:
        """通用 API 请求（带缓存）"""
        if not self.api_key:
            raise RuntimeError("BSD_API_KEY 未配置，请设置环境变量或传入 api_key 参数")

        if use_cache:
            key = self._cache_key(endpoint, params)
            cached = self._cache_get(key)
            if cached is not None:
                return cached

        url = f"{self.BASE_URL}{endpoint}"
        if params:
            url += '?' + urlencode(params)

        req = Request(url)
        req.add_header('Authorization', f'Token {self.api_key}')
        req.add_header('Accept', 'application/json')

        try:
            with urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode('utf-8'))
        except HTTPError as e:
            body = e.read().decode('utf-8') if e.fp else ''
            raise RuntimeError(f"BSD API 请求失败 [{e.code}]: {endpoint} — {body}")
        except URLError as e:
            raise RuntimeError(f"BSD API 网络错误: {endpoint} — {e.reason}")

        if use_cache:
            self._cache_set(key, data, cache_ttl)

        return data

    # ============================================
    # 比赛数据端点
    # ============================================

    def get_events(self, league_id: int = None) -> List[Dict]:
        """获取所有比赛事件（比分、阵容、伤停、赔率一体化）"""
        league_id = league_id or self.WORLD_CUP_LEAGUE_ID
        result = self._request(
            '/events/',
            params={'league': str(league_id)} if league_id else None,
            cache_ttl=self.CACHE_TTL['events']
        )
        if isinstance(result, dict) and 'results' in result:
            return result['results']
        if isinstance(result, list):
            return result
        return [result] if result else []

    def get_event(self, match_id: int) -> Dict:
        """获取单场比赛详情"""
        return self._request(
            f'/events/{match_id}/',
            cache_ttl=self.CACHE_TTL['events']
        )

    # ============================================
    # 阵容数据
    # ============================================

    def get_lineups(self, match_id: int = None,
                    home_team: str = None, away_team: str = None) -> Optional[Dict]:
        """获取首发阵容

        用法一: get_lineups(match_id=42) → 按ID查
        用法二: get_lineups(home_team='Argentina', away_team='France') → 按队名查
        """
        if match_id:
            event = self.get_event(match_id)
            return self._extract_lineups(event)

        if home_team and away_team:
            events = self.get_events()
            for ev in events:
                ht = (ev.get('home_team') or '').lower()
                at = (ev.get('away_team') or '').lower()
                if home_team.lower() in ht and away_team.lower() in at:
                    return self._extract_lineups(ev)

        return None

    def _extract_lineups(self, event: Dict) -> Optional[Dict]:
        """从事件数据中提取阵容信息"""
        lineup = event.get('lineup')
        if not lineup:
            return None

        result = {'available': False, 'home': None, 'away': None}

        if 'home' in lineup and lineup['home']:
            result['home'] = self._parse_lineup_side(lineup['home'])
        if 'away' in lineup and lineup['away']:
            result['away'] = self._parse_lineup_side(lineup['away'])

        result['available'] = bool(result['home'] or result['away'])
        result['fetched_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
        return result

    def _parse_lineup_side(self, side: Dict) -> Dict:
        return {
            'formation': side.get('formation', 'unknown'),
            'startXI': side.get('startXI', []),
            'substitutes': side.get('substitutes', []),
            'player_count': len(side.get('startXI', []))
        }

    # ============================================
    # 伤停数据
    # ============================================

    def get_injuries(self, match_id: int = None,
                     home_team: str = None, away_team: str = None) -> Optional[Dict]:
        """获取伤停信息（受伤/停赛/存疑）"""
        if match_id:
            event = self.get_event(match_id)
            return self._extract_injuries(event)

        if home_team and away_team:
            events = self.get_events()
            for ev in events:
                ht = (ev.get('home_team') or '').lower()
                at = (ev.get('away_team') or '').lower()
                if home_team.lower() in ht and away_team.lower() in at:
                    return self._extract_injuries(ev)

        return None

    def _extract_injuries(self, event: Dict) -> Optional[Dict]:
        """从事件数据中提取伤停信息"""
        unavailable = event.get('unavailable_players')
        if not unavailable:
            return {'available': False, 'home': [], 'away': []}

        result = {'available': True}

        for side in ('home', 'away'):
            players = unavailable.get(side, [])
            result[side] = []
            for p in players:
                result[side].append({
                    'name': p.get('name', 'unknown'),
                    'reason': p.get('reason', 'unknown'),
                    'status': p.get('status', 'unknown'),  # Out / Doubtful / Suspended
                    'position': p.get('position', '')
                })

        result['fetched_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
        return result

    # ============================================
    # 赔率数据
    # ============================================

    def get_odds(self, match_id: int = None,
                 home_team: str = None, away_team: str = None) -> Optional[Dict]:
        """获取实时赔率（主/平/客 + 多家博彩公司对比）"""
        if match_id:
            event = self.get_event(match_id)
            return self._extract_odds(event)

        if home_team and away_team:
            events = self.get_events()
            for ev in events:
                ht = (ev.get('home_team') or '').lower()
                at = (ev.get('away_team') or '').lower()
                if home_team.lower() in ht and away_team.lower() in at:
                    return self._extract_odds(ev)

        return None

    def _extract_odds(self, event: Dict) -> Optional[Dict]:
        """从事件数据中提取赔率信息"""
        odds_data = {
            'home_team': event.get('home_team', ''),
            'away_team': event.get('away_team', ''),
            'source': 'BSD',
            'fetched_at': time.strftime('%Y-%m-%d %H:%M:%S'),
        }

        # BSD 直接在事件中嵌入赔率
        for key in ('odds_home', 'odds_draw', 'odds_away'):
            if key in event and event[key] is not None:
                odds_data[key.replace('odds_', '')] = float(event[key])

        if 'home' in odds_data:
            return odds_data
        return None

    def get_best_odds(self, match_id: int) -> Optional[Dict]:
        """获取各盘口最优赔率"""
        try:
            return self._request(
                '/odds/best/',
                params={'match': str(match_id)},
                cache_ttl=self.CACHE_TTL['odds']
            )
        except RuntimeError:
            return None


if __name__ == '__main__':
    import sys
    client = BSDClient()

    if not client.api_key:
        print("⚠️ BSD_API_KEY 未设置，跳过测试")
        print("获取 Key: https://sports.bzzoiro.com/")
        print("设置: export BSD_API_KEY='your_key_here'")
        sys.exit(0)

    print("=== BSD API 连通性测试 ===\n")

    # 测试事件列表
    try:
        events = client.get_events()
        print(f"✅ 获取到 {len(events)} 场比赛")

        if events:
            first = events[0]
            home = first.get('home_team', '?')
            away = first.get('away_team', '?')
            print(f"  首场: {home} vs {away}")

            # 检测阵容
            lineups = client._extract_lineups(first)
            print(f"  阵容可用: {lineups['available'] if lineups else '❌ 无'}")

            # 检测伤停
            injuries = client._extract_injuries(first)
            if injuries and injuries['available']:
                home_inj = len(injuries.get('home', []))
                away_inj = len(injuries.get('away', []))
                print(f"  伤停: 主队{home_inj}人 / 客队{away_inj}人")

            # 检测赔率
            odds = client._extract_odds(first)
            if odds:
                print(f"  赔率: 主{odds.get('home','?')} 平{odds.get('draw','?')} 客{odds.get('away','?')}")
    except RuntimeError as e:
        print(f"❌ {e}")
