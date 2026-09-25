# -*- coding: utf-8 -*-
"""BDF 비트맵 폰트 직독.

★TTF 를 «디자인 px 가 아닌 크기»로 렌더하면 획이 통째로 탈락한다. 픽셀 폰트는
  반드시 BDF 를 직접 읽는다(갈무리11 @11px 에서 `종` 의 ㅈ 다리 3행이 사라진 적 있다).
  이름의 숫자는 셀 크기가 아니다 — BDF 헤더의 값을 실측해서 쓴다.
"""


class Bdf:
    def __init__(self, path):
        self.glyphs = {}          # codepoint -> (rows[], bbx)
        self.bbx = None
        cur = None
        bbx = None
        bitmap = None
        with open(path, encoding='latin-1') as f:
            for line in f:
                line = line.rstrip('\n')
                if line.startswith('FONTBOUNDINGBOX'):
                    self.bbx = tuple(int(x) for x in line.split()[1:5])
                elif line.startswith('ENCODING'):
                    cur = int(line.split()[1])
                elif line.startswith('BBX'):
                    bbx = tuple(int(x) for x in line.split()[1:5])
                elif line == 'BITMAP':
                    bitmap = []
                elif line == 'ENDCHAR':
                    if cur is not None and cur >= 0 and bitmap is not None:
                        self.glyphs[cur] = (bitmap, bbx)
                    cur = None
                    bitmap = None
                elif bitmap is not None:
                    bitmap.append(line.strip())

    def bits(self, ch):
        """글자 → [(x, y)] 잉크 픽셀 목록 (BBX 원점 기준, y 는 위에서 0).

        BDF 는 baseline 기준 offset 을 쓰므로 폰트 bbx 로 정규화한다.
        """
        g = self.glyphs.get(ord(ch))
        if not g:
            return None
        rows, (bw, bh, bx, by) = g
        fw, fh, fx, fy = self.bbx
        out = []
        for r, hexrow in enumerate(rows):
            if not hexrow:
                continue
            v = int(hexrow, 16)
            nbits = len(hexrow) * 4
            for c in range(bw):
                if (v >> (nbits - 1 - c)) & 1:
                    # 셀 안 좌표: 왼쪽 여백 (bx-fx), 위쪽 여백 (fh+fy) - (bh+by)
                    out.append((c + bx - fx, r + (fh + fy) - (bh + by)))
        return out
