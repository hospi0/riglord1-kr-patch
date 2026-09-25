# -*- coding: utf-8 -*-
r"""엔딩 제작진 명단 /STAFF_01‥16.DG2 — 직함(작은 가타카나)만 한글로. 이름(붓글씨 한자)·로고·저작권은 그대로(사용자 결정 2026-09-25).

DG2(STAFF 형): 'PP' · u16 BE 가로 픽셀(0x140) · u16 BE 세로 픽셀(0xE0) · 팔레트 256 × u16 BE · 8bpp 320×224.
  (PROLO 형은 u16 LE «256 단위» — 머리가 둘)
직함 위치: 자동 검출은 뒤쪽 장(이름도 작은 글자)에서 섞여서 «대략 상자»를 손으로 지정 → 상자 안 바탕 아닌 화소의 실제 범위로 좁힌다.
새 글자: 갈무리9 · 자간 3px(원본 직함은 글자 사이가 넓다) · 금색 한 가지(사용자 지정).

  python tools/staff.py          → my files/그래픽/02_엔딩직함(왼원본_오른한글).png
"""
import os, struct, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import bdf2 as bdf

GALMURI9 = 'C:/claude/utils/font/Galmuri-v2.40.3/Galmuri9.bdf'
W, H = 320, 224
TRACK = 3

# 장 번호 → [(대략 상자 x0,y0,x1,y1, 한글 직함, 정렬 r/l/c)] — 격자 확대 그림에서 읽음(2026-09-25)
ROLES = {
    2: [((40, 159, 141, 178), '게임 디자인', 'r'), ((15, 178, 141, 196), '치프 프로그래머', 'r')],
    3: [((50, 145, 131, 167), '프로그래머', 'r'), ((20, 175, 76, 190), '시나리오', 'l'), ((20, 190, 101, 205), '프로그래머', 'l')],
    4: [((15, 149, 136, 168), '시나리오 라이터', 'r'), ((55, 168, 136, 186), '매뉴얼', 'r')],
    5: [((195, 141, 301, 162), '캐릭터 CG', 'r')],
    6: [((25, 136, 111, 157), '맵 CG', 'l')],
    7: [((55, 138, 136, 157), '뮤직', 'r'), ((18, 156, 136, 175), '사운드 이펙트', 'r'), ((18, 190, 134, 210), '스페셜 땡스', 'r')],
    8: [((98, 141, 223, 159), '툴 프로그래머', 'c'), ((105, 159, 216, 178), '시스템 서포트', 'c')],
    9: [((15, 131, 139, 151), '3D 시스템 서포트', 'l')],
    10: [((30, 18, 213, 39), '마케팅 스태프', 'l')],
    11: [((22, 18, 156, 39), '슈퍼바이저', 'l'), ((120, 112, 303, 132), '어드바이저리 스태프', 'l')],
    15: [((40, 24, 143, 46), '디렉터', 'l'), ((40, 114, 158, 134), '프로듀서', 'l')],
    16: [((45, 65, 276, 87), '이그제큐티브 프로듀서', 'l')],
}


def parse(d):
    assert d[:2] == b'PP'
    w, h = struct.unpack_from('>HH', d, 2)
    assert (w, h) == (W, H), (w, h)
    pal = [struct.unpack_from('>H', d, 6 + 2 * k)[0] for k in range(256)]
    return pal, np.frombuffer(d[518:518 + W * H], dtype=np.uint8).reshape(H, W).copy()


def text_mask(text, G, asc):
    cols = []
    for ch in text:
        if ch == ' ':
            cols += [[0] * 12] * 4
            continue
        arr, adv = bdf.render(G, asc, ord(ch), 12, 12, asc)
        xs = [x for row in arr for x, v in enumerate(row) if v] or [0]
        for x in range(min(xs), max(xs) + 1):
            cols.append([arr[y][x] for y in range(12)])
        cols += [[0] * 12] * TRACK
    while cols and not any(cols[-1]):
        cols.pop()
    rows = [y for y in range(12) if any(c[y] for c in cols)]
    return np.array([[c[y] for c in cols] for y in range(rows[0], rows[-1] + 1)], dtype=bool)


