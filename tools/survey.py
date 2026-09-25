# -*- coding: utf-8 -*-
"""리그로드 사가 1 디스크 1차 조사 — 파일 목록·매직 분류·mato/FNTC·cp932 문자열 분량 (리그로드 사가 2 도구 재사용)

  python tools/survey.py      → work/files.tsv, work/magics.tsv, 화면 요약
"""
import collections, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from iso9660 import Iso
from mato import Mato

TRACK1 = r'C:\claude\roms\ss\Riglordsaga (Japan) (Made in Japan) (4M)\Riglordsaga (Japan) (Made in Japan) (4M) (Track 1).bin'
WORK = os.path.join(ROOT, 'work')
CP932 = re.compile(rb'(?:[\x81-\x9f\xe0-\xef][\x40-\x7e\x80-\xfc]){3,}')


def main():
    iso = Iso(TRACK1)
    rows = list(iso.walk())
    os.makedirs(WORK, exist_ok=True)
    files = [r for r in rows if not r[0].endswith('/')]
    with open(os.path.join(WORK, 'files.tsv'), 'w', encoding='utf-8') as f:
        for r in rows:
            f.write('\t'.join(str(x) for x in r) + '\n')
    print('항목 %d · 파일 %d · 첫 행 예 %s' % (len(rows), len(files), rows[:2]))
    tally = collections.Counter(); ext = collections.Counter(); jp = collections.Counter(); fntc = []; mato = collections.Counter()
    with open(os.path.join(WORK, 'magics.tsv'), 'w', encoding='utf-8') as out:
        for r in files:
            path, lba, size = r[0], r[1], r[2]
            ext[os.path.splitext(path)[1].upper()] += 1
            if size < 4 or lba + (size + 2047) // 2048 > iso.nsec:   # 트랙 밖(CD-DA 를 가리키는 항목)
                tally['(트랙 밖)'] += size >= 4
                continue
            d = iso.read(lba, size)
            m = d[:4]
            key = m.decode('ascii') if all(32 <= b < 127 for b in m) else m.hex().upper()
            tally[key] += 1
            if b'FNTC' in d:
                fntc.append((path, d.index(b'FNTC')))
            if key == 'mato':
                try:
                    Mato(d, path).check(); mato['ok'] += 1
                except Exception as e:
                    mato['err'] += 1
            n = sum(len(x) // 2 for x in CP932.findall(d))
            jp[path] = n
            out.write('%s\t%s\t%d\t%d\n' % (path, key, size, n))
    print('확장자', ext.most_common(20))
    print('매직', tally.most_common(15))
    print('mato 파싱', dict(mato))
    print('FNTC 들어 있는 파일', fntc[:10])
    print('전각 cp932 문자(대략) 합계 %d · 상위 파일 %s' % (sum(jp.values()), jp.most_common(12)))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
