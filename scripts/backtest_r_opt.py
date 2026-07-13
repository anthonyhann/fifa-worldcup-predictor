"""
对比回放脚本 — 比分/总进球特征增强(v4.15)前后对比
=================================================
回放集: 5 场 ground-truth(真实比分已知) + 100+ market 校准检验
特性: H2H交锋史 / 伤停-阵型xG接线 / Poisson低比分校准

⚠️ N=5 为方向性验证, 不具统计显著性。本报告如实呈现新旧差异。
"""
import os
import sys
import json
from typing import Dict, List, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from prediction_engine import FootballPredictionEngine

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(SKILL_DIR, 'data')

# 5 场 ground-truth（来自 review_log match-level actual_score）
GROUND_TRUTH = [
    # (team_a, team_b, actual_ga, actual_gb, round_label)
    ('巴西', '德国', 3, 1, 'QF/R32'),
    ('巴西', '日本', 2, 1, 'R32'),
    ('德国', '巴拉圭', 1, 1, 'R32'),
    ('荷兰', '摩洛哥', 1, 1, 'R32'),
    ('西班牙', '比利时', 2, 1, 'QF'),
]


def top_total_from_score_probs(score_probs: Dict[str, float]) -> Tuple[int, float]:
    tot = {}
    for sc, p in score_probs.items():
        ga, gb = map(int, sc.split('-'))
        tot[ga + gb] = tot.get(ga + gb, 0) + p
    best = max(tot.items(), key=lambda x: x[1])
    return best[0], best[1]


def run_predictions(engine: FootballPredictionEngine,
                    features_on: bool) -> List[Dict]:
    engine.toggle_features(
        h2h=features_on,
        injury_formation=features_on,
        scoreline_cal=features_on,
    )
    rows = []
    for ta, tb, ga, gb, rd in GROUND_TRUTH:
        pred = engine.predict(ta, tb, is_knockout=True,
                              tournament_round='knockout_stage')
        top_score = pred['top_scores'][0][0] if pred['top_scores'] else '?'
        top_total, top_total_p = top_total_from_score_probs(pred['poisson']['score_probs'])
        # coverage: actual in top-6?
        actual_sc = f"{ga}-{gb}"
        in_top6 = any(s == actual_sc for s, _ in pred['top_scores'])
        rows.append({
            'match': f"{ta} vs {tb}", 'round': rd,
            'actual': actual_sc, 'actual_total': ga + gb,
            'xg_a': pred['xg_a'], 'xg_b': pred['xg_b'],
            'top_score': top_score, 'score_hit': top_score == actual_sc,
            'top_total': top_total, 'total_hit': top_total == (ga + gb),
            'in_top6': in_top6,
            'final': pred['final'],
        })
    return rows


def summarize(rows: List[Dict], label: str):
    n = len(rows)
    sc_hit = sum(1 for r in rows if r['score_hit'])
    tot_hit = sum(1 for r in rows if r['total_hit'])
    cov = sum(1 for r in rows if r['in_top6'])
    print(f"\n=== {label} (n={n}) ===")
    for r in rows:
        print(f"  {r['match']:<14} 实际{r['actual']:>4} | "
              f"比分pick {r['top_score']:>4} {'✅' if r['score_hit'] else '❌'} | "
              f"总球pick {r['top_total']:>2} {'✅' if r['total_hit'] else '❌'} | "
              f"top6覆盖{'✅' if r['in_top6'] else '❌'} | "
              f"xG {r['xg_a']}/{r['xg_b']}")
    print(f"  单点比分命中: {sc_hit}/{n} = {sc_hit/n*100:.1f}%")
    print(f"  单点总球命中: {tot_hit}/{n} = {tot_hit/n*100:.1f}%")
    print(f"  top6比分覆盖: {cov}/{n} = {cov/n*100:.1f}%")
    return {'score_hit': sc_hit, 'total_hit': tot_hit, 'coverage': cov, 'n': n}