def build(d, no):
    pal, a = parse(d)
    bg = int(np.bincount(a.ravel()).argmax())
    roles = ROLES.get(no)
    if not roles:
        return d
    G, asc = bdf.load(GALMURI9)
    lum = lambda k: ((pal[k] & 31) + ((pal[k] >> 5) & 31) + ((pal[k] >> 10) & 31))
    for (x0, y0, x1, y1), text, align in roles:
        box = a[y0:y1 + 1, x0:x1 + 1]
        ys, xs = np.nonzero(box != bg)
        assert len(ys), 'STAFF_%02d %s 상자에 글자 없음' % (no, text)
        ty0, ty1, tx0, tx1 = y0 + ys.min(), y0 + ys.max(), x0 + xs.min(), x0 + xs.max()
        pts = [(y0 + y, x0 + x) for y, x in zip(ys, xs)]
        # ★금색 한 가지(사용자 지정 2026-09-26 «그냥 금색 단색으로») — 원본 직함 화소 중 금색 계열(R≥G≥B)에서 밝은 쪽 상위 색.
        #   (줄별 명암·그림자를 따라 했더니 상자 안 어두운 반사 화소가 뽑혀 글자가 안 보였다)
        def rgb(k):
            c = pal[k]
            return (c & 31), ((c >> 5) & 31), ((c >> 10) & 31)
        golds = sorted({a[p] for p in pts if rgb(a[p])[0] >= rgb(a[p])[1] >= rgb(a[p])[2] and lum(a[p]) >= 30}, key=lum)
        gold = golds[-2] if len(golds) >= 2 else golds[-1]     # 가장 밝은 한 점(반짝임)은 피한다
        for p in pts:
            a[p] = bg
        m = text_mask(text, G, asc)
        mh, mw = m.shape
        oy = (ty0 + ty1) // 2 - mh // 2
        ox = {'r': tx1 - mw + 1, 'l': tx0, 'c': (tx0 + tx1 + 1) // 2 - mw // 2}[align]
        assert 0 <= ox and ox + mw + 1 < W, ('STAFF_%02d %s 가로 넘침' % (no, text))
        for yy in range(mh):
            for xx in range(mw):
                if m[yy, xx]:
                    a[oy + yy, ox + xx] = gold
    return d[:518] + a.tobytes() + d[518 + W * H:]


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    from iso9660 import Iso
    import project
    from PIL import Image
    iso = Iso(project.TRACK1)
    ent = {r[0]: r for r in iso.walk()}
    nos = sorted(ROLES)
    before, after = [], []
    for no in nos:
        p = '/STAFF_%02d.DG2' % no
        d = iso.read(ent[p][1], ent[p][2])
        nd = build(d, no)
        assert len(nd) == len(d)
        for dd, lst in ((d, before), (nd, after)):
            pal, a = parse(dd)
            rgb = np.array([((c & 31) << 3, ((c >> 5) & 31) << 3, ((c >> 10) & 31) << 3) for c in pal], dtype=np.uint8)
            lst.append(Image.fromarray(rgb[a]))
    n = len(nos)
    out = Image.new('RGB', (W * 2, H * n))
    for k in range(n):
        out.paste(before[k], (0, k * H)); out.paste(after[k], (W, k * H))
    pth = os.path.join(ROOT, 'my files', '그래픽', '02_엔딩직함(왼원본_오른한글).png')
    import io
    buf = io.BytesIO(); out.save(buf, 'PNG')
    open(pth, 'wb').write(buf.getvalue())     # 한글 경로에 PIL 직접 저장이 가끔 «Invalid argument» 로 실패
    print('저장', pth)
