# -*- coding: utf-8 -*-
r"""번역용 추출 — 실제 문장만, 같은 문장은 한 줄로(자리 수·최소 예산 표시).

  python tools/export.py      → work/text/{map,msg,ui,skill}.tsv

열: 번호 · 종류 · 자리수 · 예산(바이트) · 예시 위치 · JP · KO(비어 있음)
  예산 = 그 문장이 나오는 자리 중 가장 짧은 원문 바이트 수. 한글 1자 = 2바이트, ASCII(반각 공백·영숫자·%b 등) = 1바이트, 전각 부호 = 2바이트.
  빌더는 같은 JP 가 나오는 모든 자리에 KO 를 넣는다(자리마다 원문 길이 안에서).
종류: map = 본편 대사(.MAP) · msg = 설명·도움말(.MSG .MAT .ADV) · ui = 실행 파일 UI 구간 · skill = 기술표 이름(반각/전각, 22바이트 필드)
"""
import collections, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import strindex

KANA = re.compile(r'[ぁ-ヿ]')
PUN = re.compile(r'[、。！？…「」]')
BIN_RANGES = {'/0_OP.BIN': (170000, 175000), '/1_SRPG.BIN': (514000, 534000), '/2_SRPGED.BIN': (510000, 530000)}
SKILL = re.compile(rb'(?<=\x00)((?:[\xa1-\xdf\x20-\x7e]|[\x81-\x9f\xe0-\xef][\x40-\xfc]){2,21}?)\x00')


def real(s):
    t = re.sub(r'%[A-Za-z][0-9]*|\\n', '', s)
    return (len(t) >= 2 and len(KANA.findall(t)) >= 0.3 * len(t)) or bool(PUN.search(t))


def main():
    rows = strindex.load()
    groups = collections.OrderedDict()
    for p, lba, off, n, s in rows:
        ext = os.path.splitext(p)[1].upper()
        if p in BIN_RANGES:
            lo, hi = BIN_RANGES[p]
            if not lo <= off <= hi:
                continue
            kind = 'ui'
        elif ext == '.MAP':
            if not real(s):
                continue
            kind = 'map'
        elif ext in ('.MSG', '.MAT', '.ADV'):
            if not real(s):
                continue
            kind = 'msg'
        else:
            continue
        g = groups.setdefault((kind, s), [0, n, '%s@%d' % (p, off)])
        g[0] += 1
        g[1] = min(g[1], n)
    # 기술표(1_SRPG 540000‥560000, 52바이트 기록의 이름 필드)
    d = open(os.path.join(ROOT, 'work', '1_SRPG.BIN'), 'rb').read()
    for m in SKILL.finditer(d, 540000, 560000):
        try:
            s = m.group(1).decode('cp932')
        except UnicodeDecodeError:
            continue
        if re.search(r'[｡-ﾟぁ-ヿ一-鿿]', s):
            g = groups.setdefault(('skill', s), [0, 21, '/1_SRPG.BIN@%d' % m.start(1)])
            g[0] += 1
    os.makedirs(os.path.join(ROOT, 'work', 'text'), exist_ok=True)
    out = collections.defaultdict(list)
    for (kind, s), (cnt, n, where) in groups.items():
        out[kind].append((cnt, n, where, s))
    tot = 0
    for kind, lst in out.items():
        with open(os.path.join(ROOT, 'work', 'text', kind + '.tsv'), 'w', encoding='utf-8') as f:
            f.write('#번호\t종류\t자리수\t예산\t예시위치\tJP\tKO\n')
            for k, (cnt, n, where, s) in enumerate(lst):
                f.write('%d\t%s\t%d\t%d\t%s\t%s\t\n' % (k, kind, cnt, n, where, s))
        chars = sum(len(re.sub(r'%[A-Za-z][0-9]*|\\n', '', s)) for _, _, _, s in lst)
        print('%-5s 고유 %5d줄 · 약 %6d자' % (kind, len(lst), chars))
        tot += len(lst)
    print('합계 %d줄' % tot)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
