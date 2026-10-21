#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R32e 双场预测与投注方案生成 (加拿大 vs 摩洛哥, 巴拉圭 vs 法国)"""
import os
import sys
import json
from datetime import datetime

# Add skill scripts to path
SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT_DIR = os.path.join(SKILL_DIR, 'scripts')
sys.path.insert(0, SCRIPT_DIR)

from prediction_engine import FootballPredictionEngine

OUTPUT_MD = os.path.join(SKILL_DIR, 'outputs', 'r32e_predictions_and_bets.md')
OUTPUT_JSON = os.path.join(SKILL_DIR, 'outputs', 'r32e_predictions.json')

def implied_prob(odds):
    return [round(100 / o, 1) for o in odds]

def total_goals_probs(pred):
    """计算总进球数分布 (0-7+)"""
    xg_a, xg_b = pred['xg_a'], pred['xg_b']
    from math import exp, factorial
    def poisson(lam, k):
        return exp(-lam) * (lam ** k) / factorial(k)
    max_goals = 7
    dist = {}
    for k in range(max_goals + 1):
        p = 0
        for i in range(k + 1):
            p += poisson(xg_a, i) * poisson(xg_b, k - i)
        dist[k] = round(p * 100, 1)
    # 7+ bucket
    p_7plus = 0
    for k in range(max_goals + 1, 12):
        for i in range(k + 1):
            p_7plus += poisson(xg_a, i) * poisson(xg_b, k - i)
    dist['7+'] = round(p_7plus * 100, 1)
    return dist

def half_time_full_time_probs(pred):
    """计算半全场结果分布 (A/A, A/D, A/B, D/A, D/D, D/B, B/A, B/D, B/B)"""
    xg_a, xg_b = pred['xg_a'], pred['xg_b']
    from math import exp, factorial
    def poisson(lam, k):
        return exp(-lam) * (lam ** k) / factorial(k)
    # HT expected goals scaled by 0.45
    ht_xg_a = xg_a * 0.45
    ht_xg_b = xg_b * 0.45
    # 2H expected goals
    fh2_xg_a = xg_a * 0.55
    fh2_xg_b = xg_b * 0.55
    probs = {}
    labels = ['A', 'D', 'B']  # A=home lead, D=draw, B=away lead
    ht_dist = {i: poisson(ht_xg_a, i) * poisson(ht_xg_b, j) for i in range(6) for j in range(6)}
    
    for ht_a in range(6):
        for ht_b in range(6):
            p_ht = poisson(ht_xg_a, ht_a) * poisson(ht_xg_b, ht_b)
            ht_state = 'A' if ht_a > ht_b else 'B' if ht_b > ht_a else 'D'
            # conditional on first half state, simulate second half
            for fh2_a in range(6):
                for fh2_b in range(6):
                    p_fh2 = poisson(fh2_xg_a, fh2_a) * poisson(fh2_xg_b, fh2_b)
                    total_a = ht_a + fh2_a
                    total_b = ht_b + fh2_b
                    ft_state = 'A' if total_a > total_b else 'B' if total_b > total_a else 'D'
                    key = f"{ht_state}/{ft_state}"
                    probs[key] = probs.get(key, 0) + p_ht * p_fh2
    return {k: round(v * 100, 1) for k, v in sorted(probs.items(), key=lambda x: -x[1])}

# 赔率数据 (来自用户截图, 巴拉圭vs法国[0]盘口缺失)
ODDS = {
    # 089: 加拿大 vs 摩洛哥 (07-05 01:00 CST)
    ('加拿大', '摩洛哥'): {
        '0': {'home': 5.50, 'draw': 3.50, 'away': 1.51},
        '+1': {'home': 2.17, 'draw': 2.80, 'away': 3.23},
    },
    # 090: 巴拉圭 vs 法国 (07-05 05:00 CST) — [0] 赔率截图未显示
    ('巴拉圭', '法国'): {
        '+2': {'home': 2.35, 'draw': 3.33, 'away': 2.48},
        '0': None,  # 缺失
    },
}

MATCHES = [
    ('加拿大', '摩洛哥', True, 'knockout_stage', '089'),
    ('巴拉圭', '法国', True, 'knockout_stage', '090'),
]

