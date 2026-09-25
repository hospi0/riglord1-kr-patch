# -*- coding: utf-8 -*-
r"""리그로드 사가 1 한글 빌드 — 도너 코드 배정 + 글꼴 세 벌 + 제자리 덮어쓰기 + Track 1 굽기(ECC).

  python tools/build.py                # 예행(디스크 안 씀) — 예산 넘침·원문 불일치 보고
  python tools/build.py --write        # work/rig1_kr_track1.bin 에 굽기
  python tools/build.py --write --install   # + F: 바깥 폴더 Track 1 교체

1) 번역 work/ko/*.tsv (대상 · JP · KO) — BIN(실행 파일 세 개에서 그 문자열 통째) / SKILL(기술표 22바이트 필드) / /파일@오프셋.
2) 한글 음절 → «도너 코드»(세 FNTC 에 모두 있는 SJIS 한자, 리드 0x88‥0x9F, 말뭉치에서 드문 한자부터). 한 글자 = 2바이트.
3) 글꼴 FNTC 세 벌(/INO4INIT.DAT · /TITLE2.MAT · /TITLEMAT.GRF): 머리 +0x14 글리프 시작 · +0x18 개수 · +0x20 코드표(u16 LE).
   ★글리프 = 16×12, 24바이트(행 2바이트 BE), 보이는 폭 12px — 머리말의 «16×16» 은 셀 크기일 뿐(2026-09-25 실측: 、。，．… 가 12행 간격).
4) 예산 = 원문 바이트 수. 남는 자리는 NUL. 파일 크기·mato 블록 경계 불변 → ISO 디렉터리 그대로, 섹터 EDC/ECC 만 재계산.
5) 이름 입력 자판: 1_SRPG/2_SRPGED 의 10칸 줄(あ い う え お　か …) 속 가나·한자 칸을 한글 음절로(부호·영숫자 그대로).
"""
import collections, glob, hashlib, os, re, shutil, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from iso9660 import Iso
from cdrom_ecc import recalc_sector
import project, strindex, krglyph, prolog, datatab

BINS = ('/0_OP.BIN', '/1_SRPG.BIN', '/2_SRPGED.BIN')
FONTS = ('/INO4INIT.DAT', '/TITLE2.MAT', '/TITLEMAT.GRF')
# ★실행 파일은 «UI 문자열 데이터 구간» 안에서만 쓴다 — 한 글자 문구(直·飛 등)가 코드 영역에서도 «2바이트+NUL» 로 우연히 걸린다(2026-09-25: 2_SRPGED 7326·7666·10058·47098)
DATA_RANGES = {'/1_SRPG.BIN': (534000, 574000), '/2_SRPGED.BIN': (529500, 570000)}   # 자료표(기술·아이템·장비·몬스터)
BIN_RANGES = {'/0_OP.BIN': (170000, 175000), '/1_SRPG.BIN': (513500, 534000), '/2_SRPGED.BIN': (509500, 530000)}   # 513612‥ 지명 목록 포함(2026-09-25)
GALMURI11 = 'C:/claude/utils/font/Galmuri-v2.40.3/Galmuri11.bdf'
KEEP_KANJI = set()             # PoC 에서 그대로 보이는 한자(도너로 쓰지 않음) — «(技Lv + up)» 도 번역해서 비움(2026-09-25)
HANGUL = re.compile('[\uac00-\ud7a3]')

CHO = 'ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ'
JUNG = 'ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ'


def syl(c, v, j=0):
    return chr(0xAC00 + (CHO.index(c) * 21 + JUNG.index(v)) * 28 + j)


