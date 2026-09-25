# -*- coding: utf-8 -*-
r"""실행 파일 UI 문구의 «글자 사이 반각 공백» → 전각 «　».
  가운데 정렬 폭 함수(1_SRPG 0x0602FDA0)는 NUL **또는 반각 공백(0x20)** 에서 재기를 멈춘다
  → «기술을 깨달았다!» 는 «기술을» 폭으로 가운데를 잡아 오른쪽으로 밀리고 잘린다(실기 2026-09-26).
  원문은 전각 공백만 쓴다. 기술 이름 복사 루프도 0x20 에서 멈춘다(이름에 반각 공백 금지).
  대상: ui.tsv 의 한 줄짜리(\n·%b 없음) 문구. 예산·폭에 안 들어가면 MANUAL 번역을 쓴다(없으면 그대로 두고 보고).
  python tools/uispace.py [--write]
"""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import kocheck

FW = '　'
MANUAL = {   # 번호: 새 번역 (전각 공백으로 들어가게 다듬음)
    '78': '사교의관1층', '79': '사교관　지하1층', '80': '사교관　지하2층',
    '99': '무르티브탑　1층', '100': '무르티브탑　2층', '101': '무르티브탑　3층',
    '102': '고대유적지하1층', '103': '고대유적지하2층', '104': '고대유적지하3층',
    '110': '마성1층', '111': '마성2층', '113': '마성3층',
    '120': '시련의미궁1층', '121': '시련의미궁지하1층', '122': '시련의미궁지하2층', '123': '시련의미궁지하3층',
    '142': '　더　못　든다', '367': '몇　개　살까요?', '368': '몇　개　팔까요?', '400': '맡겠습니까?',
    '402': '%c10;10１００００젬을　손에　넣었다%c7;8%b', '406': '대전마다　등록비가　들지만',
    '431': '시련의　미궁에　갈까?', '445': '　일행은　전멸했다‥', '452': '참가　캐릭터　선택',
    '455': 'ＥＸＰ　획득했다!', '491': '기술을　깨쳤다!', '512': 'ＭＰ가　부족해!', '532': '이　기술명은｢',
    '535': '이건　말야｢', '553': '싸움에　져서　돈　절반을　잃었다', '555': '적을　꺾고　무사히　국경통과',
    '563': '의　기술　훔침',
    '6': '본체ＲＡＭ　기록을　모두　지웁니다', '8': '초기화　중.잠시　기다려　주세요.', '10': '본체ＲＡＭ　기록을　모두　지웠습니다',
    '243': '마법에　좀　약함', '247': '전체마법　약함', '249': '활,창　약함', '251': '물　마법　약함',
}


def fits(r, ko):
    if kocheck.nbytes(ko) > int(r[3]):
        return False
    wmax = max(kocheck.px(x) for x in kocheck.LINES.split(r[5]))
    return max(kocheck.px(x) for x in kocheck.LINES.split(ko)) <= wmax


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    p = os.path.join(ROOT, 'work', 'ko', 'ui.tsv')
    L = open(p, encoding='utf-8').read().split('\n')
    auto = man = 0; left = []
    for i, ln in enumerate(L):
        r = ln.split('\t')
        if len(r) < 7 or not r[6]:
            continue
        ko = kocheck.squeeze(r[6])
        if not re.search(r'\S \S', ko) or '\\n' in ko or '%b' in ko:
            continue
        new = re.sub(r'(?<=\S) +(?=\S)', lambda m: FW * len(m.group(0)), ko)
        if fits(r, new):
            r[6] = new; auto += 1
        elif r[0] in MANUAL:
            assert fits(r, MANUAL[r[0]]), ('MANUAL 도 넘침', r[0], MANUAL[r[0]])
            r[6] = MANUAL[r[0]]; man += 1
        else:
            left.append((r[0], r[5], ko)); continue
        L[i] = '\t'.join(r)
    if '--write' in sys.argv:
        open(p, 'w', encoding='utf-8').write('\n'.join(L))
    print('자동 %d · 손질 %d · 그대로 %d%s' % (auto, man, len(left), '' if '--write' in sys.argv else ' (예행)'))
    for x in left:
        print('  그대로', *x)
