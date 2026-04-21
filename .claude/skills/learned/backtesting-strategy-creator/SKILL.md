---
name: backtesting-strategy-creator
description: >
  Creates new backtesting strategies for the claude-coin project by following the exact
  structure, naming conventions, and code style of existing strategies (K_VOLATILITY_BREAKOUT,
  RSI_OVERSOLD_BOUNCE, MA_GOLDEN_CROSS, BOLLINGER_BOUNCE). Use this skill whenever the user
  wants to add a new trading strategy to the backtesting system — whether they say "새 전략
  추가", "전략 만들어줘", "백테스팅 전략 생성", or describe any new entry/exit logic to implement.
  Also trigger when the user asks to implement indicators like MACD, Stochastic, ATR, CCI,
  Williams %R, or any pattern-based strategy into the backtest framework.
---

# Backtesting Strategy Creator

새로운 백테스팅 전략을 기존 전략의 구조와 스타일에 맞게 생성한다.

## Project Layout

```
features/backtesting/
├── service.py     ← Python 핵심 로직 (전략 함수 + run_backtest 디스패처)
├── routes.py      ← Flask API 라우트 (파라미터 파싱 → service 호출)
└── index.js       ← JS 병렬 구현 (클라이언트 사이드)
templates/
└── index.html     ← UI 파라미터 패널 + 전략 설명 표시
```

## Step 1: 전략 설계 확인

사용자에게 다음을 확인한다:
1. **전략 이름** (영문 대문자, 예: `MACD_CROSSOVER`) + 한글명 (예: `MACD 크로스오버`)
2. **전략 약어** (파라미터 접두사, 2-4자, 예: `macd`) — 모든 파라미터 앞에 붙는다
3. **진입 조건** — 어떤 조건에서 매수?
4. **청산 조건** — TP/SL 외 지표 기반 청산이 있는지?
5. **필터 조건** — MA 추세 필터, 볼륨 필터 포함 여부?
6. **핵심 파라미터** — 어떤 값을 사용자가 조정할 수 있어야 하나?

---

## Step 2: service.py 수정

### 2-1. run_backtest() 함수 시그니처에 파라미터 추가

기존 파라미터 목록 마지막에 새 전략 파라미터 블록을 추가한다:

```python
def run_backtest(
    # ... 기존 파라미터들 ...
    bb_max_hold_bars=0,
    # ── 새 전략 파라미터 ──
    <prefix>_param1=<default>,
    <prefix>_param2=<default>,
    <prefix>_use_tp=True, <prefix>_tp=0.05,
    <prefix>_use_sl=False, <prefix>_sl=-0.03,
    <prefix>_volume_filter=False, <prefix>_volume_mult=1.5,
    <prefix>_max_hold_bars=0,
    interval="days", count=200, initial_capital=1000000,
):
```

### 2-2. run_backtest() 디스패처에 분기 추가

```python
    if strategy == "<STRATEGY_NAME>":
        return _<strategy_func>_backtest(
            data,
            param1=<prefix>_param1,
            param2=<prefix>_param2,
            use_tp=<prefix>_use_tp, tp=<prefix>_tp,
            use_sl=<prefix>_use_sl, sl=<prefix>_sl,
            volume_filter=<prefix>_volume_filter,
            volume_mult=<prefix>_volume_mult,
            max_hold_bars=<prefix>_max_hold_bars,
            initial_capital=initial_capital,
        )
    return {"error": f"알 수 없는 전략: {strategy}"}  # 이 줄은 항상 마지막에
```

### 2-3. 전략 함수 구현

주석 구분선 포함 아래 패턴을 따른다:

