"""`FNTC` 폰트 — 읽기·쓰기.

`/RIG2INIT.DAT` 의 mato 블록 1 이 이것이다. 실측 사양

    0x00 u32 BE  블록 절대 오프셋 (mato 2단 머리)
    0x04 u32 BE  크기
    0x08 'FNTC'
    0x0C u32 LE  크기            ← ★블록 머리는 BE 인데 FNTC 내부는 **LE** 다
    0x20 u32 LE  글자 수 (1897)
    0x24 u8 폭(16) / u8 높이(12) / u8 bpp(1) / u8 0
    0x28 u16 LE * N   cp932 코드 표 (오름차순)
    0xEFA + 14        ★글리프 시작. **코드표 뒤에 14바이트 패딩이 있다**
    이후            N * 24 B  1bpp 글리프 (한 행 2바이트, 12행)

★★셀은 24바이트 = 16비트 × 12행이지만 **화면에 쓰이는 폭은 12px**(상위 12비트).
  나머지 4비트는 항상 0이다.

★★★시작 오프셋을 `0x28 + N*2`(=0xEFA)로 잡으면 **14바이트 어긋난다.**
  세션1에서 여기 한참 막혔다 — 형식 해석은 맞았는데 시작점만 틀려서
  「一」이 「目」처럼 보이고 화면의 한글이 세로로 겹쳐 나왔다.
  확정 근거: 무수정 원본 스크린샷의 「機」를 12×12로 리샘플한 결과가
  0xF08 기준 렌더와 **행 단위로 정확히 일치**했고, 一/二/三 가로선 개수와
  「日」 모양도 전부 맞는다.

코드 표가 **직접 매핑**이라 아무 cp932 코드나 원하는 글리프에 붙일 수 있다.
"""
import struct

MAGIC = b'FNTC'


class Fntc:
    def __init__(self, block):
        self.raw = bytes(block)
        if self.raw[8:12] != MAGIC:
            raise ValueError('FNTC 매직이 아니다: %r' % self.raw[8:12])
        self.n = struct.unpack_from('<I', self.raw, 0x20)[0]
        self.w, self.h, self.bpp = self.raw[0x24], self.raw[0x25], self.raw[0x26]
        if self.bpp != 1:
            raise ValueError('bpp %d 는 미지원' % self.bpp)
        self.cb = self.w * self.h // 8          # 24
        self.vis_w = 12                          # ★화면에 쓰이는 폭 (나머지 4비트는 항상 0)
        self.tbl_off = 0x28
        self.codes = list(struct.unpack_from('<%dH' % self.n, self.raw, self.tbl_off))
        # ★코드표 뒤 14바이트 패딩. 실측으로 확정했다(모듈 설명 참조).
        self.pad = 14
        self.glyph_off = self.tbl_off + self.n * 2 + self.pad
        end = self.glyph_off + self.n * self.cb
        if end > len(self.raw):
            raise ValueError('글리프 영역이 블록을 넘는다 (%d > %d)' % (end, len(self.raw)))
        self.data = bytearray(self.raw)

    # --- 조회 ---
    def index_of(self, ch):
        """문자 -> 글리프 인덱스. 코드 표는 오름차순이라 이분 탐색."""
        b = ch.encode('cp932')
        code = b[0] << 8 | b[1] if len(b) == 2 else b[0]
        lo, hi = 0, self.n - 1
        while lo <= hi:
            mid = (lo + hi) // 2
            if self.codes[mid] == code:
                return mid
            if self.codes[mid] < code:
                lo = mid + 1
            else:
                hi = mid - 1
        return None

    def char_of(self, i):
        c = self.codes[i]
        try:
            return bytes([c >> 8, c & 0xFF]).decode('cp932')
        except Exception:
            return None

    def glyph(self, i):
        o = self.glyph_off + i * self.cb
        return bytes(self.data[o:o + self.cb])

    def bitmap(self, i):
        """폭*높이 그레이(0/255)."""
        g = self.glyph(i)
        bpr = self.w // 8
        out = bytearray(self.w * self.h)
        for y in range(self.h):
            for xb in range(bpr):
                v = g[y * bpr + xb]
                for bit in range(8):
                    if v & (0x80 >> bit):
                        out[y * self.w + xb * 8 + bit] = 255
        return bytes(out)

    # --- 쓰기 ---
    def set_glyph(self, i, gray):
        """gray = 폭*높이 (0 이 아니면 켬). 1bpp 로 눌러 넣는다."""
        assert len(gray) == self.w * self.h, '글리프 크기 %d' % len(gray)
        bpr = self.w // 8
        o = self.glyph_off + i * self.cb
        for y in range(self.h):
            for xb in range(bpr):
                v = 0
                for bit in range(8):
                    if gray[y * self.w + xb * 8 + bit]:
                        v |= 0x80 >> bit
                self.data[o + y * bpr + xb] = v

    def to_bytes(self):
        out = bytes(self.data)
        assert len(out) == len(self.raw), '크기가 바뀌었다'
        return out


if __name__ == '__main__':
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from iso9660 import Iso
    from mato import Mato
    from project import TRACK1
    from peek import load_list
    rows = {r[0]: r for r in load_list()}
    p, lba, size, oob = rows['/RIG2INIT.DAT']
    d = Iso(TRACK1).read(lba, size)
    f = Fntc(Mato(d, p).block(1))
    print('글자 %d / 셀 %dx%d / %dbpp / 글리프시작 0x%X' % (f.n, f.w, f.h, f.bpp, f.glyph_off))
    print('앞 30자:', ''.join(f.char_of(i) or '?' for i in range(30)))
    for ch in '機熟今我計画実行世界覇':
        i = f.index_of(ch)
        print('   %s -> 인덱스 %s' % (ch, i))
    assert f.to_bytes() == f.raw, '무변경 왕복 실패'
    print('무변경 왕복 OK')
