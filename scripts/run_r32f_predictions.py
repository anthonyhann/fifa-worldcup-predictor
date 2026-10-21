#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R32f 双场预测与投注方案生成 (巴西 vs 挪威, 墨西哥 vs 英格兰)"""
import os
import sys
import json
import math
from datetime import datetime

# Add skill scripts to path
SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT_DIR = os.path.join(SKILL_DIR, 'scripts')
sys.path.insert(0, SCRIPT_DIR)

from prediction_engine import FootballPredictionEngine

OUTPUT_MD = os.path.join(SKILL_DIR, 'outputs', 'r32f_predictions_and_bets.md')
OUTPUT_JSON = os.path.join(SKILL_DIR, 'outputs', 'r32f_predictions.json')

# 比分赔率来自用户截图，已人工校验转录
ODDS = {
    ('巴西', '挪威'): {
        '1:0': 8.75, '2:0': 9.25, '2:1': 4.85, '3:0': 18.00, '3:1': 10.00,
        '3:2': 13.50, '4:0': 38.00, '4:1': 30.00, '4:2': 42.00, '5:0': 90.00,
        '5:1': 75.00, '5:2': 90.00, '胜其它': 46.00,
        '0:0': 16.00, '1:1': 7.00, '2:2': 9.00, '3:3': 30.00, '平其它': 175.0,
        '0:1': 19.00, '0:2': 35.00, '1:2': 13.50, '0:3': 90.00, '1:3': 48.00,
        '2:3': 43.00, '0:4': 200.0, '1:4': 125.0, '2:4': 100.0, '0:5': 600.0,
        '1:5': 500.0, '2:5': 350.0, '负其它': 125.0,
    },
    ('墨西哥', '英格兰'): {
        '1:0': 9.35, '2:0': 16.00, '2:1': 10.00, '3:0': 55.00, '3:1': 38.00,
        '3:2': 55.00, '4:0': 200.0, '4:1': 150.0, '4:2': 200.0, '5:0': 600.0,
        '5:1': 500.0, '5:2': 500.0, '胜其它': 300.0,
        '0:0': 8.25, '1:1': 5.00, '2:2': 12.00, '3:3': 60.00, '平其它': 300.0,
        '0:1': 6.30, '0:2': 9.50, '1:2': 6.00, '0:3': 23.00, '1:3': 17.00,
        '2:3': 50.00, '0:4': 75.00, '1:4': 75.00, '2:4': 75.00, '0:5': 200.0,
        '1:5': 200.0, '2:5': 250.0, '负其它': 150.0,
    }
}

MATCHES = [
    ('巴西', '挪威', 'knockout_stage', '091', '2026-07-06 04:00 CST', '新泽西', '多云', '29°C',
     ['小组赛: 1-1 摩洛哥', '3-0 海地', '3-0 苏格兰 (客场)', 'R32: 2-1 日本'],
     ['小组赛: 4-1 伊拉克 (客场)', '3-2 塞内加尔', '1-4 法国', 'R32: 2-1 科特迪瓦']),
    ('墨西哥', '英格兰', 'knockout_stage', '092', '2026-07-06 06:00 CST', '墨西哥城', '小雨', '17°C',
     ['小组赛: 2-0 南非', '1-0 韩国', '3-0 捷克', 'R32: 2-0 厄瓜多尔'],
     ['小组赛: 4-2 克罗地亚', '0-0 加纳', '2-0 巴拿马', 'R32: 2-1 刚果(金)']),
]


def poisson_prob(lam, k):
    return math.exp(-lam) * (lam ** k) / math.factorial(k)


def total_goals_distribution(pred):
    xg_a, xg_b = pred['xg_a'], pred['xg_b']
    dist = {}
    for k in range(8):
        p = 0.0
        for i in range(k + 1):
            p += poisson_prob(xg_a, i) * poisson_prob(xg_b, k - i)
        dist[k] = round(p * 100, 1)
    p7 = 0.0
    for k in range(8, 12):
        for i in range(k + 1):
            p7 += poisson_prob(xg_a, i) * poisson_prob(xg_b, k - i)
    dist['7+'] = round(p7 * 100, 1)
    return dist