```python
# ── <한글 전략명> ──────────────────────────────────────────────────────────────

def _<prefix>_backtest(data, param1=<default>, param2=<default>,
                        use_tp=True, tp=0.05, use_sl=False, sl=-0.03,
                        volume_filter=False, volume_mult=1.5,
                        max_hold_bars=0, initial_capital=1000000):
    trades = []
    in_trade = False
    entry_price = None      # 수수료 포함 매수가
    entry_date = None       # 진입일 (trades 기록용)
    entry_datetime = None   # 진입 캔들 datetime
    hold_bars = 0
    open_trade = None

    lookback = max(param1, param2, 20) + 1  # 지표 계산에 필요한 최소 캔들 수

    for i in range(lookback, len(data)):
        curr = data[i]

        # ── 지표 계산 ──
        # 예: closes = [c["trade_price"] for c in data[:i+1]]
        # indicator_val = _sma(closes, param1)

        # ── 볼륨 필터 (공통 패턴) ──
        if volume_filter and not in_trade:
            vol_window = data[max(0, i - 20):i]
            vols = [c.get("candle_acc_trade_volume", 0) for c in vol_window]
            avg_vol = sum(vols) / len(vol_window) if vol_window else 0
            curr_vol = curr.get("candle_acc_trade_volume", 0)
            if avg_vol > 0 and curr_vol < avg_vol * volume_mult:
                continue

        if not in_trade:
            # ── 진입 조건 ──
            triggered = False  # 전략별 진입 조건으로 교체
            if triggered and i + 1 < len(data):
                entry_price = data[i + 1]["opening_price"] * (1 + FEE_RATE)
                entry_date = curr["candle_date_time_kst"][:10]
                entry_datetime = data[i + 1]["candle_date_time_kst"]
                in_trade = True
                hold_bars = 0
        else:
            hold_bars += 1
            raw_entry = entry_price / (1 + FEE_RATE)
            tp_price = raw_entry * (1 + tp)
            sl_price = raw_entry * (1 + sl)

            exited_sell = None
            exited_dt = curr["candle_date_time_kst"]

            # ── 청산 우선순위: TP > SL > 지표청산 > 최대보유 ──
            if use_tp and curr["high_price"] >= tp_price:
                exited_sell = tp_price
            elif use_sl and curr["low_price"] <= sl_price:
                exited_sell = sl_price
            elif <indicator_exit_condition>:
                exited_sell = data[i + 1]["opening_price"] if i + 1 < len(data) else curr["trade_price"]
            elif max_hold_bars > 0 and hold_bars >= max_hold_bars:
                exited_sell = curr["trade_price"]

            if exited_sell is not None:
                sell_price = exited_sell * (1 - FEE_RATE)
                pnl = (sell_price - entry_price) / entry_price
                trades.append({
                    "date": entry_date,
                    "buy_datetime": entry_datetime,
                    "sell_datetime": exited_dt,
                    "buy_price": round(raw_entry),
                    "sell_price": round(exited_sell),
                    "pnl": round(pnl, 6),
                    "win": pnl > 0,
                })
                in_trade = False
                entry_price = entry_date = entry_datetime = None
                hold_bars = 0

    # ── 마지막 캔들에서 진입 신호 발생 시 보유중 표시 ──
    if in_trade and entry_price is not None:
        cp = data[-1]["trade_price"]
        raw_e = entry_price / (1 + FEE_RATE)
        pnl_unrealized = (cp * (1 - FEE_RATE) - entry_price) / entry_price
        open_trade = {
            "date": entry_date,
            "buy_datetime": entry_datetime,
            "sell_datetime": "",
            "buy_price": round(raw_e),
            "sell_price": round(cp),
            "pnl": round(pnl_unrealized, 6),
            "win": pnl_unrealized > 0,
            "open": True,
        }
    elif not in_trade and <last_candle_signal_triggered>:
        # 마지막 캔들에서 신호 발생 (다음 캔들에 진입 예정)
        cp = data[-1]["trade_price"]
        open_trade = {
            "date": data[-1]["candle_date_time_kst"][:10],
            "buy_datetime": data[-1]["candle_date_time_kst"],
            "sell_datetime": "",
            "buy_price": round(cp),
            "sell_price": round(cp),
            "pnl": 0.0,
            "win": False,
            "open": True,
        }

    # ── current_signal: UI 표시용 현재 상태 ──
    current_signal = {
        "date": data[-1]["candle_date_time_kst"][:10],
        "current_price": data[-1]["trade_price"],
        # 전략별 지표값 추가
        "triggered": <last_signal>,
        "in_trade": in_trade,
    }

    return _build_result("<STRATEGY_NAME>", trades, initial_capital, current_signal,
                         open_trade=open_trade, candles=data,
                         # 파라미터 에코 (UI 상태 복원용)
                         <prefix>_param1=param1,
                         <prefix>_use_tp=use_tp, <prefix>_tp=tp,
                         <prefix>_use_sl=use_sl, <prefix>_sl=sl,
                         <prefix>_volume_filter=volume_filter,
                         <prefix>_volume_mult=volume_mult,
                         <prefix>_max_hold_bars=max_hold_bars,
                         total_candles=len(data))
```

