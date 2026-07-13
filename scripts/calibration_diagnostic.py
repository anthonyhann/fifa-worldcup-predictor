"""
分布级校准诊断 — 旧引擎(v4.14)在 比分/总进球 单点pick上的置信度是否校准?
=========================================================================
用 review_log 中 100+ market 条目的 model_confidence(模型给pick的概率)
vs correct(是否命中) 做可靠性曲线(calibration)检查:
  - 若模型说 15% 的pick实际命中~15% → 校准良好, 问题在分布中心(xG)
  - 若模型说 15% 实际命中仅 5%  → 过度自信, 需压低峰值/加离散
  - 若模型说 15% 实际命中 30%  → 欠自信, 可提高峰值集中度
"""
import os, sys, json
from collections import defaultdict

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(SKILL_DIR, 'logs', 'review_log.jsonl')


def load():
    rows = [json.loads(l) for l in open(LOG, encoding='utf-8') if l.strip()]
    out = []
    for r in rows:
        t = r.get('type')
        if t in ('score', 'total_goals') and r.get('model_confidence') is not None \
           and r.get('correct') is not None:
            out.append({'type': t, 'conf': float(r['model_confidence']),
                        'correct': bool(r['correct'])})
    return out


def reliability(data, bins):
    """返回每个bin的 平均模型置信度 / 实际命中率 / 样本数"""
    edges = [i / bins for i in range(bins + 1)]
    buckets = defaultdict(list)
    for d in data:
        b = min(int(d['conf'] / 100 * bins), bins - 1)
        buckets[b].append(d)
    rows = []
    for b in range(bins):
        items = buckets[b]
        if not items:
            continue
        mean_conf = sum(x['conf'] for x in items) / len(items) / 100
        act = sum(1 for x in items if x['correct']) / len(items)
        lo, hi = int(edges[b] * 100), int(edges[b + 1] * 100)
        rows.append({'bin': f"{lo}-{hi}%", 'n': len(items),
                     'conf': round(mean_conf * 100, 1), 'actual': round(act * 100, 1)})
    return rows


def main():
    data = load()
    sc = [d for d in data if d['type'] == 'score']
    tg = [d for d in data if d['type'] == 'total_goals']
    print(f"可用market条目: score={len(sc)}, total_goals={len(tg)}")
    for name, subset in [('比分 score', sc), ('总进球 total_goals', tg)]:
        print(f"\n===== {name} 可靠性曲线 (bin=5%) =====")
        print(f"  {'区间':>8} {'n':>4} {'模型置信':>9} {'实际命中':>9} {'偏差':>7}")
        overall_conf = sum(d['conf'] for d in subset) / len(subset)
        overall_act = sum(1 for d in subset if d['correct']) / len(subset) * 100
        for r in reliability(subset, 20):
            bias = r['actual'] - r['conf']
            flag = '⚠️过自信' if bias < -5 else ('⚠️欠自信' if bias > 5 else '✅')
            print(f"  {r['bin']:>8} {r['n']:>4} {r['conf']:>8.1f}% {r['actual']:>8.1f}% {bias:>+6.1f}% {flag}")
        print(f"  --- 整体: 模型置信均值 {overall_conf:.1f}% | 实际命中 {overall_act:.1f}% | "
              f"偏差 {overall_act-overall_conf:+.1f}pt")


if __name__ == '__main__':
    main()
