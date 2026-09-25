# -*- coding: utf-8 -*-
r"""배포 묶음 — dist/Riglordsaga_KR_<VER>/ (xdelta · xdelta.exe · readme.txt · 패치적용.bat, 한국어 파일은 CP949)
  python tools/make_dist.py      (먼저 python tools/build.py --write)
"""
import hashlib, os, shutil, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import project

VER = 'v0.9'
XDELTA = r'C:\claude\utils\xdelta.exe'
BIN = os.path.basename(project.TRACK1)
ROM = BIN.replace(' (Track 1).bin', '')


def md5(p):
    h = hashlib.md5()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest().upper()


README = '''7개의 트랙으로 이루어진 @ROM@ 의
트랙 1번에 패치하시면 됩니다.

원본md5 : @SRC@
패치md5 : @DST@

입니다.


리그로드 사가 (새턴 일본판) 한글 패치 @VER@
==========================================

[ 적용 방법 ]

1. 이 묶음을 원본 「@BIN@」 과 같은 폴더에 풉니다.
2. 「패치적용.bat」 을 실행합니다. 원본 MD5 를 먼저 확인하고, 끝난 뒤 결과 MD5 까지 검사합니다.
   원본은 「.bak」 으로 남겨 둡니다.
3. .cue 와 다른 트랙(2‥7번, 음악)은 그대로 씁니다. 파일 크기도 바뀌지 않습니다.
   (Delta Patcher 같은 xdelta3 도구로 트랙 1번에 직접 적용해도 됩니다.)


[ 바뀌는 것 ]

■ 본편 대사 전부, 도움말·아이템·기술 설명
■ 메뉴·전투·상태 화면 등 시스템 문구, 인물 소개, 지명
■ 기술·아이템·장비·몬스터 이름
■ 오프닝 내레이션 그림, 엔딩 제작진 직함
■ 이름 입력 자판(한글)


[ 알려진 사항 ]

■ 세이브 파일 설명(본체 저장 데이터 관리 화면)은 일본어 그대로입니다.
■ 이전 테스트 빌드에서 만든 세이브스테이트는 글자가 깨질 수 있습니다(게임 안 세이브는 괜찮습니다).
'''

BAT = r'''@echo off
setlocal
set NAME=@BIN@
set PATCH=@PATCH@
set SRCMD5=@SRC@
set DSTMD5=@DST@

echo.
echo  ==============================================
echo    Riglordsaga ^(Saturn JP^) Korean Patch @VER@
echo  ==============================================
echo.

if not exist "%NAME%" (
  echo  [!] "%NAME%" 파일이 이 폴더에 없습니다.
  echo      원본 트랙 1번 .bin 과 같은 폴더에 두고 실행하세요.
  goto END
)
if not exist "%~dp0xdelta.exe" (
  echo  [!] xdelta.exe 가 없습니다. 패치 묶음을 그대로 풀고 실행하세요.
  goto END
)

echo  [1/3] 원본 검사 중...
set HASH=
for /f "skip=1 tokens=* delims=" %%H in ('certutil -hashfile "%NAME%" MD5') do (
  if not defined HASH set HASH=%%H
)
set HASH=%HASH: =%

if /I "%HASH%"=="%DSTMD5%" (
  echo.
  echo  [!] 이미 이 버전의 한글 패치가 적용된 파일입니다.
  goto END
)
if /I not "%HASH%"=="%SRCMD5%" (
  echo.
  echo  [!] 원본 MD5 가 다릅니다. 패치하지 않고 중단합니다.
  echo      필요 : %SRCMD5%
  echo      현재 : %HASH%
  goto END
)

echo  [2/3] 패치 적용 중...
"%~dp0xdelta.exe" -d -f -s "%NAME%" "%~dp0%PATCH%" "%NAME%.kr"
if errorlevel 1 (
  echo  [!] 패치에 실패했습니다.
  if exist "%NAME%.kr" del "%NAME%.kr"
  goto END
)

echo  [3/3] 결과 검사 중...
set HASH2=
for /f "skip=1 tokens=* delims=" %%H in ('certutil -hashfile "%NAME%.kr" MD5') do (
  if not defined HASH2 set HASH2=%%H
)
set HASH2=%HASH2: =%

if /I not "%HASH2%"=="%DSTMD5%" (
  echo  [!] 결과 MD5 가 다릅니다. 원본은 그대로 두고 중단합니다.
  del "%NAME%.kr"
  goto END
)

move /y "%NAME%" "%NAME%.bak" >nul
move /y "%NAME%.kr" "%NAME%" >nul
echo.
echo  [OK] 한글 패치 완료. 원본은 "%NAME%.bak" 으로 남겨 두었습니다.

:END
echo.
pause
'''

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    src, dst = project.TRACK1, os.path.join(ROOT, 'work', 'rig1_kr_track1.bin')
    smd5, dmd5 = md5(src), md5(dst)
    out = os.path.join(ROOT, 'dist', 'Riglordsaga_KR_%s' % VER)
    os.makedirs(out, exist_ok=True)
    patch = 'Riglordsaga_KR_%s.xdelta' % VER
    pp = os.path.join(out, patch)
    if os.path.exists(pp):
        os.remove(pp)
    subprocess.run([XDELTA, '-e', '-9', '-s', src, dst, pp], check=True)
    shutil.copyfile(XDELTA, os.path.join(out, 'xdelta.exe'))
    rep = lambda s: s.replace('@ROM@', ROM).replace('@BIN@', BIN).replace('@PATCH@', patch) \
        .replace('@SRC@', smd5).replace('@DST@', dmd5).replace('@VER@', VER)
    open(os.path.join(out, 'readme.txt'), 'wb').write(rep(README).replace('\n', '\r\n').encode('cp949'))
    open(os.path.join(out, '패치적용.bat'), 'wb').write(rep(BAT).replace('\n', '\r\n').encode('cp949'))
    # 검증: 원본에 xdelta 를 적용해 결과 md5 확인
    chk = os.path.join(ROOT, 'work', '_distcheck.bin')
    subprocess.run([XDELTA, '-d', '-f', '-s', src, pp, chk], check=True)
    ok = md5(chk) == dmd5
    os.remove(chk)
    print('배포', out, '· 원본', smd5, '· 패치본', dmd5, '· xdelta', md5(pp), '· 적용 검증', 'OK' if ok else '⛔불일치')
