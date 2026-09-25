"""한글 글리프를 FNTC 셀(16x12)에 맞춰 만든다.

★픽셀 폰트는 **BDF 직독** — TTF 를 디자인 px 아닌 크기로 렌더하면 획이 탈락한다
  ([[feedback_pixel_font_use_bdf_not_ttf]]).
★조합형 소스에 통글자가 섞여 있을 수 있으니 **커버리지를 세어 본다**
  ([[feedback_johab_font_whole_syllables]]).

셀은 16x12 인데 갈무리11 은 11x11 이라 세로가 1px 남는다. 가로는 여유가 크다.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bdf import Bdf

BDF_CANDIDATES = [
    r'C:\claude\project\conker-kr-patch\my folder\Galmuri-v2.40.3\Galmuri11.bdf',
    r'C:\claude\project\conker-kr-patch\my folder\Galmuri-v2.40.3\Galmuri11-Bold.bdf',
    r'C:\claude\project\conker-kr-patch\my folder\Galmuri-v2.40.3\Galmuri11-Condensed.bdf',
]
_cache = {}


def font(path=None):
    p = path or BDF_CANDIDATES[0]
    if p not in _cache:
        if not os.path.exists(p):
            raise RuntimeError('BDF 가 없다: %s' % p)
        _cache[p] = Bdf(p)
    return _cache[p]


def glyph(ch, w=16, h=12, path=None, dx=0, dy=0, vis_w=12):
    """FNTC 셀 크기의 그레이(0/255) bytes.

    ★`Bdf.bits()` 는 **[(x, y)] 잉크 좌표 목록**을 준다(행 리스트가 아니다).
      폰트 bbx(18x21) 기준 좌표라, **실제 잉크 범위**를 재서 셀에 맞춘다.
    ★★버퍼는 16폭(2바이트/행)이지만 **화면에 쓰이는 폭은 12px**다.
      원본 글리프도 하위 4비트가 전부 0이다(22,764행 전수 확인).
      그래서 가운데 맞춤은 **vis_w 기준**으로 하고 그 밖으로는 안 그린다.
    """
    f = font(path)
    pts = f.bits(ch)
    if pts is None:
        raise KeyError('BDF 에 %r 가 없다' % ch)
    if not pts:
        return bytes(w * h)
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)
    gw, gh = x1 - x0 + 1, y1 - y0 + 1
    ox = (vis_w - gw) // 2 - x0 + dx
    oy = (h - gh) // 2 - y0 + dy
    out = bytearray(w * h)
    for x, y in pts:
        tx, ty = x + ox, y + oy
        if 0 <= tx < vis_w and 0 <= ty < h:      # ★vis_w 밖으로는 절대 안 그린다
            out[ty * w + tx] = 255
    return bytes(out)


def coverage(text, path=None):
    """[없는 글자] — 인코딩 누락은 빌드 에러로 다뤄야 한다."""
    f = font(path)
    return [c for c in dict.fromkeys(text) if f.bits(c) is None]


if __name__ == '__main__':
    f = font()
    print('BDF:', BDF_CANDIDATES[0])
    print('  FONTBOUNDINGBOX:', f.bbx)
    print('  글리프 %d개' % len(f.glyphs))
    sample = '때가무르익다세계를제패하리라'
    miss = coverage(sample)
    print('  표본 커버리지: 없는 글자 %d개 %s' % (len(miss), miss))
    for ch in '때가무':
        b = glyph(ch)
        print('  %s:' % ch)
        for y in range(12):
            print('     ' + ''.join('#' if b[y * 16 + x] else '.' for x in range(16)))
