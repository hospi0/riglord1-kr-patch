"""Track1 빌드 — 파일 데이터를 제자리 덮어쓰고 MODE1 EDC/ECC 를 다시 계산한다.

★크기를 바꾸지 않는다. 파일 크기가 같으면 ISO 디렉터리·LBA 를 안 건드려도 된다.
★★MODE1 섹터의 EDC(4B)+ECC(276B) 를 다시 안 쓰면 **내용과 무관하게 크래시**한다
  ([[feedback_gdm_build_and_font]]). 이 디스크가 표준 ECC 를 쓴다는 건 실측했다
  (405섹터 전수 일치).

읽기 = F드라이브 **안쪽 중첩** 무수정본, 쓰기 = **바깥** 폴더.
"""
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdrom_ecc import recalc_sector
from project import TRACK1, OUT_TRACK1, OUT_DIR, SECTOR, DATA_OFF, DATA_LEN


def fresh_copy(dst=None):
    """무수정 원본을 출력 위치로 복사한다(빌드 시작점)."""
    dst = dst or OUT_TRACK1
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copyfile(TRACK1, dst)
    return dst


def write_file(fh, lba, data):
    """LBA 부터 data 를 논리적으로 쓰고, 건드린 섹터의 EDC/ECC 를 갱신한다."""
    n = (len(data) + DATA_LEN - 1) // DATA_LEN
    for i in range(n):
        chunk = data[i * DATA_LEN:(i + 1) * DATA_LEN]
        pos = (lba + i) * SECTOR
        fh.seek(pos)
        sec = bytearray(fh.read(SECTOR))
        if len(sec) < SECTOR:
            raise IOError('섹터 %d 를 못 읽었다' % (lba + i))
        sec[DATA_OFF:DATA_OFF + len(chunk)] = chunk
        sec = recalc_sector(bytes(sec))
        fh.seek(pos)
        fh.write(sec)
    return n


def verify_roundtrip(sample_lbas):
    """★무변경 왕복 — 원본 섹터를 다시 계산해도 원본과 같아야 한다."""
    bad = []
    with open(TRACK1, 'rb') as f:
        for lba in sample_lbas:
            f.seek(lba * SECTOR)
            s = f.read(SECTOR)
            if len(s) == SECTOR and s[15] == 1 and recalc_sector(s) != s:
                bad.append(lba)
    return bad


if __name__ == '__main__':
    from peek import load_list
    rows = [r for r in load_list() if not r[3] and not r[0].endswith('/')]
    bad = verify_roundtrip([r[1] for r in rows[:300]])
    print('무변경 왕복(ECC 재계산 == 원본): 불일치 %d' % len(bad))
    print('원본 :', TRACK1)
    print('출력 :', OUT_TRACK1)
