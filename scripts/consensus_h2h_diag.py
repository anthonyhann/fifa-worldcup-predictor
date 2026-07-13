"""
选项A 诊断 — 交锋史(H2H)注入 predict_with_consensus 单点选择 (v4.16)
====================================================================
验证四件事:
  1. H2H 重建泊松矩阵的 top_scores 是否并入共识候选池(扩大可覆盖比分线)
  2. H2H 隐含比分线(round(avg_a):round(avg_b)) vs 真实赛果
  3. 无市场时: 合并池#1 比分 vs 基座#1 比分(机制是否移动单点pick)
  4. [SYNTHETIC 合成市场] 给每对从其自身泊松分布构造参与人数, 演示 H2H 偏好覆盖
     是否触发并把 pick 移到 H2H 隐含比分线

⚠️ N=5 回放无历史 market participantCount 存档, 且含前瞻污染; 合成市场仅用于
   演示选择机制, 不声称命中率提升。选项A完成的是『通路接线 + H2H偏好信号』。
"""
import os
import sys
from typing import Dict, List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from prediction_engine import FootballPredictionEngine

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(SKILL_DIR, 'data')

GROUND_TRUTH = [
    ('巴西', '德国', 3, 1, 'QF/R32'),
    ('巴西', '日本', 2, 1, 'R32'),
    ('德国', '巴拉圭', 1, 1, 'R32'),
    ('荷兰', '摩洛哥', 1, 1, 'R32'),
    ('西班牙', '比利时', 2, 1, 'QF'),
]


def fmt_pool(pool):
    return ", ".join(f"{s}({p:.1f}%)" for s, p in pool[:6])


def main():
    engine = FootballPredictionEngine(data_dir=DATA_DIR)
    engine.toggle_features(h2h=True, injury_formation=True, scoreline_cal=True)

    print("########## 选项A: H2H 注入 consensus 单点选择 (v4.16) ##########\n")

    print("— 验证1+2+3: H2H 候选池 / 隐含比分线 vs 真实 / 无市场合并池#1 —")
    agg = {'pairs': 0, 'pool_expanded': 0, 'h2h_eq_actual': 0, 'no_mkt_move': 0}
    for ta, tb, ga, gb, rd in GROUND_TRUTH:
        off = engine.predict(ta, tb, is_knockout=True, tournament_round='knockout_stage')
        cons_on = engine.predict_with_consensus(
            ta, tb, is_knockout=True, tournament_round='knockout_stage', use_h2h=True)

        base_pool = [(s.replace('-', ':'), p) for s, p in off['top_scores']]
        merged_pool = cons_on.get('consensus_candidate_pool') or base_pool
        h2h_sig = cons_on.get('h2h_signal')
        h2h_line = h2h_sig['scoreline'] if h2h_sig else None
        actual = f"{ga}:{gb}"

        off_set = {s for s, _ in base_pool[:6]}
        merged_set = {s for s, _ in merged_pool[:6]}
        expanded = len(merged_set - off_set) > 0

        pick_on = cons_on.get('score_pick')     # 无市场 → 合并池#1
        pick_base = base_pool[0][0]

        agg['pairs'] += 1
        if expanded:
            agg['pool_expanded'] += 1
        if h2h_line == actual:
            agg['h2h_eq_actual'] += 1
        if pick_on != pick_base:
            agg['no_mkt_move'] += 1

        print(f"\n  {ta} vs {tb} [{rd}]  实际 {actual}")
        print(f"    基座xG {off['xg_a']}/{off['xg_b']}  | H2H avg {h2h_sig['avg_a']}/{h2h_sig['avg_b']} (n={h2h_sig['meetings']})"
              if h2h_sig else f"    基座xG {off['xg_a']}/{off['xg_b']}")
        print(f"    H2H隐含比分线: {h2h_line}  →  真实 {actual}  {'✅吻合' if h2h_line==actual else '⚠️偏差'}")
        print(f"    基座top6 : {fmt_pool(base_pool)}")
        print(f"    合并池#1 : {pick_on}   (基座#1: {pick_base})  {'→已移动' if pick_on!=pick_base else '→未变'}")
        print(f"    候选池新增比分线: {sorted(merged_set - off_set) or '无'}  | H2H融合xG: {cons_on.get('h2h_xg')}")

    print(f"\n  汇总: {agg['pairs']} 对有H2H种子; 候选池扩展 {agg['pool_expanded']}/{agg['pairs']}; "
          f"H2H隐含==真实 {agg['h2h_eq_actual']}/{agg['pairs']}; "
          f"无市场合并池#1移动 {agg['no_mkt_move']}/{agg['pairs']}")

    print("\n— 验证4 [SYNTHETIC 合成市场, 非真实回放]: H2H 偏好覆盖是否把 pick 移到 H2H 隐含线 —")
    print("  (合成市场 = 各对自身泊松分布×10取整为参与人数, 仅演示机制)")
    n_override = 0
    for ta, tb, ga, gb, rd in GROUND_TRUTH:
        off = engine.predict(ta, tb, is_knockout=True, tournament_round='knockout_stage')
        base_p = off['poisson']['score_probs']
        synth = {sc.replace('-', ':'): max(1, round(p * 10)) for sc, p in base_p.items() if p >= 1.0}
        cons = engine.predict_with_consensus(
            ta, tb, market_scores=synth, is_knockout=True,
            tournament_round='knockout_stage', use_h2h=True)
        h2h_line = cons.get('h2h_signal', {}).get('scoreline')
        pick = cons.get('score_pick')
        ov = cons.get('h2h_override_applied', False)
        if ov:
            n_override += 1
        print(f"  {ta} vs {tb}: pick={pick}  H2H线={h2h_line}  覆盖触发={'✅' if ov else '❌'}"
              f"  note={cons.get('score_selection_note')}")

    print(f"\n  合成市场下 H2H 偏好覆盖触发: {n_override}/{agg['pairs']}")

    print("\n⚠️  说明: 合成市场仅为演示选择机制; 真实 64 场历史无逐场 participantCount 存档, "
          "无法在本环境复算 15.3%/16.7% 原始指标。选项A完成的是『通路接线 + H2H偏好信号』, "
          "而非『命中率证明』。西班牙2-1(avg2.0/0.96→2:1)在合成市场下可被H2H覆盖正确选中。")


if __name__ == '__main__':
    main()
