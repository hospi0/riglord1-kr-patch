# -*- coding: utf-8 -*-
r"""번역의 «…»(U+2026, SJIS 8163) → 반각 «...» — 본문 글꼴(INO4INIT·TITLE2)에 8163 글리프가 없어 빈칸으로 나온다(실기 2026-09-26: «여긴  ?», 첫 줄 들여쓰기, 겐유사이 빈 대사).
  «…» + 마침표(«….») → «...» 하나로 · «……» → «......».
  python tools/ellipsis.py          # 예행: 넘치는 줄만 보인다
  python tools/ellipsis.py --write  # work/ko/*.tsv 에 쓴다(넘치는 줄은 쓰지 않고 목록만)
"""
import glob, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import kocheck

E = '…'


def conv(s):
    s = re.sub(E + r'+\.', lambda m: '...' * (len(m.group(0)) - 1), s)   # «….» → «...», «…….» → «......»
    return s.replace(E, '...')


def fits(r, ko):
    jp = r[5]
    if kocheck.nbytes(kocheck.squeeze(ko)) > int(r[3]):
        return False
    wmax = max(kocheck.px(x) for x in kocheck.LINES.split(jp))
    if r[1] == 'data':
        wmax = max(wmax, 96)
    return max(kocheck.px(x) for x in kocheck.LINES.split(ko)) <= wmax


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    write = '--write' in sys.argv
    n = 0; bad = []
    for fn in sorted(glob.glob(os.path.join(ROOT, 'work', 'ko', '*.tsv'))):
        L = open(fn, encoding='utf-8').read().split('\n')
        for i, ln in enumerate(L):
            r = ln.split('\t')
            if len(r) >= 7 and E in r[6]:
                ko = conv(r[6])
                if fits(r, ko):
                    r[6] = ko; L[i] = '\t'.join(r); n += 1
                else:
                    bad.append((os.path.basename(fn), r[0], r[3], r[5], r[6]))
            elif len(r) == 3 and E in r[2]:                 # PoC 형식(대상·JP·KO) — 예산 열 없음, kocheck 가 따로 본다
                r[2] = conv(r[2]); L[i] = '\t'.join(r); n += 1
        if write:
            open(fn, 'w', encoding='utf-8').write('\n'.join(L))
    print('바꾼 줄 %d · 넘쳐서 남긴 줄 %d%s' % (n, len(bad), '' if write else ' (예행)'))
    for b in bad:
        print('  %s %s 예산%s | %s | %s' % b)