def htft_distribution(pred):
    xg_a, xg_b = pred['xg_a'], pred['xg_b']
    ht_a, ht_b = xg_a * 0.45, xg_b * 0.45
    fh_a, fh_b = xg_a * 0.55, xg_b * 0.55
    probs = {}
    for a1 in range(6):
        for b1 in range(6):
            p1 = poisson_prob(ht_a, a1) * poisson_prob(ht_b, b1)
            s1 = 'A' if a1 > b1 else 'B' if b1 > a1 else 'D'
            for a2 in range(6):
                for b2 in range(6):
                    p2 = poisson_prob(fh_a, a2) * poisson_prob(fh_b, b2)
                    ta, tb = a1 + a2, b1 + b2
                    s2 = 'A' if ta > tb else 'B' if tb > ta else 'D'
                    k = f'{s1}/{s2}'
                    probs[k] = probs.get(k, 0) + p1 * p2
    return {k: round(v * 100, 1) for k, v in sorted(probs.items(), key=lambda x: -x[1])}


def score_probabilities(pred, odds_map):
    matrix = engine.poisson_matrix(pred['xg_a'], pred['xg_b'], max_goals=7)
    result = []
    for score, p in matrix['score_probs'].items():
        key = score.replace('-', ':')
        if key in odds_map:
            result.append((key, p, odds_map[key], round(p * odds_map[key] / 100, 3)))
    result.sort(key=lambda x: -x[1])
    return result


def label_htft(code, home, away):
    m = {'A': home, 'D': '平', 'B': away}
    a, b = code.split('/')
    return f'{m[a]}/{m[b]}'


def implied_over_under_25(odds_map):
    invs = {s: 1.0 / o for s, o in odds_map.items() if ':' in s}
    total = sum(invs.values())
    over = sum(v for s, v in invs.items() if sum(map(int, s.split(':'))) >= 3)
    under = sum(v for s, v in invs.items() if sum(map(int, s.split(':'))) <= 2)
    return {
        'over_pct': round(over / total * 100, 1),
        'under_pct': round(under / total * 100, 1),
        'vig_pct': round((total - 1) * 100, 1)
    }


def format_score_parlay(scores_a, scores_b):
    lines = []
    total_hit = (sum(x[1] for x in scores_a) / 100) * (sum(y[1] for y in scores_b) / 100)
    combos = []
    for x in scores_a:
        for y in scores_b:
            combo_odds = round(x[2] * y[2], 2)
            combo_p = x[1] * y[1] / 10000
            combos.append((x[0], y[0], combo_odds, combo_p))
    combos.sort(key=lambda c: -c[3])
    for sa, sb, co, cp in combos:
        p_str = f'{cp:.2%}' if cp >= 0.0001 else '<0.01%'
        lines.append(f'  - 巴西 {sa} × 墨西哥 {sb} | 赔率 {co}x | 单注命中概率 {p_str}')
    return lines, total_hit, len(combos)


