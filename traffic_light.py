#!/usr/bin/env python3
"""
사거리 신호등 시스템 - Python CLI 시뮬레이터

사용법:
    python traffic_light.py              # 기본 실행
    python traffic_light.py --speed 2   # 2배속 실행
    python traffic_light.py --cycles 3  # 3사이클 후 종료
    python traffic_light.py --ns 45 --ew 30  # 시간 직접 지정
"""

import time
import sys
import argparse
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict


# ─── 신호 색상 ────────────────────────────────────────────────
class Signal(Enum):
    RED    = "red"
    YELLOW = "yellow"
    GREEN  = "green"


# ─── 단계 ────────────────────────────────────────────────────
class Phase(Enum):
    NS_GREEN  = "NS_GREEN"
    NS_YELLOW = "NS_YELLOW"
    EW_GREEN  = "EW_GREEN"
    EW_YELLOW = "EW_YELLOW"


# ─── ANSI 색상 코드 ───────────────────────────────────────────
class Color:
    RED    = "\033[91m"
    YELLOW = "\033[93m"
    GREEN  = "\033[92m"
    BLUE   = "\033[94m"
    CYAN   = "\033[96m"
    BOLD   = "\033[1m"
    DIM    = "\033[2m"
    RESET  = "\033[0m"


# ─── 신호 렌더 헬퍼 ──────────────────────────────────────────
SIGNAL_SYMBOLS = {
    Signal.RED:    (Color.RED,    "●"),
    Signal.YELLOW: (Color.YELLOW, "●"),
    Signal.GREEN:  (Color.GREEN,  "●"),
}

DIM_SYMBOLS = {
    Signal.RED:    (Color.DIM, "○"),
    Signal.YELLOW: (Color.DIM, "○"),
    Signal.GREEN:  (Color.DIM, "○"),
}


def render_light(sig: Signal, active: bool) -> str:
    color, symbol = (SIGNAL_SYMBOLS if active else DIM_SYMBOLS)[sig]
    return f"{color}{symbol}{Color.RESET}"


# ─── 단계 설정 테이블 ─────────────────────────────────────────
@dataclass
class PhaseConfig:
    north: Signal
    south: Signal
    east:  Signal
    west:  Signal
    ped_ns: str   # 'walk' | 'stop'
    ped_ew: str
    label: str


PHASE_CONFIGS: Dict[Phase, PhaseConfig] = {
    Phase.NS_GREEN: PhaseConfig(
        north=Signal.GREEN, south=Signal.GREEN,
        east=Signal.RED,    west=Signal.RED,
        ped_ns="stop",  ped_ew="walk",
        label="남북 직진 (초록)",
    ),
    Phase.NS_YELLOW: PhaseConfig(
        north=Signal.YELLOW, south=Signal.YELLOW,
        east=Signal.RED,     west=Signal.RED,
        ped_ns="stop",  ped_ew="stop",
        label="남북 주의 (황색)",
    ),
    Phase.EW_GREEN: PhaseConfig(
        north=Signal.RED,   south=Signal.RED,
        east=Signal.GREEN,  west=Signal.GREEN,
        ped_ns="walk",  ped_ew="stop",
        label="동서 직진 (초록)",
    ),
    Phase.EW_YELLOW: PhaseConfig(
        north=Signal.RED,    south=Signal.RED,
        east=Signal.YELLOW,  west=Signal.YELLOW,
        ped_ns="stop",  ped_ew="stop",
        label="동서 주의 (황색)",
    ),
}

PHASE_ORDER = [
    Phase.NS_GREEN,
    Phase.NS_YELLOW,
    Phase.EW_GREEN,
    Phase.EW_YELLOW,
]


