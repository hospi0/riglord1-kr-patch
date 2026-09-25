# -*- coding: utf-8 -*-
r"""적 정보 화면 설명문 = PF_xx.PRF 뒤쪽 글(128×160 RGB555 그림 40,960 B + 머리 4 B 뒤, 파일 끝까지).
  2026-09-26 실기(«적1/적2») — 추출에서 빠져 있었다(69종, PF_48·PF_71 은 같은 글).
  화면은 한 줄 10자에서 자동으로 접힌다 → 낱말 경계에서 «\r\n» 으로 직접 끊는다(한 줄 ≤ 10자, 공백·부호도 1자).
  예산 = 원문 글 바이트(파일 크기 불변). 남는 자리는 마지막 줄 뒤 반각 공백으로 채운다(보이지 않음). 끝 표시(\r\n·\x1a)는 원문 그대로.
  work/text/prf.tsv(번호·파일·예산·JP) + work/ko/prf.tsv(번호·KO, «\n» = 강제 줄바꿈)
  python tools/prf.py            # 검사·미리보기
"""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

LINE = 120                  # ★px — 전각·한글 12, 반각 6 (실기 «후 왕자의 교육을 맡» = 120px 한 줄, 2026-09-26)
TOKW = {'%s1': 48}          # 인물 이름 자리(최대 4자로 본다)


def load():
    src = {}
    for ln in open(os.path.join(ROOT, 'work', 'text', 'prf.tsv'), encoding='utf-8'):
        if ln.startswith('#') or not ln.strip():
            continue
        r = ln.rstrip('\n').split('\t')
        src[r[0]] = (r[1].split(','), int(r[2]), r[3])
    ko = {}
    p = os.path.join(ROOT, 'work', 'ko', 'prf.tsv')
    if os.path.exists(p):
        for ln in open(p, encoding='utf-8'):
            if ln.startswith('#') or not ln.strip():
                continue
            r = ln.rstrip('\n').split('\t')
            if len(r) >= 2 and r[1]:
                ko[r[0]] = r[1]
    return src, ko


def ulen(s):
    n = 0
    for t in re.split(r'(%s\d)', s):
        if t.startswith('%s'):
            n += TOKW.get(t, 48)
        else:
            n += sum(6 if ord(c) < 0x80 else 12 for c in t)
    return n


def wrap(text):
    """낱말 경계로 한 줄 ≤ LINE 자. «\\n» 은 강제 줄바꿈."""
    lines = []
    for para in text.split('\\n'):
        cur = ''
        for w in para.split(' '):
            cand = (cur + ' ' + w) if cur else w
            if ulen(cand) <= LINE:
                cur = cand
            else:
                if cur:
                    lines.append(cur)
                assert ulen(w) <= LINE, ('한 낱말이 %d자 넘음' % LINE, w)
                cur = w
        lines.append(cur)
    return lines


def encode(text, jp, budget, enc):
    """KO → 바이트(원문 끝 표시 유지, 예산까지 공백 채움)"""
    tail = ''
    m = re.search(r'((?:\\n)?(?:<EOF>)?)$', jp)
    tail = m.group(1)
    body = '\r\n'.join(wrap(text))
    tb = tail.replace('\\n', '\r\n').replace('<EOF>', '\x1a').encode('cp932')
    b = enc(body)
    pad = budget - len(b) - len(tb)
    return b + b' ' * pad + tb, pad


def check(enc=None):
    enc = enc or (lambda s: s.encode('cp932', 'replace') if False else bytes(sum(2 if ord(c) >= 0x80 else 1 for c in s)))
    src, ko = load()
    err = []
    for k, (files, budget, jp) in src.items():
        if k not in ko:
            continue
        try:
            b, pad = encode(ko[k], jp, budget, enc)
        except AssertionError as e:
            err.append('%s %s' % (k, e)); continue
        if pad < 0:
            err.append('%s 예산 %dB 초과 %dB: %s' % (k, budget, -pad, ko[k][:30]))
        if len(wrap(ko[k])) > 12:
            err.append('%s %d줄 > 12' % (k, len(wrap(ko[k]))))
        if '…' in ko[k]:
            err.append('%s «…» 금지' % k)
    return src, ko, err


def export():
    """ROM → work/text/prf.tsv (같은 글은 한 줄)"""
    import collections, project
    from iso9660 import Iso
    iso = Iso(project.TRACK1)
    by = collections.OrderedDict()
    for p, lba, size, *_ in iso.walk():
        if not p.endswith('.PRF'):
            continue
        d = iso.read(lba, size)
        assert d[:4] == b'\x00\x80\x00\xa0', p
        by.setdefault(d[40964:], []).append(p)
    with open(os.path.join(ROOT, 'work', 'text', 'prf.tsv'), 'w', encoding='utf-8') as f:
        f.write('#번호\t파일\t예산\tJP\n')
        for k, (t, ps) in enumerate(by.items()):
            s = t.decode('cp932').replace('\r\n', '\\n').replace('\x1a', '<EOF>')
            assert '\n' not in s and '\t' not in s, s
            f.write('%d\t%s\t%d\t%s\n' % (k, ','.join(ps), len(t), s))
    print('PRF %d종 → work/text/prf.tsv' % len(by))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    if '--export' in sys.argv:
        export()
    src, ko, err = check()
    for e in err:
        print('⛔', e)
    print('PRF %d종 · 번역 %d · 오류 %d' % (len(src), len(ko), len(err)))
    if '-v' in sys.argv:
        for k in ko:
            print('--', k); print('\n'.join(wrap(ko[k])))