### 공통 유틸 함수 (service.py 하단에 이미 존재)

```python
def _sma(values, period):       # 단순이동평균
def _rsi(closes, period=14):    # Wilder's RSI
def _build_result(...):         # 결과 포매터
```

새 지표 계산 함수가 필요하면 `_sma`, `_rsi` 옆에 동일 스타일로 추가한다:
```python
def _ema(values, period):
    # ...

def _macd(closes, fast=12, slow=26, signal=9):
    # ...
```

---

## Step 3: routes.py 수정

`run_backtest` 호출 부분에 새 파라미터를 파싱해 전달한다:

```python
# 새 전략 파라미터 파싱 (기존 파라미터 파싱 블록 아래에 추가)
<prefix>_param1 = request.args.get("<prefix>_param1", <default>, type=<int|float>)
<prefix>_use_tp = request.args.get("<prefix>_use_tp", "true").lower() == "true"
<prefix>_tp = request.args.get("<prefix>_tp", <default>, type=float)
<prefix>_use_sl = request.args.get("<prefix>_use_sl", "false").lower() == "true"
<prefix>_sl = request.args.get("<prefix>_sl", <default>, type=float)
<prefix>_volume_filter = request.args.get("<prefix>_volume_filter", "false").lower() == "true"
<prefix>_volume_mult = request.args.get("<prefix>_volume_mult", 1.5, type=float)
<prefix>_max_hold_bars = request.args.get("<prefix>_max_hold_bars", 0, type=int)

return jsonify(run_backtest(
    # ... 기존 파라미터들 ...
    <prefix>_param1=<prefix>_param1,
    <prefix>_use_tp=<prefix>_use_tp,
    # ... 나머지 ...
))
```

---

## Step 4: index.html 수정

### 4-1. 전략 선택 드롭다운에 추가

```html
<select id="strategySelect" onchange="onStrategyChange()">
    <!-- 기존 옵션들 -->
    <option value="<STRATEGY_NAME>"><한글명></option>
</select>
```

### 4-2. 파라미터 패널 추가

기존 패널(`ctrl-k`, `ctrl-rsi`, `ctrl-ma`, `ctrl-bb`) 옆에 추가한다.
패널 ID 규칙: `ctrl-<prefix>` (2-4자 약어)

```html
<div id="ctrl-<prefix>" class="param-panel" style="display:none">
    <!-- 진입 섹션 -->
    <div class="param-row">
        <span class="param-section-label">진입</span>
        <label><param1 한글명>
            <input type="number" id="<prefix>Param1" value="<default>"
                   min="<min>" max="<max>" step="<step>"
                   oninput="updateStrategyDesc()">
        </label>
    </div>

    <!-- 청산 섹션 -->
    <div class="param-row">
        <span class="param-section-label">청산</span>
        <label><input type="checkbox" id="<prefix>UseTp" checked onchange="updateStrategyDesc()"> TP
            <input type="number" id="<prefix>Tp" value="5" min="0.1" max="50" step="0.1"
                   oninput="updateStrategyDesc()">%
        </label>
        <label><input type="checkbox" id="<prefix>UseSl" onchange="updateStrategyDesc()"> SL
            <input type="number" id="<prefix>Sl" value="3" min="0.1" max="50" step="0.1"
                   oninput="updateStrategyDesc()">%
        </label>
        <!-- 지표 기반 청산이 있으면 추가 -->
        <label><input type="checkbox" id="<prefix>UseIndicatorExit" checked
                       onchange="updateStrategyDesc()"> <청산조건명></label>
        <!-- 최대 보유 기간 -->
        <label>최대보유
            <input type="number" id="<prefix>MaxHoldBars" value="0" min="0" max="200"
                   oninput="updateStrategyDesc()">봉
        </label>
    </div>

    <!-- 필터 섹션 -->
    <div class="param-row">
        <span class="param-section-label">필터</span>
        <label><input type="checkbox" id="<prefix>VolumeFilter" onchange="updateStrategyDesc()"> 거래량
            <input type="number" id="<prefix>VolumeMult" value="1.5" min="0.1" max="10" step="0.1"
                   oninput="updateStrategyDesc()">배
        </label>
    </div>
</div>
```