def main():
    global engine
    engine = FootballPredictionEngine(data_dir=os.path.join(SKILL_DIR, 'data'))
    predictions = {}
    report = []

    report.append('# 📊 R32f 双场预测与二串一投注报告')
    report.append(f'引擎版本: v4.8 (KO主导胜上限 + 高Elo缓冲 + 首次KO黑马)')
    report.append(f'数据时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    report.append('数据源:')
    report.append('- 26worldcup.github.io — 赛程/比分/积分榜/球场天气 (静态PWA，免认证)')
    report.append('- worldcup26.ir — 赛程/实时比分交叉验证 (免认证 REST API)')
    report.append('- kickoffapi.com / api-football.com — 未启用 (需 API Key / 赔率需付费套餐)')
    report.append('比分赔率: 来自用户截图，已人工转录校验')
    report.append('')
    report.append('赛程确认:')
    report.append('- 091 巴西 vs 挪威 | 07-06 04:00 CST | R16 | 新泽西 多云 29°C')
    report.append('- 092 墨西哥 vs 英格兰 | 07-06 06:00 CST | 墨西哥城 小雨 17°C')
    report.append('')

    json_out = {
        'generated_at': datetime.now().isoformat(),
        'engine_version': 'v4.8',
        'data_sources': ['26worldcup.github.io', 'worldcup26.ir'],
        'matches': []
    }

    for idx, match in enumerate(MATCHES):
        if len(match) == 8:
            team_a, team_b, rnd, num, dt, stadium, weather, temp, form_a = match
            form_b = []
        else:
            team_a, team_b, rnd, num, dt, stadium, weather, temp, form_a, form_b = match

        pred = engine.predict(team_a, team_b, is_knockout=True, tournament_round=rnd)
        predictions[(team_a, team_b)] = pred

        f = pred['final']
        xg_a, xg_b = pred['xg_a'], pred['xg_b']
        elo_a, elo_b = pred['elo_a'], pred['elo_b']

        enh = pred['enhancements']
        applied = []
        if enh.get('host_effect_applied'):
            applied.append('东道主效应')
        if enh.get('superstar_effect_applied'):
            applied.append('球星加成')
        if enh.get('balanced_xg_boost_applied'):
            applied.append('均势xG爆发')
        if enh.get('high_elo_gap_buffer_applied'):
            applied.append('高Elo爆冷缓冲')
        if enh.get('first_ko_debut_boost_applied'):
            applied.append('首次KO黑马')
        applied_str = ', '.join(applied) if applied else '无'

        totals = total_goals_distribution(pred)
        htft = htft_distribution(pred)
        score_probs = score_probabilities(pred, ODDS[(team_a, team_b)])
        over_under = implied_over_under_25(ODDS[(team_a, team_b)])

        report.append('---')
        report.append(f'## ⚽ {num} {team_a} vs {team_b}')
        report.append('')
        report.append(f'**赛事信息**: {dt} | {stadium} | {weather} {temp}')
        report.append(f'**近期走势**')
        report.append(f'- {team_a}: ' + '；'.join(form_a))
        if form_b:
            report.append(f'- {team_b}: ' + '；'.join(form_b))
        report.append('')
        report.append(f'**基础数据**')
        report.append(f'- Elo: {team_a} {elo_a} vs {team_b} {elo_b} (差 {elo_a - elo_b})')
        report.append(f'- xG: {team_a} {xg_a:.2f} vs {team_b} {xg_b:.2f} (合计 {xg_a + xg_b:.2f})')
        report.append(f'- 修正因子: {applied_str}')
        report.append('')
        report.append(f'**最终概率 (v4.8)**')
        report.append(f'| {team_a}胜 | 平局 | {team_b}胜 |')
        report.append(f'|--------|------|--------|')
        report.append(f'| {f["win_a"]}% | {f["draw"]}% | {f["win_b"]}% |')
        report.append('')

        report.append('**总进球 Top5**')
        top_totals = sorted(totals.items(), key=lambda x: -x[1])[:5]
        report.append('| ' + ' | '.join([f'{k}球 {v}%' for k, v in top_totals]) + ' |')
        report.append('')
        report.append(f'**由比分赔率反推大/小球 2.5**: 大球 {over_under["over_pct"]}% / 小球 {over_under["under_pct"]}% (原始赔率合计水位 +{over_under["vig_pct"]}%，含"其它"未覆盖项，仅作参考)')
        report.append('')

        report.append('**半全场 Top6**')
        top_htft = list(htft.items())[:6]
        report.append('| ' + ' | '.join([f'{label_htft(k, team_a, team_b)} {v}%' for k, v in top_htft]) + ' |')
        report.append('')

        report.append('**比分 Top8 (按模型概率)**')
        top_scores = score_probs[:8]
        report.append('| 比分 | 模型概率 | 赔率 | EV |')
        report.append('|------|---------|------|-----|')
        for s, p, o, ev in top_scores:
            report.append(f'| {s} | {p}% | {o} | {ev:.2f} |')
        report.append('')

        if enh.get('handicap_warnings') or enh.get('strategy_hints'):
            report.append('**v4.8 策略提示**')
            for h in enh['strategy_hints'][:3]:
                report.append(f'- {h}')
            for w in enh['handicap_warnings'][:1]:
                report.append(f'- ⚠️ {w}')
            report.append('')

        json_out['matches'].append({
            'match_no': num,
            'team_a': team_a,
            'team_b': team_b,
            'datetime': dt,
            'stadium': stadium,
            'weather': f'{weather} {temp}',
            'elo_a': elo_a,
            'elo_b': elo_b,
            'xg_a': xg_a,
            'xg_b': xg_b,
            'final_probabilities': f,
            'total_goals': totals,
            'htft': htft,
            'score_probs': score_probs,
            'over_under_25': over_under,
            'enhancements': pred['enhancements'],
        })

    # =========================
    # 投注方案
    # =========================
    report.append('---')
    report.append('# 🎯 串关投注方案')
    report.append('')
    report.append('> **成本控制原则**: 单轮总投入建议 ≤10u；比分因为命中低，单注宜小；总进球/半全场相对稳健，可适度加注。')
    report.append('> **数据缺口**: 截图仅提供**比分赔率**，半全场与总进球的实际赔率未提供，以下两项给出模型概率和推荐选项，实际投注时请用当场盘口赔率换算期望。')
    report.append('')

    score_a = score_probabilities(predictions[('巴西', '挪威')], ODDS[('巴西', '挪威')])
    score_b = score_probabilities(predictions[('墨西哥', '英格兰')], ODDS[('墨西哥', '英格兰')])

    # 比分方案
    report.append('## 一、比分二串一')
    report.append('')
    report.append('### 方案 A：稳健型（命中概率最高）')
    lines, hit, n = format_score_parlay(score_a[:1], score_b[:1])
    report.extend(lines)
    report.append(f'- **注数**: {n} 注')
    report.append(f'- **建议**: 1u × {n} 注 = {n}u')
    report.append(f'- **理论命中概率**: {hit:.2%}（按模型各比分概率乘积）')
    report.append('')

    report.append('### 方案 B：均衡型（兼顾命中与赔率）')
    lines, hit, n = format_score_parlay(score_a[:2], score_b[:2])
    report.extend(lines)
    report.append(f'- **注数**: {n} 注')
    report.append(f'- **建议**: 0.5u × {n} 注 = {n * 0.5:.1f}u')
    report.append(f'- **理论命中概率**: {hit:.2%}')
    report.append('')

    report.append('### 方案 C：进取型（高赔 + 模型价值，过滤极低概率）')
    # 每场取概率第1 + 一个模型概率≥4%且EV最高的选项
    high_ev_a = sorted([x for x in score_a if x[1] >= 4.0], key=lambda x: -x[3])[:1]
    high_ev_b = sorted([x for x in score_b if x[1] >= 4.0], key=lambda x: -x[3])[:1]
    if not high_ev_a:
        high_ev_a = [sorted(score_a, key=lambda x: -x[3])[0]]
    if not high_ev_b:
        high_ev_b = [sorted(score_b, key=lambda x: -x[3])[0]]
    set_a = list({x[0]: x for x in [score_a[0], high_ev_a[0]]}.values())
    set_b = list({x[0]: x for x in [score_b[0], high_ev_b[0]]}.values())
    lines, hit, n = format_score_parlay(set_a, set_b)
    report.extend(lines)
    report.append(f'- **注数**: {n} 注')
    report.append(f'- **建议**: 0.5u × {n} 注 = {n * 0.5:.1f}u')
    report.append(f'- **理论命中概率**: {hit:.2%}')
    report.append(f'- **说明**: 巴西高EV选项为 {high_ev_a[0][0]}(模型{high_ev_a[0][1]}%, EV {high_ev_a[0][3]:.2f})；墨西哥高EV选项为 {high_ev_b[0][0]}(模型{high_ev_b[0][1]}%, EV {high_ev_b[0][3]:.2f})')
    report.append('')

    # 半全场方案
    report.append('## 二、半全场二串一')
    report.append('')
    ht_a = htft_distribution(predictions[('巴西', '挪威')])
    ht_b = htft_distribution(predictions[('墨西哥', '英格兰')])
    top_ht_a = list(ht_a.items())[:2]
    top_ht_b = list(ht_b.items())[:2]
    report.append('### 推荐组合（按模型概率 Top2 × Top2）')
    for ca, pa in top_ht_a:
        for cb, pb in top_ht_b:
            la = label_htft(ca, '巴西', '挪威')
            lb = label_htft(cb, '墨西哥', '英格兰')
            report.append(f'- 巴西 {la} × 墨西哥 {lb} | 模型命中概率 {pa * pb / 10000:.2%}')
    report.append('- **注数**: 4 注')
    report.append('- **建议**: 0.5u × 4 注 = 2.0u')
    report.append('- **说明**: 半全场 Top1 命中率 15 场累计仅 53%，建议小额覆盖；实际赔率未提供，无法给出精确期望。')
    report.append('')

    # 总进球方案
    report.append('## 三、总进球数二串一')
    report.append('')
    tg_a = total_goals_distribution(predictions[('巴西', '挪威')])
    tg_b = total_goals_distribution(predictions[('墨西哥', '英格兰')])
    top_tg_a = sorted(tg_a.items(), key=lambda x: -x[1])[:2]
    top_tg_b = sorted(tg_b.items(), key=lambda x: -x[1])[:2]
    report.append('### 推荐组合（按模型概率 Top2 总进球 × Top2 总进球）')
    for ta, pa in top_tg_a:
        for tb, pb in top_tg_b:
            report.append(f'- 巴西 {ta}球 × 墨西哥 {tb}球 | 模型命中概率 {pa * pb / 10000:.2%}')
    report.append('- **注数**: 4 注')
    report.append('- **建议**: 0.5u × 4 注 = 2.0u')
    report.append('- **替代思路**: 若只买大/小球 2.5，两场模型均看大球（巴西大球约 60.8%，墨西哥大球约 60.9%），可二串一「两场大2.5」，理论命中概率约 37.0%，但需现场盘口赔率支撑。')
    report.append('')

    # 汇总
    report.append('---')
    report.append('# 💰 三套方案同时押注分配')
    report.append('')
    report.append('| 玩法 | 方案 | 单注 | 注数 | 成本 | 说明 |')
    report.append('|------|------|------|------|------|------|')
    report.append('| 比分 | A 稳健 | 1.0u | 1 | 1.0u | 命中概率最高 |')
    report.append('| 比分 | B 均衡 | 0.5u | 4 | 2.0u | 兼顾命中与赔率 |')
    report.append('| 比分 | C 进取 | 0.5u | 4 | 2.0u | 含高EV长串 |')
    report.append('| 半全场 | Top2×Top2 | 0.5u | 4 | 2.0u | 模型辅助，赔率未提供 |')
    report.append('| 总进球 | Top2×Top2 | 0.5u | 4 | 2.0u | 模型辅助，赔率未提供 |')
    report.append('| 预留 | — | — | — | 1.0u | 临场调整/补单 |')
    report.append('| **合计** | — | — | **17** | **10.0u** | 成本上限内 |')
    report.append('')

    # 关键判断
    report.append('---')
    report.append('# ⚠️ 关键判断')
    report.append('')
    report.append('1. **巴西 vs 挪威**: 模型给出巴西 49.9% / 平 32.8% / 挪威 17.3%，xG 1.87 vs 1.28。')
    report.append('   - 双方均有超级巨星（巴西 Vinicius、挪威 Haaland），KO 赛 xG 同获 +12% 加成，因此挪威仍具备 17% 的爆冷窗口。')
    report.append('   - 比分 Top2 为 1-1、2-1，均落在巴西不败范围内，但挪威 1-2、0-1 等高赔选项 EV 偏高，说明市场对挪威客胜定价偏保守。')
    report.append('   - 26worldcup 显示巴西 R32 2-1 日本，淘汰赛进攻不算犀利；挪威小组赛末轮 1-4 法国、R32 2-1 科特迪瓦，攻防开放，本场比赛大球概率高。')
    report.append('')
    report.append('2. **墨西哥 vs 英格兰**: 模型给出墨西哥 22.0% / 平 32.8% / 英格兰 45.2%，xG 1.58 vs 1.84。')
    report.append('   - 墨西哥东道主效应（xG +15%）把比赛拉回均势，但英格兰超级巨星（Kane、Bellingham）+12% 仍让其略占上风。')
    report.append('   - 由比分赔率反推，市场认为本场小球概率更高（小球 2.5 约 54.6%），而模型看大球（约 60.9%）。若临场大2.5 赔率 ≥1.85，存在模型价值。')
    report.append('   - 英格兰小组赛曾 0-0 加纳，淘汰赛进球效率不一定高；墨西哥主场防守韧性强，1-1、1-2 是最可能比分。')
    report.append('')
    report.append('3. **让球盘继续规避**: 15 场 KO 让球[-1]胜累计仅 1/9(11%)，本报告不涉及让球串关。')
    report.append('')
    report.append('4. **比分「其它」项**: 截图中的 胜其它/平其它/负其它 未给出具体比分范围，未纳入模型概率计算；若选择覆盖大比分，建议仅用小注。')
    report.append('')
    report.append('---')
    report.append('⚠️ 风险提示：以上分析基于统计模型与历史数据，不构成投注建议。足球比赛存在不可预测因素，请理性决策。')
    report.append('数据来源：26worldcup.github.io + worldcup26.ir（2026-07-05 抓取）；比分赔率来自用户截图。半全场/总进球赔率未提供，实际投注请核对盘口。')

    with open(OUTPUT_MD, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report))

    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(json_out, f, ensure_ascii=False, indent=2)

    print(f'Report saved to: {OUTPUT_MD}')
    print(f'JSON saved to: {OUTPUT_JSON}')


if __name__ == '__main__':
    main()
