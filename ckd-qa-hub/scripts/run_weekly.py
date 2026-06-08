"""
주간 자동 실행 스크립트
GitHub Actions에서 호출됨
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("run_weekly")


def main():
    logger.info("=== 종근당 QA Intelligence Hub 주간 수집 시작 ===")

    # 1. 데이터 수집
    from app.collectors.fda_warning_letters import collect as collect_wl
    from app.collectors.fda_483 import collect as collect_483
    from app.collectors.mfds_notices import collect as collect_mfds

    wl_count = collect_wl(max_items=50)
    f483_count = collect_483(max_pages=3)
    mfds_count = collect_mfds(max_pages=2)
    logger.info(f"수집 완료 — WL:{wl_count}, 483:{f483_count}, MFDS:{mfds_count}")

    # 2. AI 분석
    from app.ai.gemini_analyzer import run_all_analyses
    analyzed = run_all_analyses()
    logger.info(f"AI 분석 완료: {analyzed}건")

    # 3. 주간 브리핑 생성
    from app.ai.weekly_briefing import generate
    briefing = generate()
    logger.info("주간 브리핑 생성 완료")
    logger.info("=== 주간 작업 완료 ===")


if __name__ == "__main__":
    main()
