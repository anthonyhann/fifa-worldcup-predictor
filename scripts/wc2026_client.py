"""
worldcup2026 REST API 客户端 v1.2
封装 https://github.com/rezarahiminia/worldcup2026 的开源 API
提供: 实时比分、进球者、赛程、积分榜、球队信息
API 地址: https://worldcup26.ir
特点: 读端点无需认证, 无 API Key
"""

import json
import os
import time
import hashlib
from typing import Dict, List, Optional
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


class WC2026Client:
    """worldcup2026 免费 REST API 客户端 v1.2

    数据覆盖: 48球队 / 12小组积分榜 / 104场比赛(含比分+进球者) / 16球场
    全量 /get/games 可用 (~50KB, 需30s超时)
    """

    BASE_URL = "https://worldcup26.ir"
    API_TIMEOUT = 35  # /get/games 全量需较长超时
    CACHE_TTL = {
        'games': 30,          # 比分: 30秒
        'teams': 86400,       # 球队: 1天
        'groups': 60,         # 积分榜: 1分钟
        'stadiums': 86400,    # 球场: 1天
    }

    def __init__(self, cache_dir: str = None):
        self.cache_dir = cache_dir or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), '..', 'data'
        )
        self._cache_path = os.path.join(self.cache_dir, 'wc2026_cache.json')
        self._cache = self._load_cache()

    @property
    def is_available(self) -> bool:
        return True

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

    def _cache_key(self, endpoint: str) -> str:
        return hashlib.md5(endpoint.encode()).hexdigest()[:12]

    def _cache_get(self, key: str) -> Optional:
        e = self._cache.get(key)
        if e and time.time() - e.get('ts', 0) < e.get('ttl', 60):
            return e.get('data')
        return None

    def _cache_set(self, key: str, data, ttl: int):
        self._cache[key] = {'ts': time.time(), 'ttl': ttl, 'data': data}
        self._save_cache()

    # ============================================
    # HTTP
    # ============================================
    def _request(self, endpoint: str, use_cache: bool = True,
                 cache_ttl: int = 60, timeout: int = None) -> Optional:
        """GET 请求（免认证）"""
        if use_cache:
            key = self._cache_key(endpoint)
            c = self._cache_get(key)
            if c is not None:
                return c

        timeout = timeout or self.API_TIMEOUT if 'games' in endpoint else 15
        url = f"{self.BASE_URL}{endpoint}"
        
        try:
            req = Request(url)
            req.add_header('Accept', 'application/json')
            with urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode('utf-8'))
            
            if use_cache:
                self._cache_set(self._cache_key(endpoint), data, cache_ttl)
            return data
        except Exception:
            return None

    # ============================================
    # 数据端点
    # ============================================
    def get_teams(self) -> List[Dict]:
        d = self._request('/get/teams', cache_ttl=self.CACHE_TTL['teams'])
        if isinstance(d, list): return d
        return d.get('teams', []) if d else []

    def get_groups(self) -> List[Dict]:
        d = self._request('/get/groups', cache_ttl=self.CACHE_TTL['groups'])
        if isinstance(d, list): return d
        return d.get('groups', []) if d else []

    def get_stadiums(self) -> List[Dict]:
        d = self._request('/get/stadiums', cache_ttl=self.CACHE_TTL['stadiums'])
        if isinstance(d, list): return d
        return d.get('stadiums', []) if d else []

    def get_games(self) -> List[Dict]:
        """获取全部 104 场比赛（~50KB, 30s超时）"""
        d = self._request('/get/games', cache_ttl=self.CACHE_TTL['games'])
        if isinstance(d, list): return d
        return d.get('games', d.get('data', [])) if d else []

    # ============================================
    # 查询
    # ============================================
    def find_game(self, home_team: str, away_team: str) -> Optional[Dict]:
        """按队名找比赛"""
        games = self.get_games()
        h = home_team.lower().strip()
        a = away_team.lower().strip()
        
        # 别名映射
        ALIASES = {
            'south korea': 'south korea', 'korea': 'south korea',
            'czech': 'czech republic', 'ivory coast': 'ivory coast',
            'bosnia': 'bosnia and herzegovina',
            'dr congo': 'democratic republic of the congo',
            'congo': 'democratic republic of the congo',
            'usa': 'united states', 'us': 'united states',
            'ksa': 'saudi arabia', 'curacao': 'curaçao',
            'cape verde': 'cape verde', 'nz': 'new zealand',
        }
        
        for g in games:
            gh = (g.get('home_team_name_en') or '').lower().strip()
            ga = (g.get('away_team_name_en') or '').lower().strip()
            
            # 双方向匹配 + 别名
            home_match = (h in gh or gh in h or ALIASES.get(h) == gh)
            away_match = (a in ga or ga in a or ALIASES.get(a) == ga)
            
            if home_match and away_match:
                return g
            
            # 反向匹配
            home_match2 = (h in ga or ga in h or ALIASES.get(h) == ga)
            away_match2 = (a in gh or gh in a or ALIASES.get(a) == gh)
            if home_match2 and away_match2:
                return g
        
        return None

    def _to_int(self, val) -> int:
        """安全转int（处理字符串分数）"""
        if val is None:
            return 0
        try:
            return int(val)
        except (ValueError, TypeError):
            return 0

    def _parse_scorers(self, raw) -> List[Dict]:
        """解析进球者（可能是字符串列表或结构化列表）"""
        if not raw:
            return []
        result = []
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict):
                    result.append(item)
                elif isinstance(item, str):
                    # "Player Name 45'" format
                    result.append({'name': item})
        return result

    def get_live_score(self, home_team: str, away_team: str) -> Optional[Dict]:
        """获取实时比分（仅返回真正有比分的比赛）"""
        game = self.find_game(home_team, away_team)
        if not game:
            return None

        hs = self._to_int(game.get('home_score'))
        aws = self._to_int(game.get('away_score'))
        finished = game.get('finished')
        
        # 只信任真有比分或明确标记 finished 且有非零比分的比赛
        is_real_result = (finished and (hs > 0 or aws > 0))
        is_truly_live = (not finished and game.get('time_elapsed') and 
                        game.get('time_elapsed') != 'finished')
        
        status = 'upcoming'
        if is_real_result:
            status = 'finished'
        elif is_truly_live:
            status = 'live'
        else:
            status = 'upcoming'  # API 可能错误标记为 finished 但无真实比分

        return {
            'game_id': game.get('id', game.get('_id', '')),
            'home_team': game.get('home_team_name_en', home_team),
            'away_team': game.get('away_team_name_en', away_team),
            'home_score': hs,
            'away_score': aws,
            'home_scorers': self._parse_scorers(game.get('home_scorers')),
            'away_scorers': self._parse_scorers(game.get('away_scorers')),
            'status': status,
            'time_elapsed': game.get('time_elapsed', ''),
            'group': game.get('group', ''),
            'matchday': game.get('matchday', ''),
            'stadium_id': game.get('stadium_id', ''),
            'local_date': game.get('local_date', ''),
            'fetched_at': time.strftime('%Y-%m-%d %H:%M:%S'),
            'source': 'worldcup2026'
        }

    def get_standings_dict(self) -> Dict[str, List[Dict]]:
        """按小组名索引的积分榜"""
        groups = self.get_groups()
        teams = self.get_teams()
        
        id_to_name = {}
        for t in teams:
            tid = str(t.get('id', ''))
            if tid:
                id_to_name[tid] = t.get('name_en', '')
        
        result = {}
        for g in groups:
            name = g.get('name', '?')
            td = g.get('teams', g.get('standings', []))
            for t in td:
                tid = str(t.get('team_id', ''))
                t['_name'] = id_to_name.get(tid, f'#{tid}')
            result[name] = td
        
        return result


