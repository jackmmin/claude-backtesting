### 2026-04-19
* 백테스팅 15분봉 캔들차트 미표시 + 손익그래프 축소 애니메이션 버그 수정
    - 문제1:
        - **캔들차트 미표시**: features/backtesting/index.js의 buildResult가 candles 데이터를 반환하지 않음
        - Python service.py는 candles 포함, JS index.js는 누락.
        - renderBtCandleChart: `if (!d.candles || d.candles.length === 0) return;` 조건에 걸려 항상 조기 종료
    - 문제2:
        - **손익그래프 축소 애니메이션**: renderBacktest() 호출 후 btResult를 display:block으로 표시
        - Chart.js 생성 시 container가 display:none → clientWidth=0 → responsive 모드 무한 리사이즈
* 백테스팅 탭 캔들차트 + 진입/청산 마커 표시
* 분봉 차트 데이터 표시 수정 + 봉 기준 전략 적용
    - 문제1:
        - `setVisibleRange`를 365일 고정으로 설정하는데, 분봉 1000개는 약 3.5일치 데이터밖에 없어 실제 데이터가 화면 밖에 위치
    - 문제2:
        - 전략 신호가 봉 단위가 아닌 날짜 단위로 그룹화되어 분봉에서 정확한 위치에 마커가 표시되지 않음
    - 문제3:
        - UI 텍스트가 "일봉" 기준으로 표기됨
* 기존 K변동성 돌파 전략 외 RSI 과매도 반등, MA 골든크로스, 볼린저밴드 반등 전략도 백테스팅 가능하도록 확장
* 기간 버튼 제거 + 365일 기본 표시 + 전 타임프레임 신호 마커
* 봉 fetch 1000개 고정 + 타임프레임별 표시 범위 제어
* 차트 탭 타임프레임 선택 기능 추가
* 백테스팅 멀티 타임프레임 및 캔들 수 입력 가능하도록 수정
* K변동성 돌파 전략 백테스팅 기능 추가
* 코인 정보 TOP10 제한
* features/ 기반 폴더 구조 재편성
* API 디렉터리 구조 재편성
* 업비트 코인 차트 웹사이트 구현

---