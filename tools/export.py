# -*- coding: utf-8 -*-
r"""번역용 추출 — 빠짐없이. 같은 문장은 한 줄(자리 수·최소 예산 표시).

  python tools/export.py      → work/text/{map,msg,ui,data,other}.tsv + 요약

열: 번호 · 종류 · 자리수 · 예산(바이트) · 예시위치 · JP · KO(비어 있음)
  예산 = 그 문장이 나오는 자리 중 가장 작은 «쓸 수 있는 바이트». 한글 1자 = 2 B, ASCII(반각 공백·영숫자·%b·{} 등) = 1 B, 전각 부호 = 2 B.
종류
  map   = 본편 대사(.MAP)
  msg   = 설명·도움말(.MSG .MAT .ADV)
  ui    = 실행 파일 UI 구간(0_OP 170000‥175000 · 1_SRPG 514000‥534000 · 2_SRPGED 510000‥530000) — 반각 가타카나 포함(ﾊﾟﾜｰ:攻撃力+ …)
  data  = 실행 파일 자료표(1_SRPG 534000‥574000: 기술·아이템·장비·몬스터 이름). 예산 = 표의 이름 칸 폭(datatab.widths).
          ★«{ｶｲﾌｸﾔｸ}» 의 중괄호는 «히라가나로 보이기» 표시 — 한글에선 빼도 된다(실기 확인 전).
  other = 위에 안 든 곳(다른 파일·실행 파일의 다른 구간)에서 문장처럼 보이는 것 — 검토용(허수 섞임). 번역할 것이 있으면 알려 달라.
2_SRPGED.BIN 은 1_SRPG 와 같은 내용이라 따로 뽑지 않는다(빌더가 둘 다 쓴다).
"""
import collections, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import strindex, datatab

KANA = re.compile(r'[ぁ-ヿ]')          # 대사·설명은 전각만(반각을 세면 그림 데이터 허수가 쏟아진다)
FULLJP = re.compile(r'[ぁ-ヿ一-鿿]')
PUN = re.compile(r'[、。！？…「」]')
BIN_RANGES = {'/0_OP.BIN': (170000, 175000), '/1_SRPG.BIN': (513500, 534000), '/2_SRPGED.BIN': (509500, 530000)}   # 513612‥ 지명 목록 포함(2026-09-25)


def strip(s):
    return re.sub(r'%[A-Za-z][0-9]*|\\n', '', s)


def real(s):
    t = strip(s)
    return (len(t) >= 2 and len(KANA.findall(t)) >= 0.3 * len(t)) or bool(PUN.search(t))


def other_like(s):
    """다른 곳의 문장 후보 — 허수(그림 데이터가 우연히 SJIS 로 읽힌 것)를 줄이려고 엄격하게:
    전각 가나가 3자 이상이고 문자열의 40% 이상(허수는 대개 드문 한자 나열), 전각 가나·한자가 전체의 70% 이상"""
    t = strip(s)
    if not t:
        return False
    return len(KANA.findall(t)) >= 3 and len(KANA.findall(t)) >= 0.4 * len(t) and len(FULLJP.findall(t)) >= 0.7 * len(t)


def main():
    rows = strindex.load()
    groups = collections.OrderedDict()

    def add(kind, s, n, where):
        g = groups.setdefault((kind, s), [0, n, where])
        g[0] += 1
        g[1] = min(g[1], n)

    d1 = open(os.path.join(ROOT, 'work', '1_SRPG.BIN'), 'rb').read()
    L = datatab.names(d1)
    W = datatab.widths(d1, L)
    for o, b, s in L:
        add('data', s, W[o], '/1_SRPG.BIN@%d' % o)
    for p, lba, off, n, s in rows:
        ext = os.path.splitext(p)[1].upper()
        if p == '/2_SRPGED.BIN':
            continue
        if p in BIN_RANGES and BIN_RANGES[p][0] <= off <= BIN_RANGES[p][1]:
            add('ui', s, n, '%s@%d' % (p, off))
        elif p == '/1_SRPG.BIN' and datatab.LO <= off <= datatab.HI:
            continue                                   # 자료표(위에서)
        elif ext == '.MAP' and real(s):
            add('map', s, n, '%s@%d' % (p, off))
        elif ext in ('.MSG', '.MAT', '.ADV') and real(s):
            add('msg', s, n, '%s@%d' % (p, off))
        elif other_like(s):
            add('other', s, n, '%s@%d' % (p, off))
    os.makedirs(os.path.join(ROOT, 'work', 'text'), exist_ok=True)
    out = collections.defaultdict(list)
    for (kind, s), (cnt, n, where) in groups.items():
        out[kind].append((cnt, n, where, s))
    old = os.path.join(ROOT, 'work', 'text', 'skill.tsv')
    if os.path.exists(old):
        os.remove(old)                                 # data.tsv 로 합침(기술+아이템+장비+몬스터)
    tot = 0
    for kind in ('map', 'msg', 'ui', 'data', 'other'):
        lst = out.get(kind, [])
        with open(os.path.join(ROOT, 'work', 'text', kind + '.tsv'), 'w', encoding='utf-8') as f:
            f.write('#번호\t종류\t자리수\t예산\t예시위치\tJP\tKO\n')
            for k, (cnt, n, where, s) in enumerate(lst):
                f.write('%d\t%s\t%d\t%d\t%s\t%s\t\n' % (k, kind, cnt, n, where, s))
        chars = sum(len(strip(s)) for _, _, _, s in lst)
        print('%-5s 고유 %5d줄 · 약 %6d자' % (kind, len(lst), chars))
        tot += len(lst)
    print('합계 %d줄' % tot)
    per = collections.Counter(w.split('@')[0] for c, n, w, s in out.get('other', []))
    print('other 파일별', per.most_common(15))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
