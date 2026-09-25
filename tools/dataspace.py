# -*- coding: utf-8 -*-
r"""자료표 이름(data.tsv)의 반각 공백 → 전각 «　»(안 들어가면 공백 빼기).
  이름은 «(아이템) 더 못 든다» 같은 가운데 정렬 문장에 끼고, 기술 이름 복사 루프는 0x20 에서 멈춘다(uispace.py 참고).
  python tools/dataspace.py [--write]
"""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import kocheck

FW = '　'
RENAME = {'刺槍': '창찌르기', '痛刺槍': '강창찌르기', '轟刺槍': '폭풍창찌르기'}   # 사용자 2026-09-26 «자창 알아먹기 힘듦»


def fits(r, ko):
    if kocheck.nbytes(ko) > int(r[3]):
        return False
    wmax = max(96, max(kocheck.px(x) for x in kocheck.LINES.split(r[5])))
    return kocheck.px(ko) <= wmax


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    p = os.path.join(ROOT, 'work', 'ko', 'data.tsv')
    L = open(p, encoding='utf-8').read().split('\n')
    fw = nosp = ren = 0
    for i, ln in enumerate(L):
        r = ln.split('\t')
        if len(r) < 7 or not r[6]:
            continue
        if r[5] in RENAME:
            r[6] = RENAME[r[5]]; ren += 1
            assert fits(r, r[6]), r
        if ' ' in r[6].strip():
            a = re.sub(r'(?<=\S) +(?=\S)', FW, r[6])
            if fits(r, a):
                r[6] = a; fw += 1
            else:
                r[6] = re.sub(r'(?<=\S) +(?=\S)', '', r[6]); nosp += 1
                print('  공백 뺌', r[0], r[5], r[6])
        L[i] = '\t'.join(r)
    if '--write' in sys.argv:
        open(p, 'w', encoding='utf-8').write('\n'.join(L))
    print('전각 %d · 공백 뺌 %d · 이름 바꿈 %d%s' % (fw, nosp, ren, '' if '--write' in sys.argv else ' (예행)'))
