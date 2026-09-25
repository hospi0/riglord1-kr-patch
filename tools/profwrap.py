# -*- coding: utf-8 -*-
r"""인물 소개 글(ui 321‥333, 1_SRPG) — 적 설명(PRF)과 같은 렌더러: 한 줄 120px 에서 자동으로 접힌다
  → «맡/아» 처럼 낱말이 잘리고 줄 앞에 공백이 온다(실기 2026-09-26). 낱말 경계에서 «\n» 으로 다시 접는다.
  python tools/profwrap.py [--write]
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import kocheck, prf

IDS = set(map(str, range(321, 334)))

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    p = os.path.join(ROOT, 'work', 'ko', 'ui.tsv')
    L = open(p, encoding='utf-8').read().split('\n')
    n = 0
    for i, ln in enumerate(L):
        r = ln.split('\t')
        if len(r) < 7 or r[0] not in IDS or not r[6]:
            continue
        paras = r[6].split('\\n')                                 # 원문 문단 나눔은 살리고 문단 안에서만 다시 접는다
        new = '\\n'.join('\\n'.join(prf.wrap(x)) for x in paras)
        nb = kocheck.nbytes(kocheck.squeeze(new))
        print(r[0], '예산', r[3], '→', nb, 'B', '줄', new.count('\\n') + 1, '⛔넘침' if nb > int(r[3]) else '')
        if nb <= int(r[3]):
            r[6] = new; L[i] = '\t'.join(r); n += 1
    if '--write' in sys.argv:
        open(p, 'w', encoding='utf-8').write('\n'.join(L))
    print('다시 접은 줄 %d%s' % (n, '' if '--write' in sys.argv else ' (예행)'))