### 4-3. onStrategyChange() 함수에 패널 토글 추가

```javascript
function onStrategyChange() {
    const s = document.getElementById("strategySelect").value;
    document.querySelectorAll(".param-panel").forEach(p => p.style.display = "none");
    const map = { K_VOLATILITY_BREAKOUT: "k", RSI_OVERSOLD_BOUNCE: "rsi",
                  MA_GOLDEN_CROSS: "ma", BOLLINGER_BOUNCE: "bb",
                  "<STRATEGY_NAME>": "<prefix>" };  // ← 이 줄 추가
    const id = map[s];
    if (id) document.getElementById("ctrl-" + id).style.display = "";
    updateStrategyDesc();
}
```

### 4-4. getParams() 또는 API 호출 함수에 파라미터 수집 추가

```javascript
// 기존 파라미터 수집 블록 아래에 추가
const <prefix>Param1 = document.getElementById("<prefix>Param1").value;
const <prefix>UseTp = document.getElementById("<prefix>UseTp").checked;
const <prefix>Tp = document.getElementById("<prefix>Tp").value / 100;
// ... etc

// URL 파라미터에 추가
params += `&<prefix>_param1=${<prefix>Param1}`;
params += `&<prefix>_use_tp=${<prefix>UseTp}`;
params += `&<prefix>_tp=${<prefix>Tp}`;
```

### 4-5. getStrategyDesc() 또는 updateStrategyDesc() 함수에 설명 추가

```javascript
function getStrategyDesc(strategy) {
    // ... 기존 케이스들 ...
    if (strategy === "<STRATEGY_NAME>") {
        const p1 = document.getElementById("<prefix>Param1").value;
        const tp = document.getElementById("<prefix>UseTp").checked
            ? `+${document.getElementById("<prefix>Tp").value}%` : "";
        const sl = document.getElementById("<prefix>UseSl").checked
            ? `-${document.getElementById("<prefix>Sl").value}%` : "";
        return `진입: <진입조건 설명>(${p1}) | 청산: TP${tp} · SL${sl}`;
    }
}
```

---

## Step 5: 코드 품질 규칙

1. **파라미터 접두사 일관성**: 모든 파라미터는 `<prefix>_` 접두사를 가진다 (HTML id는 camelCase: `<prefix>Param1`)
2. **청산 우선순위**: TP → SL → 지표청산 → 최대보유 순서를 항상 유지한다
3. **수수료 처리**: 매수가 `= price * (1 + FEE_RATE)`, 매도가 `= price * (1 - FEE_RATE)`
4. **마지막 캔들 처리**: 마지막 캔들에서 신호 발생 시 `open_trade` 객체로 보유중 상태 표시
5. **`_build_result()` 에코**: 함수에 전달된 모든 파라미터를 `_build_result()`에 키워드 인수로 다시 넘겨 UI 상태 복원에 사용
6. **지표 함수**: `_sma()`, `_rsi()` 스타일로 단독 함수로 분리 후 `service.py` 하단에 배치
7. **구분선 주석**: 각 전략 함수 시작 전 `# ── <한글명> ──────...` 형식 구분선 추가

---

## 체크리스트

전략 추가 완료 전 확인:
- [ ] `service.py`: `run_backtest()` 파라미터 추가
- [ ] `service.py`: 디스패처 분기 추가 (`return {"error": ...}` 줄 바로 위에)
- [ ] `service.py`: `_<prefix>_backtest()` 함수 구현
- [ ] `routes.py`: 파라미터 파싱 + `run_backtest()` 호출 인수 추가
- [ ] `index.html`: `<select>` 옵션 추가
- [ ] `index.html`: `ctrl-<prefix>` 패널 추가
- [ ] `index.html`: `onStrategyChange()` map 추가
- [ ] `index.html`: 파라미터 수집 코드 추가
- [ ] `index.html`: `getStrategyDesc()` 케이스 추가
