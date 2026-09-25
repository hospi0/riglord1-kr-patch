# -*- coding: utf-8 -*-
"""대사·문구 분량 — NUL 로 끝나는 cp932 문자열 중 가나·한자가 든 것만(그림 데이터 허수 제외). 같은 문장 중복 제거.

  python tools/corpus.py   → 확장자별 문자열 수·글자 수, 고유 전각 글자 수, 예시
"""
import collections, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from iso9660 import Iso
from mato import Mato
import survey

RUN = re.compile(rb'(?:[\x20-\x7e\x0a]|[\x81-\x9f\xe0-\xef][\x40-\x7e\x80-\xfc])+\x00')
JP = re.compile(r'[ぁ-ヿ一-鿿]')


def strings(data):
    for m in RUN.finditer(data):
        b = m.group()[:-1]
        try:
            s = b.decode('cp932')
        except UnicodeDecodeError:
            continue
        if len(JP.findall(s)) >= 2:
            yield s


def main():
    iso = Iso(survey.TRACK1)
    per_ext = collections.defaultdict(dict)
    for r in iso.walk():
        path, lba, size = r[0], r[1], r[2]
        if path.endswith('/') or size < 4 or lba + (size + 2047) // 2048 > iso.nsec:
            continue
        d = iso.read(lba, size)
        blocks = Mato(d, path).blocks() if d[:4] == b'mato' else [d]
        ext = os.path.splitext(path)[1].upper()
        for b in blocks:
            for s in strings(b):
                per_ext[ext].setdefault(s, path)
    uniq = {}
    for ext, ss in per_ext.items():
        for s, p in ss.items():
            uniq.setdefault(s, (ext, p))
    by = collections.Counter(); chars = collections.Counter()
    for s, (ext, p) in uniq.items():
        by[ext] += 1
        chars[ext] += len(JP.findall(s)) + sum(1 for c in s if '　' <= c <= '￯' and not JP.match(c))
    allc = set(c for s in uniq for c in s if ord(c) > 0x7f)
    print('고유 문자열 %d · 전각 글자 합 %d · 고유 전각 글자 %d' % (len(uniq), sum(chars.values()), len(allc)))
    for ext, n in by.most_common():
        ex = next(s for s, (e, _) in uniq.items() if e == ext)
        print('  %-6s 문자열 %5d · 글자 %7d · 예: %s' % (ext, n, chars[ext], ex[:40].replace('\n', '⏎')))
    with open(os.path.join(ROOT, 'work', 'corpus_ja.tsv'), 'w', encoding='utf-8') as f:
        for s, (ext, p) in uniq.items():
            f.write('%s\t%s\n' % (p, s.replace('\n', '\\n')))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