# ─── 신호등 시스템 ────────────────────────────────────────────
@dataclass
class TrafficLightSystem:
    ns_green_dur:  int = 30
    ns_yellow_dur: int = 5
    ew_green_dur:  int = 30
    ew_yellow_dur: int = 5
    speed:         float = 1.0
    max_cycles:    int = 0   # 0 = 무한 반복

    phase_index: int = field(default=0, init=False)
    cycle_count: int = field(default=0, init=False)
    log: list = field(default_factory=list, init=False)

    def get_duration(self, phase: Phase) -> int:
        return {
            Phase.NS_GREEN:  self.ns_green_dur,
            Phase.NS_YELLOW: self.ns_yellow_dur,
            Phase.EW_GREEN:  self.ew_green_dur,
            Phase.EW_YELLOW: self.ew_yellow_dur,
        }[phase]

    def current_phase(self) -> Phase:
        return PHASE_ORDER[self.phase_index]

    def next_phase(self):
        self.phase_index = (self.phase_index + 1) % len(PHASE_ORDER)
        if self.phase_index == 0:
            self.cycle_count += 1

    def render_frame(self, phase: Phase, time_left: int) -> str:
        cfg = PHASE_CONFIGS[phase]
        lines = []

        # ── 헤더 ──
        lines.append("")
        lines.append(f"{Color.BOLD}{Color.CYAN}  사거리 신호등 시스템  {Color.RESET}")
        lines.append(f"  사이클: {Color.BOLD}{self.cycle_count:3d}{Color.RESET}  "
                     f"단계: {Color.BOLD}{cfg.label}{Color.RESET}  "
                     f"남은시간: {Color.YELLOW}{Color.BOLD}{time_left:3d}초{Color.RESET}")
        lines.append("")

        # ── 교차로 ASCII 다이어그램 ──
        # 신호 표시 함수
        def sig(direction: str) -> str:
            s = getattr(cfg, direction)
            return render_light(s, True)

        def ped(side: str) -> str:
            status = getattr(cfg, f"ped_{side}")
            if status == "walk":
                return f"{Color.GREEN}▶{Color.RESET}"
            else:
                return f"{Color.RED}✖{Color.RESET}"

        # 신호등 수직형 렌더 (R/Y/G)
        def vlight(direction: str) -> list[str]:
            """수직 신호등 3줄 반환"""
            s = getattr(cfg, direction)
            r = render_light(Signal.RED,    s == Signal.RED)
            y = render_light(Signal.YELLOW, s == Signal.YELLOW)
            g = render_light(Signal.GREEN,  s == Signal.GREEN)
            return [r, y, g]

        # 수평형 신호등 (동서용)
        def hlight(direction: str) -> str:
            s = getattr(cfg, direction)
            r = render_light(Signal.RED,    s == Signal.RED)
            y = render_light(Signal.YELLOW, s == Signal.YELLOW)
            g = render_light(Signal.GREEN,  s == Signal.GREEN)
            return f"{r} {y} {g}"

        n_r, n_y, n_g = vlight("north")
        s_r, s_y, s_g = vlight("south")

        w_ped = ped("ew")
        e_ped = ped("ew")
        n_ped = ped("ns")
        s_ped = ped("ns")

        # 교차로 그림
        road = f"{Color.DIM}══{Color.RESET}"
        cross = f"{Color.DIM}╬{Color.RESET}"

        lines += [
            f"               북 (N) {n_ped} ",
            f"               [{n_r}]         ",
            f"               [{n_y}]         ",
            f"               [{n_g}]         ",
            f"               │           ",
            f"  {hlight('west')}  ══{cross}══  {hlight('east')} ",
            f"  서(W){w_ped}          {e_ped}동(E)  ",
            f"               │           ",
            f"               [{s_g}]         ",
            f"               [{s_y}]         ",
            f"               [{s_r}]         ",
            f"               남 (S) {s_ped} ",
        ]

        lines.append("")

        # ── 단계 타임라인 ──
        timeline = []
        for i, p in enumerate(PHASE_ORDER):
            dur = self.get_duration(p)
            label_map = {
                Phase.NS_GREEN:  "NS초록",
                Phase.NS_YELLOW: "NS황색",
                Phase.EW_GREEN:  "EW초록",
                Phase.EW_YELLOW: "EW황색",
            }
            lbl = label_map[p]
            if p == phase:
                timeline.append(f"{Color.CYAN}[{Color.BOLD}{lbl}{dur:2d}s{Color.RESET}{Color.CYAN}]{Color.RESET}")
            else:
                timeline.append(f"{Color.DIM}[{lbl}{dur:2d}s]{Color.RESET}")
        lines.append("  " + " → ".join(timeline))
        lines.append("")

        # ── 보행자 범례 ──
        lines.append(f"  보행자: {Color.GREEN}▶ 통행가능{Color.RESET}  {Color.RED}✖ 정지{Color.RESET}")
        lines.append("")

        return "\n".join(lines)

    def run(self):
        phase = self.current_phase()
        time_left = self.get_duration(phase)

        print("\033[2J\033[H", end="")  # clear screen
        print(f"{Color.DIM}종료: Ctrl+C{Color.RESET}")

        try:
            while True:
                # 화면 갱신
                print("\033[H", end="")  # cursor to top
                frame = self.render_frame(phase, time_left)
                print(frame, end="", flush=True)

                time.sleep(1.0 / self.speed)
                time_left -= 1

                if time_left <= 0:
                    self.next_phase()
                    phase = self.current_phase()
                    time_left = self.get_duration(phase)

                    if self.max_cycles > 0 and self.cycle_count >= self.max_cycles:
                        print(f"\n{Color.BOLD}{Color.GREEN}  {self.max_cycles}사이클 완료. 종료합니다.{Color.RESET}\n")
                        break

        except KeyboardInterrupt:
            print(f"\n\n{Color.DIM}  시뮬레이션 종료.{Color.RESET}\n")
            self._print_summary()

    def _print_summary(self):
        total = (
            self.ns_green_dur + self.ns_yellow_dur +
            self.ew_green_dur + self.ew_yellow_dur
        )
        print(f"{Color.BOLD}=== 시뮬레이션 요약 ==={Color.RESET}")
        print(f"  완료 사이클: {self.cycle_count}")
        print(f"  1사이클 시간: {total}초")
        print(f"  NS 초록: {self.ns_green_dur}s  NS 황색: {self.ns_yellow_dur}s")
        print(f"  EW 초록: {self.ew_green_dur}s  EW 황색: {self.ew_yellow_dur}s")
        print()