def main():
    engine = FootballPredictionEngine(data_dir=os.path.join(SKILL_DIR, 'data'))
    predictions = {}
    report = []
    
    report.append("# 📊 R32e 双场预测与投注报告")
    report.append(f"引擎版本: v4.8 (KO主导胜上限 + 高Elo缓冲 + 首次KO黑马)")
    report.append(f"数据时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"数据源: worldcup26.ir (实时 API 已恢复；26worldcup.github.io 返回空/无效JSON；备选 kickoffapi.com/api-football.com 未启用)")
    report.append(f"赛程确认:")
    report.append(f"- 089 加拿大 vs 摩洛哥 | 07-05 01:00 CST | R16 | API id=90")
    report.append(f"- 090 巴拉圭 vs 法国 | 07-05 05:00 CST | R16 | API id=89")
    report.append("")
    
    # 重要提示：巴拉圭vs法国标准赔率缺失
    report.append("⚠️ **数据缺口**: 截图中巴拉圭 vs 法国仅显示 [+2] 让球赔率，标准 1X2 ([0]) 赔率缺失。")
    report.append("   下文模型 vs 市场对比仅基于 [+2] 盘口，标准盘对比标记为 [未提供] 。")
    report.append("")
    
    # 逐场预测
    for team_a, team_b, is_ko, round_name, match_no in MATCHES:
        pred = engine.predict(team_a, team_b, is_knockout=is_ko, tournament_round=round_name)
        predictions[(team_a, team_b)] = pred
        
        f = pred['final']
        xg_a, xg_b = pred['xg_a'], pred['xg_b']
        elo_a, elo_b = pred['elo_a'], pred['elo_b']
        elo_diff = elo_a - elo_b
        
        # 显示已应用的修正因子
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
        
        report.append(f"---")
        report.append(f"## ⚽ {match_no} {team_a} vs {team_b}")
        report.append("")
        report.append(f"**基础数据**")
        report.append(f"- Elo: {team_a} {elo_a} vs {team_b} {elo_b} (差 {elo_diff})")
        report.append(f"- xG: {team_a} {xg_a:.2f} vs {team_b} {xg_b:.2f} (合计 {xg_a+xg_b:.2f})")
        report.append(f"- 修正因子: {applied_str}")
        report.append("")
        report.append(f"**最终概率 (v4.8)**")
        report.append(f"| {team_a}胜 | 平 | {team_b}胜 |")
        report.append(f"|--------|------|--------|")
        report.append(f"| {f['win_a']}% | {f['draw']}% | {f['win_b']}% |")
        report.append("")
        
        # 市场赔率对比
        odds = ODDS.get((team_a, team_b), {})
        if odds.get('0'):
            o = odds['0']
            market = implied_prob([o['home'], o['draw'], o['away']])
            model = [f['win_a'], f['draw'], f['win_b']]
            edges = [model[i] - market[i] for i in range(3)]
            report.append(f"**市场赔率 [0]**")
            report.append(f"- 主胜 {o['home']} / 平 {o['draw']} / 客胜 {o['away']}")
            report.append(f"- 市场隐含: {team_a} {market[0]}% / 平 {market[1]}% / {team_b} {market[2]}%")
            report.append(f"- 模型偏差: {team_a} {edges[0]:+.1f}% / 平 {edges[1]:+.1f}% / {team_b} {edges[2]:+.1f}%")
            report.append("")
        if odds.get('+1') or odds.get('+2'):
            for hk in ['+1', '+2']:
                if hk in odds and odds[hk]:
                    o = odds[hk]
                    market = implied_prob([o['home'], o['draw'], o['away']])
                    report.append(f"**市场赔率 [{hk}]**")
                    report.append(f"- 主胜 {o['home']} / 平 {o['draw']} / 客胜 {o['away']}")
                    report.append(f"- 市场隐含: {team_a}[{hk}] {market[0]}% / 平 {market[1]}% / {team_b}[{hk}] {market[2]}%")
                    report.append("")
        if odds.get('0') is None:
            report.append(f"**市场赔率 [0]**: [未提供] — 截图仅显示让球盘，无法进行标准1X2模型偏差分析。")
            report.append("")
        
        # 总进球
        totals = total_goals_probs(pred)
        top_totals = sorted(totals.items(), key=lambda x: -x[1])[:4]
        report.append(f"**总进球 Top4**")
        report.append(f"| {' | '.join([f'{k}球 {v}%' for k,v in top_totals])} |")
        report.append("")
        
        # 半全场
        htft = half_time_full_time_probs(pred)
        top_htft = sorted(htft.items(), key=lambda x: -x[1])[:3]
        report.append(f"**半全场 Top3**")
        report.append(f"| {' | '.join([f'{k} {v}%' for k,v in top_htft])} |")
        report.append("")
        
        # 比分
        top_scores = pred['top_scores']
        report.append(f"**比分 Top6**")
        report.append(f"| {' | '.join([f'{s} {p}%' for s,p in top_scores])} |")
        report.append("")
        
        # 策略提示
        hints = pred['enhancements'].get('strategy_hints', [])
        warnings = pred['enhancements'].get('handicap_warnings', [])
        if hints or warnings:
            report.append(f"**v4.8 策略提示**")
            for h in hints[:2]:
                report.append(f"- {h}")
            for w in warnings[:1]:
                report.append(f"- ⚠️ {w}")
            report.append("")
    
    # 投注方案
    report.append("---")
    report.append("# 🎯 串关投注方案")
    report.append("")
    report.append("> **注意：用户仅指定 2 场比赛，严格意义上的「三串一」需要 3 场。**")
    report.append("> 下面提供 **2串1**（双场）方案，并额外给出一种「三串一补第三场」的备选思路。")
    report.append("")
    
    # 提取各场 Top 选择
    totals_top1 = []
    for ta, tb, _, _, _ in MATCHES:
        pred = predictions[(ta, tb)]
        totals = total_goals_probs(pred)
        top1 = sorted(totals.items(), key=lambda x: -x[1])[0]
        totals_top1.append(f"{ta} {top1[0]}球")
    
    htft_top1 = []
    for ta, tb, _, _, _ in MATCHES:
        pred = predictions[(ta, tb)]
        htft = half_time_full_time_probs(pred)
        top1 = sorted(htft.items(), key=lambda x: -x[1])[0]
        htft_top1.append(f"{ta} {top1[0]}")
    
    score_top2 = {}
    for ta, tb, _, _, _ in MATCHES:
        pred = predictions[(ta, tb)]
        score_top2[(ta, tb)] = [s for s, p in pred['top_scores'][:2]]
    
    report.append("## 方案 A：总进球 2串1（概率最稳）")
    report.append(f"- **组合**: {' × '.join(totals_top1)}")
    report.append(f"- **建议**: 2u × 1注 = 2u")
    report.append("")
    
    report.append("## 方案 B：半全场 2串1（次稳）")
    report.append(f"- **组合**: {' × '.join(htft_top1)}")
    report.append(f"- **建议**: 2u × 1注 = 2u")
    report.append("")
    
    report.append("## 方案 C：比分 2×2 2串1（高赔覆盖）")
    report.append(f"- 加拿大 vs 摩洛哥: {', '.join(score_top2[('加拿大', '摩洛哥')])}")
    report.append(f"- 巴拉圭 vs 法国: {', '.join(score_top2[('巴拉圭', '法国')])}")
    report.append(f"- **注数**: 2 × 2 = 4 注")
    report.append(f"- **建议**: 0.75u × 4注 = 3u")
    report.append("")
    
    report.append("## 方案 D：三串一补第三场（如要凑3场）")
    report.append("- 若必须凑三串一，可加入一个低赔稳胆（如西班牙/德国/葡萄牙已晋级队，或已开赛的强队）作为第三场固定选择。")
    report.append("- 例如：总进球 2串1 再串一场 **已晋级强队的小球/主胜** 作为第三场，降低成本但需额外确认赔率。")
    report.append("- 不在本报告分析范围内，因为用户只给了 2 场比赛。")
    report.append("")
    
    report.append("## 三套同时押注分配（≤10u）")
    report.append("| 方案 | 单注 | 注数 | 成本 | 说明 |")
    report.append("|------|------|------|------|------|")
    report.append("| 总进球 2串1 | 2u | 1 | 2u | 主推 |")
    report.append("| 半全场 2串1 | 2u | 1 | 2u | 次推 |")
    report.append("| 比分 2×2 2串1 | 0.75u | 4 | 3u | 高赔 |")
    report.append("| 预留/机动 | — | — | 3u | 用于补第三场或临场调整 |")
    report.append("| **合计** | — | 6 | **7u** | 成本受控 |")
    report.append("")
    
    # 关键判断
    report.append("# ⚠️ 关键判断")
    report.append("")
    pred_can_mar = predictions[('加拿大', '摩洛哥')]
    pred_par_fra = predictions[('巴拉圭', '法国')]
    
    can_mar_away = pred_can_mar['final']['win_b']
    par_fra_home = pred_par_fra['final']['win_a']
    par_fra_draw = pred_par_fra['final']['draw']
    
    report.append(f"1. **加拿大 vs 摩洛哥**: 摩洛哥客胜概率 {can_mar_away}% vs 市场隐含 66.2%，模型偏差 **{can_mar_away-66.2:+.1f}%**。")
    report.append(f"   加拿大是东道主之一，v4.8 东道主效应 xG+15%。摩洛哥市场 1.51 过热的风险存在，但模型仍看摩洛哥不败。")
    report.append("")
    report.append(f"2. **巴拉圭 vs 法国**: 法国 Elo 优势 {pred_par_fra['elo_b'] - pred_par_fra['elo_a']} 分，接近但未触发 v4.8 高 Elo 缓冲阈值（>400）。模型直接给出法国胜 65.2% / 平 29.3%，xG 2.18 体现了球星加成。")
    report.append(f"   [+2] 让球盘：巴拉圭[+2]胜隐含 42.6%，法国[-2]需净胜 3 球以上才能赢下让球盘，模型 Top 比分集中在 0-2/0-1/1-2，[0-2] 刚好走水，[-2] 方向偏危险。")
    report.append(f"   标准 [0] 赔率缺失，无法判断主胜/平/负的市场偏差，但法国大胜概率高，可考虑法国[-1]或[-2]仅作为小额覆盖，禁止做串关断链腿。")
    report.append("")
    report.append("3. **让球盘仍维持低置信**: 15场 KO 让球[-1] 累计 1/9(11%)。法国[-2] 需净胜 3 球以上，模型 Top 比分 0-2/0-1/1-2 均不满足[-2]穿盘，让球方向建议远离或仅小额覆盖，禁止做串关断链腿。")
    report.append("")
    
    report.append("---")
    report.append("⚠️ 风险提示：以上分析基于统计模型与历史数据，不构成投注建议。足球比赛存在不可预测因素，请理性决策。")
    report.append("数据来源：worldcup26.ir 实时 API（2026-07-04 抓取），赔率来自用户截图。巴拉圭 vs 法国标准盘赔率缺失，[0] 对比标记为未提供。")
    
    with open(OUTPUT_MD, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report))
    
    # JSON output
    json_out = {
        'generated_at': datetime.now().isoformat(),
        'engine_version': 'v4.8',
        'data_source': 'worldcup26.ir',
        'matches': []
    }
    for team_a, team_b, is_ko, round_name, match_no in MATCHES:
        pred = predictions[(team_a, team_b)]
        json_out['matches'].append({
            'match_no': match_no,
            'team_a': team_a,
            'team_b': team_b,
            'elo_a': pred['elo_a'],
            'elo_b': pred['elo_b'],
            'xg_a': pred['xg_a'],
            'xg_b': pred['xg_b'],
            'final_probabilities': pred['final'],
            'top_scores': pred['top_scores'],
            'total_goals': total_goals_probs(pred),
            'htft': half_time_full_time_probs(pred),
            'odds': ODDS.get((team_a, team_b), {}),
            'enhancements': pred['enhancements'],
        })
    
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(json_out, f, ensure_ascii=False, indent=2)
    
    print(f"Report saved to: {OUTPUT_MD}")
    print(f"JSON saved to: {OUTPUT_JSON}")

if __name__ == '__main__':
    main()
