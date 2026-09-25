# -*- coding: utf-8 -*-
"""공통 경로·상수 — 리그로드 사가 1. ★원본 자산은 저장소에 두지 않는다.

★★경로 규칙(리그로드 사가 2 와 같은 중첩 구조)
    무수정 원본 = F: **안쪽 중첩 폴더**(읽기 전용)  — 같은 파일이 C:\\claude\\roms\\ss 에도 있다
    패치 출력   = F: **바깥 폴더**(Track 2‥7 과 .cue 가 있는 곳)
"""
import os

_F = r'F:\hospi\roms\ss roms\Riglordsaga (Japan) (Made in Japan) (4M)'
_NAME = 'Riglordsaga (Japan) (Made in Japan) (4M)'

ORIG_DIR = r'C:\claude\roms\ss\%s' % _NAME
TRACK1 = os.path.join(ORIG_DIR, '%s (Track 1).bin' % _NAME)
ORIG_MD5 = '4270c76f0492f0fc1cfec2254724f597'

OUT_DIR = _F
OUT_TRACK1 = os.path.join(OUT_DIR, '%s (Track 1).bin' % _NAME)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.path.join(REPO, 'work')

SECTOR = 2352
DATA_OFF = 16
DATA_LEN = 2048
