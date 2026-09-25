# -*- coding: utf-8 -*-
"""문자열 색인 — 디스크의 모든 파일(mato 는 블록마다)에서 NUL 로 끝나는 cp932 문자열을 «파일 안 오프셋»과 함께.

  python tools/strindex.py            → work/strings.tsv (경로 · 파일오프셋 · 원문바이트수 · 문자열)
  python tools/strindex.py 문구 …      → 색인에서 찾기
제자리 덮어쓰기 예산 = 원문 바이트 수(NUL 제외). 파일 크기·mato 블록 경계는 바꾸지 않는다.
"""
import os, re, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from iso9660 import Iso
import survey

RUN = re.compile(rb'(?:[\x20-\x7e\x0a]|[\x81-\x9f\xe0-\xef][\x40-\x7e\x80-\xfc])+\x00')
JP = re.compile(r'[\u3041-\u30ff\u4e00-\u9fff\uff01-\uff5e]')
OUT = os.path.join(ROOT, 'work', 'strings.tsv')


def esc(s):
    return s.replace('\\', '\\\\').replace('\n', '\\n').replace('\t', '\\t')


def build():
    iso = Iso(survey.TRACK1)
    rows = []
    for r in iso.walk():
        path, lba, size = r[0], r[1], r[2]
        if path.endswith('/') or size < 4 or lba + (size + 2047) // 2048 > iso.nsec:
            continue
        d = iso.read(lba, size)
        for m in RUN.finditer(d):
            b = m.group()[:-1]
            try:
                s = b.decode('cp932')
            except UnicodeDecodeError:
                continue
            if JP.search(s):
                rows.append((path, lba, m.start(), len(b), s))
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write('#경로\tLBA\t오프셋\t바이트\t문자열\n')
        for p, lba, o, n, s in rows:
            f.write('%s\t%d\t%d\t%d\t%s\n' % (p, lba, o, n, esc(s)))
    print('문자열 %d → %s' % (len(rows), OUT))


def load():
    out = []
    for ln in open(OUT, encoding='utf-8'):
        if ln.startswith('#'):
            continue
        p, lba, o, n, s = ln.rstrip('\n').split('\t', 4)
        out.append((p, int(lba), int(o), int(n), s))
    return out


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    if len(sys.argv) == 1 or not os.path.exists(OUT):
        build()
    for q in sys.argv[1:]:
        hits = [r for r in load() if q in r[4]]
        print('%s\t%d건' % (q, len(hits)))
        for h in hits[:6]:
            print('    %s @%d (%dB): %s' % (h[0], h[2], h[3], h[4][:60]))
