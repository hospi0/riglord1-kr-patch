"""`mato` 컨테이너 — 이 게임의 범용 묶음 포맷 (839개 파일).

실측 헤더 (전부 **빅엔디언**. SH-2 가 BE 라서가 아니라 실제 값이 그렇게만 읽힌다)

    0x00  'mato'
    0x04  u32  총 크기 (파일 크기와 일치)
    0x08  u32  N = 블록 수
    0x0C  u32  0
    0x10  u32 * (N+1)   블록 경계. 블록 i = [off[i], off[i+1])

검산 예
    ITEMHELP.MSG N=1  -> 0x10=0x18, 0x14=0x2DD0                    (블록 1개)
    EVE_080.EVE  N=5  -> 0x2C,0x5500,0xE8AC,0x13284,0x1333C,0x13570 (블록 5개)

★블록 안이 또 「BE u32 오프셋 표 + 본문」인 2단 구조인 경우가 있다
  (.MSG 가 그렇다). 그건 소비자마다 다르므로 여기서 단정하지 않는다.
"""
import struct

MAGIC = b'mato'


class MatoError(Exception):
    pass


class Mato:
    def __init__(self, data, name=''):
        self.name = name
        self.data = data
        if data[:4] != MAGIC:
            raise MatoError('매직이 %r' % data[:4])
        self.total, self.n, self.zero = struct.unpack_from('>3I', data, 4)
        if self.zero != 0:
            raise MatoError('0x0C 가 0 이 아니다: %08X' % self.zero)
        if not (0 < self.n <= 4096):
            raise MatoError('블록 수 %d' % self.n)
        need = 0x10 + (self.n + 1) * 4
        if need > len(data):
            raise MatoError('경계표가 파일을 넘는다 (%d > %d)' % (need, len(data)))
        self.off = list(struct.unpack_from('>%dI' % (self.n + 1), data, 0x10))

    # --- 검증 ---
    def check(self):
        """[문제 문자열]. 비어 있으면 통과."""
        bad = []
        if self.total != len(self.data):
            bad.append('총크기 %d != 파일 %d' % (self.total, len(self.data)))
        hdr_end = 0x10 + (self.n + 1) * 4
        if self.off[0] < hdr_end:
            bad.append('첫 블록 0x%X 가 헤더 끝 0x%X 보다 앞' % (self.off[0], hdr_end))
        if self.off[0] - hdr_end >= 16:
            bad.append('헤더~첫블록 갭 %d B' % (self.off[0] - hdr_end))
        for i in range(self.n):
            if self.off[i] > self.off[i + 1]:
                bad.append('경계 역전 #%d: 0x%X > 0x%X' % (i, self.off[i], self.off[i + 1]))
        if self.off[-1] > len(self.data):
            bad.append('마지막 경계 0x%X > 파일 %d' % (self.off[-1], len(self.data)))
        return bad

    # --- 접근 ---
    def block(self, i):
        return self.data[self.off[i]:self.off[i + 1]]

    def blocks(self):
        return [self.block(i) for i in range(self.n)]

    def sizes(self):
        return [self.off[i + 1] - self.off[i] for i in range(self.n)]

    # --- 재조립 ---
    def rebuild(self, blocks, align=4):
        """블록을 갈아끼워 새 mato 를 만든다. 경계표를 다시 쓴다."""
        if len(blocks) != self.n:
            raise MatoError('블록 수가 다르다 %d != %d' % (len(blocks), self.n))
        hdr_end = 0x10 + (self.n + 1) * 4
        gap = self.off[0] - hdr_end                 # 원본 갭(정렬 패딩)을 보존한다
        out = bytearray(self.data[:self.off[0]])
        offs = [self.off[0]]
        for b in blocks:
            out += b
            while len(out) % align:
                out.append(0)
            offs.append(len(out))
        new = bytearray(out)
        struct.pack_into('>3I', new, 4, len(new), self.n, 0)
        struct.pack_into('>%dI' % (self.n + 1), new, 0x10, *offs)
        new[:4] = MAGIC
        _ = gap
        return bytes(new)


if __name__ == '__main__':
    import os
    import sys
    import collections
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from iso9660 import Iso
    from project import TRACK1
    from peek import load_list

    rows = [r for r in load_list() if not r[3] and not r[0].endswith('/')]
    iso = Iso(TRACK1)
    ok = 0
    fails = []
    stats = collections.Counter()
    nblocks = collections.Counter()
    for path, lba, size, oob in rows:
        head = iso.read(lba, 4)
        if head != MAGIC:
            continue
        d = iso.read(lba, size)
        ext = os.path.splitext(path)[1].upper()
        try:
            m = Mato(d, path)
            bad = m.check()
        except MatoError as e:
            fails.append((path, str(e)))
            stats[ext + ':실패'] += 1
            continue
        if bad:
            fails.append((path, '; '.join(bad)))
            stats[ext + ':경고'] += 1
        else:
            ok += 1
            stats[ext] += 1
        nblocks[m.n] += 1
    print('mato 파일 %d개 중 통과 %d / 문제 %d' % (ok + len(fails), ok, len(fails)))
    print('\n-- 확장자별 --')
    for k, c in stats.most_common():
        print('   %-14s %d' % (k, c))
    print('\n-- 블록 수 분포 --')
    for k, c in nblocks.most_common(12):
        print('   N=%-5d %d개' % (k, c))
    if fails:
        print('\n-- 문제 %d건 (앞 15) --' % len(fails))
        for p, e in fails[:15]:
            print('   %-30s %s' % (p, e))
