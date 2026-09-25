# -*- coding: utf-8 -*-
r"""실행 파일 뒤쪽 «자료표»(기술·아이템·장비·몬스터 이름) — 1_SRPG.BIN 534000‥574000 (2_SRPGED.BIN 은 같은 내용이 4420 B 앞).

이름 = 앞 바이트 NUL/0xFF + (반각 가타카나·ASCII 또는 SJIS 전각) 2‥21 B + NUL. 반각·전각 섞임(ｽﾄﾗｲｸ / 防御 / ｶｲﾌｸﾔｸ → 화면엔 히라가나).
★칸 폭(예산): 같은 간격(stride)으로 늘어선 기록 묶음마다 «이름 시작 → 다음 0 아닌 바이트» 거리의 최솟값. 거기서 NUL 1 B 를 뺀 것이 쓸 수 있는 최대.
  (기술표: 52 B 기록 · 이름 칸 22 B 실측 — 2026-09-25)
"""
import re

LO, HI = 534000, 574000
NAME = re.compile(rb'(?<=[\x00\xff])((?:[\xa1-\xdf\x20-\x7e]|[\x81-\x9f\xe0-\xef][\x40-\xfc]){2,21}?)\x00')
JP = re.compile(r'[｡-ﾟぁ-ヿ一-鿿]')


def names(d, lo=LO, hi=HI):
    """[(오프셋, 원문 바이트, 문자열)] — 영문자가 섞인 허수(ｴA 등)는 뺀다."""
    out = []
    for m in NAME.finditer(d, lo, hi):
        b = m.group(1)
        try:
            s = b.decode('cp932')
        except UnicodeDecodeError:
            continue
        if len(JP.findall(s)) >= 2 and not re.search(r'[A-Za-z#]', s):
            out.append((m.start(1), b, s))
    return out


def widths(d, lst):
    """오프셋 → 쓸 수 있는 최대 바이트(NUL 1 B 제외). 같은 간격 묶음의 최솟값."""
    free = {}
    for o, b, s in lst:
        e = o + len(b)
        while e < len(d) and d[e] == 0 and e - o < 64:
            e += 1
        free[o] = e - o
    out = {}
    run = []
    offs = [o for o, _, _ in lst]
    for k, o in enumerate(offs):
        if run and (o - run[-1] != (run[-1] - run[-2] if len(run) > 1 else o - run[-1]) or o - run[-1] > 256):
            w = min(free[x] for x in run)
            for x in run:
                out[x] = min(w, 22) - 1
            run = []
        run.append(o)
    if run:
        w = min(free[x] for x in run)
        for x in run:
            out[x] = min(w, 22) - 1
    for o, b, s in lst:                         # 원문 길이보다 작게 잡히지는 않게
        out[o] = max(out[o], len(b))
    return out
