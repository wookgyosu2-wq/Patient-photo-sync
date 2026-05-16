# Patient Photo Sync

AutoHotkey로 작성되어 있던 환자 사진/영상 PowerPoint 전송 자동화를 Python으로 옮긴 버전입니다. 기존 기능 흐름은 유지하면서 `OCR.ahk` 의존성을 Python OCR 모듈로 대체했습니다.

## 주요 기능

- 항상 위에 표시되는 Tkinter GUI
- Panorama, CBCT, PNS CT, Neck CT 모드 선택
- EMR 사진 넣기 옵션(진료 단계와 촬영일 입력)
- 술 중 구내/구외, 술 후 종물 특수 모드
- F1~F12 및 백틱(`) 단축키 처리
- OCR로 날짜 또는 파일명을 인식한 뒤 캡션 생성
- 클립보드의 이미지를 활성 PowerPoint 슬라이드에 붙여넣고 크기/위치 조정
- 바이옵시 처방코드 자동 입력

## 설치

Windows에서 Python 3.11 이상을 권장합니다.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

OCR은 기본적으로 `pytesseract`를 사용합니다. Tesseract 본체와 Korean trained data(`kor`)를 설치해야 한국어 OCR이 동작합니다. Tesseract 실행 파일이 PATH에 없다면 `TESSERACT_CMD` 환경 변수에 실행 파일 경로를 지정하세요.

```powershell
$env:TESSERACT_CMD = "C:\Program Files\Tesseract-OCR\tesseract.exe"
```

## 실행

```powershell
python main.py
```

## 사용 방법

1. GUI에서 원하는 모드를 선택합니다.
2. X-ray 계열 모드는 날짜 텍스트 위에 마우스를 올리고 F1을 누릅니다.
3. EMR 모드는 옵션 창에서 진료 단계와 날짜를 정한 뒤 사진/파일명 영역 위에서 F1 또는 백틱을 누릅니다.
4. 특수 모드는 촬영 날짜를 입력한 뒤 사진 위에서 F1~F12 또는 백틱을 누릅니다.
5. PowerPoint가 열려 있으면 현재 슬라이드 첫 번째 도형에 캡션을 넣고 이미지를 붙여넣은 뒤 다음 슬라이드를 추가합니다.
6. 바이옵시 확인 모드는 대상 입력창에 커서를 둔 뒤 F1을 누르면 처방코드를 순서대로 입력합니다.

## 코드 구조

- `main.py`: 실행 진입점
- `patient_photo_sync/app.py`: GUI, 단축키, 기존 AutoHotkey 워크플로우 포팅
- `patient_photo_sync/ocr_engine.py`: Python OCR 캡처/인식 계층
- `patient_photo_sync/input_automation.py`: 마우스, 키보드, 클립보드 자동화
- `patient_photo_sync/powerpoint.py`: PowerPoint COM 자동화
