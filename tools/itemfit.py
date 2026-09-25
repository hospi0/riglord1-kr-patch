# -*- coding: utf-8 -*-
r"""아이템 목록 이름 칸 = 60px(한글 5자) — 개수 «×N» 이 이름 시작 +62px 에 고정으로 찍힌다(실기 2026-09-26 «마나의 물×3방울»).
  원문 목록 이름은 반각 가나(8px)라 들어갔다. 소모품·장신구(157‥201)만: 공백 빼서 5자면 그대로, 아니면 SHORT.
  python tools/itemfit.py [--write]
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import kocheck

LIMIT = 60
SHORT = {'マナのしずく': '마나물방울', 'ﾏﾅ{ﾉｼｽﾞｸ}': '마나물방울', 'マナの結晶': '마나결정', 'ﾏﾅ{ﾉｹｯｼｮｳ}': '마나결정'}

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    p = os.path.join(ROOT, 'work', 'ko', 'data.tsv')
    L = open(p, encoding='utf-8').read().split('\n')
    n = 0
    for i, ln in enumerate(L):
        r = ln.split('\t')
        if len(r) < 7 or not r[6] or not r[0].isdigit() or not 157 <= int(r[0]) <= 201:
            continue
        if kocheck.px(r[6]) <= LIMIT or r[5].startswith('ボツ'):     # ボツ = 안 쓰는 디버그 아이템
            continue
        new = SHORT.get(r[5]) or r[6].replace('　', '').replace(' ', '')
        assert kocheck.px(new) <= LIMIT, ('5자 넘음 — SHORT 에 넣을 것', r[0], r[5], new)
        print(' ', r[0], r[5], r[6], '→', new)
        r[6] = new; L[i] = '\t'.join(r); n += 1
    if '--write' in sys.argv:
        open(p, 'w', encoding='utf-8').write('\n'.join(L))
    print('바꾼 이름 %d%s' % (n, '' if '--write' in sys.argv else ' (예행)'))