def keyboard_syllables():
    """이름 자판 한글 칸(한글1 → 한글2 순서로 채움). 하·스·피(사용자 이름) 포함."""
    base = [syl(c, v) for c in 'ㄱㄴㄷㄹㅁㅂㅅㅇㅈㅊㅋㅌㅍㅎ' for v in 'ㅏㅓㅗㅜㅡㅣ']            # 84
    base += [syl(c, v) for c in 'ㄱㄴㄷㄹㅁㅂㅅㅇㅈㅊㅋㅌㅍㅎ' for v in 'ㅐㅔ']                # 28
    base += list('야여요유예와워위의외까따빠싸짜꼬또뽀쏘쪼')                                   # 20
    base += list('한민진준현영정성은인일윤연원용철석상동명종경승훈혁빈선근순숙란린설별솔결')  # 40
    base += list('김박최강조장임신권황안송전홍')                                               # 성씨
    out = list(dict.fromkeys(base))
    # 칸 수(한글1·한글2 가나·한자 칸)는 main 에서 확인
    assert all(c in out for c in '하스피아서')
    return out


def squeeze(s):
    return re.sub(r'([,.!?:;])[ ]+(?=\S)', r'\1', s)


def unesc(s):
    return s.replace('\\n', '\n')


KIND = {'ui': 'BIN', 'skill': 'SKILL', 'data': 'DATA', 'map': 'TEXT', 'msg': 'TEXT'}


def load_trans():
    """두 형식: PoC(대상 · JP · KO) / 추출본 복사(번호 · 종류 · 자리수 · 예산 · 예시위치 · JP · KO).
    같은 (대상, JP) 가 여러 파일에 있으면 «뒤 파일»이 이긴다(00_poc → 본번역 순)."""
    rows = collections.OrderedDict()
    for fn in sorted(glob.glob(os.path.join(ROOT, 'work', 'ko', '*.tsv'))):
        for ln in open(fn, encoding='utf-8'):
            if ln.startswith('#') or not ln.strip():
                continue
            r = ln.rstrip('\n').split('\t')
            if len(r) >= 7 and r[1] in KIND:
                t, jp, ko = KIND[r[1]], r[5], r[6]
            else:
                t, jp, ko = r[:3]
            if not ko:
                continue
            rows[(t, unesc(jp))] = squeeze(unesc(ko))
    return [(t, jp, ko) for (t, jp), ko in rows.items()]


def read_font(d):
    i = d.index(b'FNTC')
    go, n = struct.unpack_from('<II', d, i + 0x14)
    codes = [struct.unpack_from('<H', d, i + 0x20 + 2 * k)[0] for k in range(n)]
    return i, go, codes


def pack_glyph(gray, w=16, h=12):
    out = bytearray()
    for y in range(h):
        v = 0
        for x in range(w):
            if gray[y * w + x]:
                v |= 0x8000 >> x
        out += struct.pack('>H', v)
    return bytes(out)