if __name__ == '__main__':
    import sys
    client = WC2026Client()
    print("=== worldcup2026 API v1.2 ===\n")

    # Teams
    teams = client.get_teams()
    print(f"Teams: {len(teams)}")

    # Standings
    standings = client.get_standings_dict()
    print(f"Groups: {len(standings)}")
    for g in ['A', 'B']:
        if g in standings:
            print(f"  Group {g}:")
            for t in standings[g][:3]:
                print(f"    {t['_name']}: {t.get('pts','?')}pts {t.get('w','?')}W {t.get('d','?')}D {t.get('l','?')}L")

    # Find game
    print("\nFind Argentina vs Austria:")
    g = client.find_game('Argentina', 'Austria')
    if g:
        print(f"  Found: ID={g.get('id')}, Group={g.get('group')}, Matchday={g.get('matchday')}, {g.get('home_team_name_en')} {g.get('home_score')}-{g.get('away_score')} {g.get('away_team_name_en')}")
    
    # Live scores for past games
    print("\nLive scores (finished):")
    for (h, a) in [('Mexico', 'South Africa'), ('France', 'Senegal'), ('Argentina', 'Algeria')]:
        s = client.get_live_score(h, a)
        if s:
            print(f"  {s['home_team']} {s['home_score']}-{s['away_score']} {s['away_team']} [{s['status']}]")