# ─── CLI ──────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="사거리 신호등 시뮬레이터",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python traffic_light.py                  # 기본 실행
  python traffic_light.py --speed 5        # 5배속
  python traffic_light.py --ns 45 --ew 30  # 남북 45초, 동서 30초
  python traffic_light.py --cycles 2       # 2사이클 실행 후 종료
        """
    )
    parser.add_argument("--ns",     type=int, default=30, metavar="초",
                        help="남북 초록 신호 시간 (기본: 30)")
    parser.add_argument("--ew",     type=int, default=30, metavar="초",
                        help="동서 초록 신호 시간 (기본: 30)")
    parser.add_argument("--ny",     type=int, default=5,  metavar="초",
                        help="남북 황색 신호 시간 (기본: 5)")
    parser.add_argument("--ey",     type=int, default=5,  metavar="초",
                        help="동서 황색 신호 시간 (기본: 5)")
    parser.add_argument("--speed",  type=float, default=1.0,
                        help="시뮬레이션 배속 (기본: 1.0)")
    parser.add_argument("--cycles", type=int, default=0,
                        help="실행 사이클 수 (기본: 0=무한)")

    args = parser.parse_args()

    system = TrafficLightSystem(
        ns_green_dur=args.ns,
        ns_yellow_dur=args.ny,
        ew_green_dur=args.ew,
        ew_yellow_dur=args.ey,
        speed=args.speed,
        max_cycles=args.cycles,
    )

    system.run()


if __name__ == "__main__":
    main()