def main():
    write = '--write' in sys.argv
    install = '--install' in sys.argv
    iso = Iso(project.TRACK1)
    ent = {r[0]: r for r in iso.walk()}
    data = {}

    def file(p):
        if p not in data:
            r = ent[p]
            data[p] = bytearray(iso.read(r[1], r[2]))
        return data[p]

    trans = load_trans()
    kbd = keyboard_syllables()
    # --- 도너 배정 -------------------------------------------------------------
    fonts = {p: read_font(file(p)) for p in FONTS}
    common = set.intersection(*[set(f[2]) for f in fonts.values()])
    freq = collections.Counter()
    for ln in open(os.path.join(ROOT, 'work', 'strings.tsv'), encoding='utf-8'):
        freq.update(ln.split('\t', 4)[-1])
    cand = [c for c in common if 0x88 <= c >> 8 <= 0x9F]
    cand = [c for c in cand if bytes([c >> 8, c & 255]).decode('cp932', 'replace') not in KEEP_KANJI]
    cand.sort(key=lambda c: (freq[bytes([c >> 8, c & 255]).decode('cp932', 'replace')], c))
    sylls = list(dict.fromkeys(ch for _, _, ko in trans for ch in ko if HANGUL.match(ch)) | dict.fromkeys(kbd).keys()) if False else \
        list(dict.fromkeys([ch for _, _, ko in trans for ch in ko if HANGUL.match(ch)] + kbd))
    assert len(sylls) <= len(cand), ('도너 부족', len(sylls), len(cand))
    donor = {s: cand[k] for k, s in enumerate(sylls)}
    print('한글 음절 %d → 도너 %d개 중 사용(공통 코드 %d)' % (len(sylls), len(cand), len(common)))

    def enc(s):
        out = bytearray()
        for ch in s:
            if ch in donor:
                c = donor[ch]; out += bytes([c >> 8, c & 255])
            elif ord(ch) < 0x80:
                out += ch.encode('ascii')
            else:
                out += ch.encode('cp932')
        return bytes(out)

    # --- 글꼴 세 벌 -------------------------------------------------------------
    for p, (i, go, codes) in fonts.items():
        d = file(p)
        for s, c in donor.items():
            k = codes.index(c)
            g = pack_glyph(krglyph.glyph(s, path=GALMURI11))
            d[i + go + 24 * k:i + go + 24 * k + 24] = g
    # --- 문자열 ----------------------------------------------------------------
    idx = strindex.load()
    # 자료표 자리: (파일, 원문) → [(오프셋, 쓸 수 있는 바이트)] — 원본 바이트로 계산(쓰기 전에)
    data_slots = collections.defaultdict(list)
    for p, (lo, hi) in DATA_RANGES.items():
        d0 = bytes(file(p))
        L = datatab.names(d0, lo, hi)
        W = datatab.widths(d0, L)
        for o, b, s in L:
            data_slots[(p, s)].append((o, W[o]))
    err, n_w = [], collections.Counter()

    def put(p, off, n, jp_b, ko):
        d = file(p)
        if bytes(d[off:off + n]) != jp_b:
            err.append('%s@%d 원문 불일치' % (p, off)); return
        b = enc(ko)
        if len(b) > n:
            err.append('%s@%d 예산 %dB < %dB: %s' % (p, off, n, len(b), ko)); return
        d[off:off + n] = b + bytes(n - len(b))
        n_w[p] += 1

    for t, jp, ko in trans:
        jb = jp.encode('cp932')
        if t == 'BIN':
            hits = [r for r in idx if r[0] in BINS and strindex_unesc(r[4]) == jp
                    and BIN_RANGES[r[0]][0] <= r[2] <= BIN_RANGES[r[0]][1]]
            if not hits:                  # 색인에 없는 것(반각 가타카나 ﾊﾟﾜｰ 등) — UI 구간에서 «NUL+문자열+NUL» 직접 찾기
                for p in BINS:
                    lo, hi = BIN_RANGES[p]
                    d = file(p)
                    # ﾊﾟﾜｰ 는 «ﾊﾟﾜｰ:攻撃力+» 처럼 뒤에 ':' 가 붙은 한 문자열의 머리 — 그 4바이트만 제자리.
                    # 앞 바이트는 NUL 또는 정렬 채움 0xFF(517191 실측)
                    for pre in (b'\0', b'\xff'):
                        for tail in (b'\0', b':'):
                            j = d.find(pre + jb + tail, lo - 1, hi + len(jb) + 2)
                            while j >= 0:
                                hits.append((p, 0, j + 1, len(jb), jp))
                                j = d.find(pre + jb + tail, j + 1, hi + len(jb) + 2)
            if not hits:
                err.append('BIN 에 없는 문자열: %s' % jp)
            for p, lba, off, n, s in hits:
                put(p, off, n, jb, ko)
        elif t == 'TEXT':                   # 대사·설명: 실행 파일 밖에서 그 문자열 통째가 나오는 모든 자리
            hits = [r for r in idx if r[0] not in BINS and strindex_unesc(r[4]) == jp]
            if not hits:
                err.append('TEXT 에 없는 문자열: %s' % jp[:40])
            for p, lba, off, n, s in hits:
                put(p, off, n, jb, ko)
        elif t in ('SKILL', 'DATA'):          # 자료표(기술·아이템·장비·몬스터 이름) — 두 실행 파일 모두, 표의 이름 칸 폭 안에서
            found = 0
            for p in BINS[1:]:
                d = file(p)
                for off, width in data_slots.get((p, jp), []):
                    if bytes(d[off:off + len(jb)]) != jb:
                        err.append('DATA %s@%d 원문 불일치' % (p, off)); continue
                    b = enc(ko)
                    if len(b) > width:
                        err.append('DATA %s@%d 칸 %dB < %dB: %s' % (p, off, width, len(b), ko)); continue
                    d[off:off + width] = b + bytes(width - len(b)); found += 1; n_w[p] += 1
            if not found:
                err.append('DATA 못 찾음: %s' % jp)
        else:
            p, off = t.split('@')
            put(p, int(off), len(jb), jb, ko)
    # --- 오프닝 내레이션 그림(PROLO_00.DG2, 크기 불변) -----------------------------
    pd = file('/PROLO_00.DG2')
    pd[:] = prolog.build(bytes(pd))
    n_w['/PROLO_00.DG2'] += 1
    # --- 이름 입력 자판 ---------------------------------------------------------
    it = iter(kbd)
    for p in BINS[1:]:
        d = file(p)
        start = d.find('あ い う え お　か き く け こ'.encode('cp932'))
        assert start > 0, p
        for row in range(24):
            # ★12·24번째 줄(0부터 11·23)은 전환 줄(«カタカナ/ひらがな もどる 終了») — 번역 단계가 이미 한글(=도너 한자 코드)로
            #   바꿔 놓아서 «もどる» 로는 못 알아본다. 위치로 건너뛴다(실기 2026-09-25: 첫 쪽 전환 줄이 «호후2 흐히 개»로 덮임).
            if row in (11, 23):
                continue
            off = start + 32 * row
            e = d.index(b'\0', off)
            s = bytes(d[off:e]).decode('cp932')
            new = ''.join((next(it) if (0x3041 <= ord(c) <= 0x30FF or 0x4E00 <= ord(c) <= 0x9FFF) and c not in 'ー・' else c) for c in s)
            d[off:e] = enc(new)
        it = iter(kbd)                     # 2_SRPGED 도 같은 배열
        n_w[p] += 1
    for e_ in err:
        print('⛔', e_)
    print('쓴 자리', dict(n_w))
    if err:
        raise SystemExit('오류 %d — 빌드 안 함' % len(err))
    snap = os.path.join(ROOT, 'work', 'charmap.tsv')
    with open(snap, 'w', encoding='utf-8') as f:
        for s, c in donor.items():
            f.write('%s\t%04X\t%s\n' % (s, c, bytes([c >> 8, c & 255]).decode('cp932')))
    if not write:
        print('예행 끝(디스크 안 씀)')
        return
    out = os.path.join(ROOT, 'work', 'rig1_kr_track1.bin')
    shutil.copyfile(project.TRACK1, out)
    with open(out, 'r+b') as fh:
        for p, d in data.items():
            lba = ent[p][1]
            orig = iso.read(lba, len(d))
            for s in range(0, len(d), project.DATA_LEN):
                if d[s:s + project.DATA_LEN] != orig[s:s + project.DATA_LEN]:
                    pos = (lba + s // project.DATA_LEN) * project.SECTOR
                    fh.seek(pos)
                    sec = bytearray(fh.read(project.SECTOR))
                    chunk = d[s:s + project.DATA_LEN]
                    sec[project.DATA_OFF:project.DATA_OFF + len(chunk)] = chunk
                    fh.seek(pos)
                    fh.write(recalc_sector(bytes(sec)))
    md5 = hashlib.md5(open(out, 'rb').read()).hexdigest()
    print('완료 %s md5 %s' % (out, md5))
    if install:
        shutil.copyfile(out, project.OUT_TRACK1)
        print('설치 %s' % project.OUT_TRACK1)


def strindex_unesc(s):
    return s.replace('\\t', '\t').replace('\\n', '\n').replace('\\\\', '\\')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
