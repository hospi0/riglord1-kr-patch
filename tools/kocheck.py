# -*- coding: utf-8 -*-
r"""번역 검사 — «쓰는 순간» 돌린다(ROM 불필요).

  python tools/kocheck.py              # work/ko/*.tsv 전부 (work/text/X.tsv 를 복사해 KO 열을 채운 것)
  python tools/kocheck.py 파일.tsv

막는 것:
  - 바이트 예산 초과: 한글 1자 = 2 B(도너 코드), ASCII(반각 공백·영숫자·%b 등) = 1 B, 그 밖(전각 부호 등) = 2 B. 예산 = 예산 열.
  - 제어 토큰 불일치: %b %h %H %m0 %m1 %V0 %V100 %s0 등 — 개수·종류가 원문과 같아야 한다.
  - 줄 폭: `\n` 으로 나뉜 각 줄의 화면 폭이 원문 같은 순번 줄 중 가장 넓은 줄보다 넓으면 오류
    (글리프 12px: 전각·한글 = 12, 반각 = 6 — 리그로드 사가 2 실측과 같은 렌더러).
  - 번역에 남은 가나·한자.
규칙(자동): 문장부호(, . ! ? : ;) 뒤 공백은 빌더가 지운다 — 검사도 지운 뒤 기준.
"""
import glob, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN = re.compile(r'%[A-Za-z][0-9]*')
JPCH = re.compile(r'[ぁ-ヿ一-鿿｡-ﾟ]')


def squeeze(s):
    return re.sub(r'([,.!?:;])[ ]+(?=\S)', r'\1', s)


def nbytes(s):
    n = 0
    for c in s.replace('\\n', '\n'):
        n += 1 if ord(c) < 0x80 else 2
    return n


def px(line):
    """화면 폭. 반각 가타카나는 화면에서 전각으로 바뀌어 보인다(ｽﾄﾗｲｸ → ストライク) → 12px, 탁점·반탁점(ﾞﾟ)은 앞 글자에 붙어 0.
    중괄호 {} 는 «히라가나로 보이기» 표시라 폭 0."""
    t = TOKEN.sub('', line)
    w = 0
    for c in t:
        o = ord(c)
        if c in 'ﾞﾟ{}':
            continue
        w += 6 if o < 0x80 else 12
    return w


def check(fn):
    err, done = [], 0
    for ln in open(fn, encoding='utf-8'):
        if ln.startswith('#') or not ln.strip():
            continue
        r = ln.rstrip('\n').split('\t')
        if len(r) < 7 or not r[6]:
            continue
        done += 1
        num, kind, budget, jp, ko = r[0], r[1], int(r[3]), r[5], squeeze(r[6])
        where = '%s:%s' % (os.path.basename(fn), num)
        if nbytes(ko) > budget:
            err.append('%s 예산 %dB < %dB: %s' % (where, budget, nbytes(ko), ko[:40]))
        if sorted(TOKEN.findall(jp)) != sorted(TOKEN.findall(ko)):
            err.append('%s 토큰 불일치 JP%s KO%s' % (where, TOKEN.findall(jp), TOKEN.findall(ko)))
        if JPCH.search(TOKEN.sub('', ko)):
            err.append('%s 일본어 남음: %s' % (where, ko[:40]))
        jl = jp.split('\\n'); kl = ko.split('\\n')
        wmax = max(px(x) for x in jl)
        for k, line in enumerate(kl):
            if px(line) > wmax:
                err.append('%s %d번째 줄 폭 %dpx > 원문 최대 %dpx: %s' % (where, k + 1, px(line), wmax, line[:30]))
    return err, done


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    files = sys.argv[1:] or sorted(glob.glob(os.path.join(ROOT, 'work', 'ko', '*.tsv')))
    E = D = 0
    for fn in files:
        if os.path.basename(fn).startswith('00_poc'):
            continue                      # PoC 파일은 형식이 다르다(대상·JP·KO) — 빌더가 예산 검사
        e, d = check(fn)
        for x in e:
            print('⛔', x)
        E += len(e); D += d
    print('번역 %d줄 · 오류 %d' % (D, E))
    sys.exit(1 if E else 0)
