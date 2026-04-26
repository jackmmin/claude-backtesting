// 실시간 매매 탭 진입점 — 상태 변수 및 초기화
// 렌더링: trading_render.js / API 호출: trading_api.js

let ltActive = false;
let ltStatusTimer = null;
let _lastEventTs = null;  // 마지막 확인한 스케줄러 이벤트 타임스탬프