def demo_h2h(engine: FootballPredictionEngine):
    print("\n=== 特性演示 1: 交锋史(H2H) ===")
    ta, tb = '西班牙', '比利时'
    engine.toggle_features(h2h=False, injury_formation=False, scoreline_cal=False)
    off = engine.predict(ta, tb, is_knockout=True, tournament_round='knockout_stage')
    engine.toggle_features(h2h=True)
    on = engine.predict(ta, tb, is_knockout=True, tournament_round='knockout_stage')
    print(f"  {ta} vs {tb}  xG: 关H2H {off['xg_a']}/{off['xg_b']} → 开H2H {on['xg_a']}/{on['xg_b']}")
    print(f"  关H2H top比分: {off['top_scores'][0]} | 开H2H top比分: {on['top_scores'][0]}")


def demo_injury(engine: FootballPredictionEngine):
    print("\n=== 特性演示 2: 伤停 → xG 主链路 ===")
    ta, tb = '西班牙', '比利时'
    engine.toggle_features(h2h=False, injury_formation=False, scoreline_cal=False)
    base = engine.predict(ta, tb, is_knockout=True, tournament_round='knockout_stage')
    # 主队(西班牙)缺3名主力
    inj = {'available': True, 'home_out_count': 3, 'home_doubtful_count': 0,
           'away_out_count': 0, 'away_doubtful_count': 0}
    engine.set_injuries(inj)
    engine.toggle_features(injury_formation=True)
    hurt = engine.predict(ta, tb, is_knockout=True, tournament_round='knockout_stage')
    engine.set_injuries(None)
    print(f"  西班牙缺3主力: xG {base['xg_a']}/{base['xg_b']} → {hurt['xg_a']}/{hurt['xg_b']} (主队xG下调)")
    print(f"  top比分: 无伤停 {base['top_scores'][0]} → 有伤停 {hurt['top_scores'][0]}")


def demo_scoreline(engine: FootballPredictionEngine):
    print("\n=== 特性演示 3: Poisson 低比分校准 ===")
    ta, tb = '巴西', '德国'
    engine.toggle_features(h2h=False, injury_formation=False, scoreline_cal=False)
    off = engine.predict(ta, tb, is_knockout=True, tournament_round='knockout_stage')
    engine.toggle_features(scoreline_cal=True)
    on = engine.predict(ta, tb, is_knockout=True, tournament_round='knockout_stage')
    for cell in ['0-0', '1-0', '0-1', '1-1', '2-1', '3-1']:
        po = off['poisson']['score_probs'].get(cell, 0)
        pn = on['poisson']['score_probs'].get(cell, 0)
        arrow = '↑' if pn > po else ('↓' if pn < po else '=')
        print(f"  {cell:>4}: 关{po:>5.1f}% → 开{pn:>5.1f}% {arrow}")


def main():
    engine = FootballPredictionEngine(data_dir=DATA_DIR)

    print("########## 比分/总进球特征增强 对比回放 (v4.15) ##########")
    old = run_predictions(engine, features_on=False)
    new = run_predictions(engine, features_on=True)

    so = summarize(old, "OLD — 关全部新特性 (v4.14 基线)")
    sn = summarize(new, "NEW — 开 H2H+伤停+xG校准 (v4.15)")

    print("\n=== 前后差异 ===")
    print(f"  单点比分命中: {so['score_hit']} → {sn['score_hit']} ({sn['score_hit']-so['score_hit']:+d})")
    print(f"  单点总球命中: {so['total_hit']} → {sn['total_hit']} ({sn['total_hit']-so['total_hit']:+d})")
    print(f"  top6比分覆盖: {so['coverage']} → {sn['coverage']} ({sn['coverage']-so['coverage']:+d})")

    demo_h2h(engine)
    demo_injury(engine)
    demo_scoreline(engine)

    print("\n⚠️  N=5 方向性验证, 不具统计显著性。H2H 仅对 5 对回放对有种子数据;"\
          "伤停/阵型需实时数据方在真实预测中生效(已合成注入演示)。")


if __name__ == '__main__':
    main()
