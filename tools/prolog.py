# -*- coding: utf-8 -*-
r"""오프닝 내레이션 그림 /PROLO_00.DG2 한글판.

DG2 형식(실측 2026-09-25): 'PP' · u16 LE 가로/256 · u16 LE 세로/256 · 팔레트 256색 × u16 BE(새턴 RGB555) · 8bpp 비트맵.
  PROLO_00 = 1024×512, 색 0 = 투명(하늘색), 1(검정)‥14(흰색) 회색 단계. 장면 6개가 3열×2행으로 한 장에.
  원본: 붓글씨 흰 글자 + 검은 테두리, 줄 간격 20px, 글자 높이 17‥19px.
한글: 연성체(YeonSung, 붓글씨 느낌)로 흰 글자 + 테두리 2px → 원본 회색 단계로 양자화. 파일 크기 불변.

  python tools/prolog.py        → my files/그래픽/01_오프닝내레이션(위원본_아래한글).png 미리보기
"""
import os, struct, sys
from PIL import Image, ImageDraw, ImageFont
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
FONT = 'C:/claude/utils/font/yeonsung/YeonSung-Regular.ttf'
SIZE = 18
STROKE = 1
TRACK = 2          # 자간(원본 붓글씨는 글자 사이가 넓다)
SHADOW = (1, 1)    # 오른쪽 아래 그림자(원본 테두리 명암)
PITCH = 20
W, H = 1024, 512

# (열, 행) 장면 → 줄들. 문장부호 뒤 공백은 두지 않는다(전 프로젝트 규칙).
SCENES = {
    (0, 0): ['이 땅,리그로드는', '풍요로운 대지와 아름다운 자연이', '길러 온 대륙이다.', '그곳에서는 네 나라가', '서로 미워하는 일 없이', '평화로운 시간을 새겨 가고 있었다.'],
    (1, 0): ['그러나', '평화가 영원히 이어지는 일은 없다.', '어느 시대나', '그러했듯이…'],
    (2, 0): ['머나먼 동방,', '야마타이라 불리는 나라에서', '마장군 겐유사이와 그 군단이', '바다를 건너 나타났다.'],
    (0, 1): ['그 군단은', '퀸즈랜드 여왕국을', '순식간에 손아귀에 넣고', '다시 다른 나라들을 향해', '진군을 시작한 것이다.'],
    (1, 1): ['재야로 내려간 왕자 일행은', '반격의 기회를 엿보며', '방랑의 여행을 이어 가다…', '그리고 마침내', '겐유사이와', '대결할 때를 맞이했다.'],
    (2, 1): ['리그로드의 역사를 바꿀', '전설의 싸움이', '지금 여기서 막을 연다…'],
}
COLW = [(0, 341), (341, 682), (682, 1024)]
ROWH = [(0, 256), (256, 512)]


def parse(d):
    assert d[:2] == b'PP'
    w, h = struct.unpack_from('<HH', d, 2)
    pal = [struct.unpack_from('>H', d, 6 + 2 * k)[0] for k in range(256)]
    return w * 256, h * 256, pal, np.frombuffer(d[518:], dtype=np.uint8).reshape(h * 256, w * 256).copy()


def lum_table(pal):
    return {k: ((pal[k] & 31) + ((pal[k] >> 5) & 31) + ((pal[k] >> 10) & 31)) * 255 // 93 for k in range(1, 15)}


def render_block(lines):
    font = ImageFont.truetype(FONT, SIZE)
    def width(t):
        return sum(int(font.getlength(c)) + (TRACK if c != ' ' else 0) for c in t)
    wmax = max(width(t) for t in lines) + 2 * STROKE + 6
    im = Image.new('RGBA', (wmax, PITCH * len(lines) + 10), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    for k, t in enumerate(lines):
        for layer in ('shadow', 'text'):
            x = STROKE + 1
            for c in t:
                y = k * PITCH + 1
                if layer == 'shadow':
                    dr.text((x + SHADOW[0], y + SHADOW[1]), c, font=font, fill=(40, 40, 40, 255), stroke_width=STROKE, stroke_fill=(0, 0, 0, 255))
                else:
                    dr.text((x, y), c, font=font, fill=(255, 255, 255, 255), stroke_width=STROKE, stroke_fill=(0, 0, 0, 255))
                x += int(font.getlength(c)) + (TRACK if c != ' ' else 0)
    return np.asarray(im)


def build(d):
    w, h, pal, a = parse(d)
    lum = lum_table(pal)
    idx = sorted(lum, key=lambda k: lum[k])
    lv = np.array([lum[k] for k in idx])
    for (cx, cy), lines in SCENES.items():
        (x0, x1), (y0, y1) = COLW[cx], ROWH[cy]
        blk = a[y0:y1, x0:x1]
        ys, xs = np.nonzero(blk)
        bx, by = xs.min(), ys.min()                     # 원본 글자 덩어리 왼쪽 위
        blk[:] = 0
        img = render_block(lines)
        ih, iw = img.shape[:2]
        assert bx + iw <= x1 - x0, '장면 %s 가로 넘침 %d > %d' % ((cx, cy), bx + iw, x1 - x0)
        assert by + ih <= y1 - y0, '장면 %s 세로 넘침' % ((cx, cy),)
        alpha = img[:, :, 3] > 110
        g = img[:, :, 0].astype(int)
        q = np.array(idx)[np.abs(g[..., None] - lv[None, None, :]).argmin(-1)]
        tgt = blk[by:by + ih, bx:bx + iw]
        tgt[alpha] = q[alpha]
    return d[:518] + a.tobytes()


def preview(orig, new, path):
    ims = []
    for dd in (orig, new):
        w, h, pal, a = parse(dd)
        rgb = np.array([((c & 31) << 3, ((c >> 5) & 31) << 3, ((c >> 10) & 31) << 3) for c in pal], dtype=np.uint8)
        ims.append(Image.fromarray(rgb[a]))
    out = Image.new('RGB', (W, H * 2 + 8), (0, 0, 0))
    out.paste(ims[0], (0, 0)); out.paste(ims[1], (0, H + 8))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    out.save(path)


if __name__ == '__main__':
    sys.path.insert(0, HERE)
    sys.stdout.reconfigure(encoding='utf-8')
    from iso9660 import Iso
    import project
    iso = Iso(project.TRACK1)
    e = [r for r in iso.walk() if r[0] == '/PROLO_00.DG2'][0]
    d = iso.read(e[1], e[2])
    nd = build(d)
    assert len(nd) == len(d)
    p = os.path.join(ROOT, 'my files', '그래픽', '01_오프닝내레이션(위원본_아래한글).png')
    preview(d, nd, p)
    print('저장', p)
