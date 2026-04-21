import logging
from apscheduler.schedulers.background import BackgroundScheduler
from .models import TradingConfig
from . import service as trading_service

logger = logging.getLogger(__name__)

# 타임프레임별 체크 주기 (초)
INTERVAL_SECONDS = {
    "minutes5": 300,
    "minutes15": 900,
    "minutes60": 3600,
    "minutes240": 14400,
    "days": 3600,   # 일봉은 1시간마다 체크 (당일 신호 감지)
    "weeks": 86400,
    "months": 86400,
}

_scheduler = BackgroundScheduler(timezone="Asia/Seoul")
_active_configs: dict[str, TradingConfig] = {}


def start_trading(config: TradingConfig):
    """마켓에 대한 자동매매 스케줄 시작"""
    job_id = f"trading_{config.market}"
    interval = INTERVAL_SECONDS.get(config.timeframe, 3600)

    _active_configs[config.market] = config

    _scheduler.add_job(
        func=_run_job,
        trigger="interval",
        seconds=interval,
        args=[config.market],
        id=job_id,
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    if not _scheduler.running:
        _scheduler.start()

    logger.info(f"자동매매 시작: {config.market} / {config.strategy} / {interval}초 간격")


def stop_trading(market: str):
    """마켓 자동매매 중지"""
    job_id = f"trading_{market}"
    if _scheduler.get_job(job_id):
        _scheduler.remove_job(job_id)
    _active_configs.pop(market, None)
    logger.info(f"자동매매 중지: {market}")


def get_status() -> dict:
    """스케줄러 상태 조회"""
    jobs = []
    if _scheduler.running:
        for job in _scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
            })
    return {
        "running": _scheduler.running,
        "jobs": jobs,
        "active_markets": list(_active_configs.keys()),
    }


def get_active_config(market: str) -> TradingConfig | None:
    return _active_configs.get(market)


def _run_job(market: str):
    config = _active_configs.get(market)
    if not config:
        return
    try:
        result = trading_service.check_and_execute(config)
        logger.info(f"[{market}] 체크 결과: {result.get('status')} - {result.get('reason', result.get('exit_reason', ''))}")
    except Exception as e:
        logger.error(f"[{market}] 자동매매 오류: {e}", exc_info=True)
