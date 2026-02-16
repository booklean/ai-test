/**
 * 사거리 신호등 시스템 - JavaScript 상태 머신
 *
 * 단계(Phase) 순환:
 *   NS_GREEN  → NS_YELLOW  → EW_GREEN  → EW_YELLOW  → (반복)
 *   남북 초록     남북 황색     동서 초록     동서 황색
 */

// ─── 신호 단계 정의 ───────────────────────────────────────────
const PHASES = {
  NS_GREEN:  'NS_GREEN',
  NS_YELLOW: 'NS_YELLOW',
  EW_GREEN:  'EW_GREEN',
  EW_YELLOW: 'EW_YELLOW',
};

// 각 단계의 신호 상태 매핑
//   각 방향: 'red' | 'yellow' | 'green'
const PHASE_MAP = {
  [PHASES.NS_GREEN]: {
    north: 'green',  south: 'green',
    east:  'red',    west:  'red',
    pedNS: 'stop',   pedEW: 'walk',   // 보행자: NS도로 정지, EW보도 통행
    label: '남북 직진 (초록)',
  },
  [PHASES.NS_YELLOW]: {
    north: 'yellow', south: 'yellow',
    east:  'red',    west:  'red',
    pedNS: 'stop',   pedEW: 'stop',
    label: '남북 주의 (황색)',
  },
  [PHASES.EW_GREEN]: {
    north: 'red',    south: 'red',
    east:  'green',  west:  'green',
    pedNS: 'walk',   pedEW: 'stop',   // 보행자: NS보도 통행, EW도로 정지
    label: '동서 직진 (초록)',
  },
  [PHASES.EW_YELLOW]: {
    north: 'red',    south: 'red',
    east:  'yellow', west:  'yellow',
    pedNS: 'stop',   pedEW: 'stop',
    label: '동서 주의 (황색)',
  },
};

// 단계 순서
const PHASE_ORDER = [
  PHASES.NS_GREEN,
  PHASES.NS_YELLOW,
  PHASES.EW_GREEN,
  PHASES.EW_YELLOW,
];

// ─── 상태 ──────────────────────────────────────────────────────
let state = {
  running:       false,
  phaseIndex:    0,          // PHASE_ORDER 인덱스
  timeLeft:      0,          // 남은 초
  cycleCount:    0,
  speed:         1,          // 배속 (1~10)
  intervalId:    null,
  durations: {
    nsGreen:  30,
    nsYellow:  5,
    ewGreen:  30,
    ewYellow:  5,
  },
};

// ─── 단계별 지속 시간 조회 ──────────────────────────────────────
function getPhaseDuration(phaseKey) {
  switch (phaseKey) {
    case PHASES.NS_GREEN:  return state.durations.nsGreen;
    case PHASES.NS_YELLOW: return state.durations.nsYellow;
    case PHASES.EW_GREEN:  return state.durations.ewGreen;
    case PHASES.EW_YELLOW: return state.durations.ewYellow;
  }
}

// ─── DOM 헬퍼 ──────────────────────────────────────────────────
function el(id) { return document.getElementById(id); }

function setLightState(direction, signalColor) {
  ['red', 'yellow', 'green'].forEach(color => {
    const node = el(`${direction}-${color}`);
    if (node) {
      node.classList.toggle('on', color === signalColor);
    }
  });
}

function setPedestrianState(side, pedState) {
  // side: 'ns' or 'ew'
  // pedState: 'walk' | 'stop' | 'wait'
  const dirs = side === 'ns' ? ['north', 'south'] : ['east', 'west'];
  dirs.forEach(dir => {
    const icon  = el(`ped-${dir}-icon`);
    const label = el(`ped-${dir}-label`);
    if (!icon || !label) return;

    icon.className  = `ped-icon ${pedState}`;
    label.className = `ped-label ${pedState}`;

    if (pedState === 'walk') {
      icon.textContent  = '🚶';
      label.textContent = '통행';
    } else if (pedState === 'stop') {
      icon.textContent  = '🚷';
      label.textContent = '정지';
    } else {
      icon.textContent  = '🚶';
      label.textContent = '대기';
    }
  });
}

function highlightPhaseStep(phaseKey) {
  const stepMap = {
    [PHASES.NS_GREEN]:  'step-ns-green',
    [PHASES.NS_YELLOW]: 'step-ns-yellow',
    [PHASES.EW_GREEN]:  'step-ew-green',
    [PHASES.EW_YELLOW]: 'step-ew-yellow',
  };
  Object.values(stepMap).forEach(id => {
    const node = el(id);
    if (node) node.classList.remove('active');
  });
  const active = el(stepMap[phaseKey]);
  if (active) active.classList.add('active');
}

function updateCarAnimation(phaseKey) {
  const carNS = el('car-ns');
  const carEW = el('car-ew');
  if (!carNS || !carEW) return;

  const nsMoving = phaseKey === PHASES.NS_GREEN;
  const ewMoving = phaseKey === PHASES.EW_GREEN;

  carNS.classList.toggle('running', nsMoving);
  carEW.classList.toggle('running', ewMoving);
}

// ─── 단계 적용 ──────────────────────────────────────────────────
function applyPhase(phaseKey) {
  const cfg = PHASE_MAP[phaseKey];
  if (!cfg) return;

  // 신호등 업데이트
  ['north', 'south', 'east', 'west'].forEach(dir => {
    setLightState(dir, cfg[dir]);
  });

  // 보행자 신호 업데이트
  setPedestrianState('ns', cfg.pedNS);
  setPedestrianState('ew', cfg.pedEW);

  // 타임라인 하이라이트
  highlightPhaseStep(phaseKey);

  // 차량 애니메이션
  updateCarAnimation(phaseKey);

  // 상태 표시
  el('phase-name').textContent = cfg.label;
}

// ─── 초기 상태 렌더링 ──────────────────────────────────────────
function renderInitialState() {
  // 모든 신호등 끄기
  ['north', 'south', 'east', 'west'].forEach(dir => {
    ['red', 'yellow', 'green'].forEach(color => {
      const node = el(`${dir}-${color}`);
      if (node) node.classList.remove('on');
    });
  });

  // 보행자 대기
  ['north', 'south', 'east', 'west'].forEach(dir => {
    const icon  = el(`ped-${dir}-icon`);
    const label = el(`ped-${dir}-label`);
    if (icon)  { icon.textContent  = '🚶'; icon.className  = 'ped-icon'; }
    if (label) { label.textContent = '대기'; label.className = 'ped-label'; }
  });

  el('phase-name').textContent   = '-';
  el('countdown').textContent    = '--';
  el('cycle-count').textContent  = '0';

  // 타임라인 초기화
  ['step-ns-green','step-ns-yellow','step-ew-green','step-ew-yellow'].forEach(id => {
    const node = el(id);
    if (node) node.classList.remove('active');
  });

  // 차량 정지
  const carNS = el('car-ns');
  const carEW = el('car-ew');
  if (carNS) carNS.classList.remove('running');
  if (carEW) carEW.classList.remove('running');

  updateDurationLabels();
}

// ─── 틱 (매 초 호출) ──────────────────────────────────────────
function tick() {
  if (!state.running) return;

  state.timeLeft -= 1;
  el('countdown').textContent = Math.max(0, state.timeLeft);

  if (state.timeLeft <= 0) {
    // 다음 단계로
    state.phaseIndex = (state.phaseIndex + 1) % PHASE_ORDER.length;

    // 사이클 카운트: NS_GREEN 으로 돌아올 때마다 +1
    if (state.phaseIndex === 0) {
      state.cycleCount += 1;
      el('cycle-count').textContent = state.cycleCount;
    }

    const nextPhase = PHASE_ORDER[state.phaseIndex];
    state.timeLeft  = getPhaseDuration(nextPhase);
    applyPhase(nextPhase);
    el('countdown').textContent = state.timeLeft;
  }
}

// ─── 시뮬레이션 제어 ──────────────────────────────────────────
function startSimulation() {
  if (state.running) return;
  state.running = true;
  el('btn-start-stop').textContent = '일시정지';

  // 처음 시작 시 초기 단계 설정
  if (state.timeLeft <= 0) {
    state.phaseIndex = 0;
    const firstPhase = PHASE_ORDER[0];
    state.timeLeft   = getPhaseDuration(firstPhase);
    applyPhase(firstPhase);
    el('countdown').textContent = state.timeLeft;
  }

  const intervalMs = Math.round(1000 / state.speed);
  state.intervalId = setInterval(tick, intervalMs);
}

function pauseSimulation() {
  if (!state.running) return;
  state.running = false;
  el('btn-start-stop').textContent = '계속';
  clearInterval(state.intervalId);
  state.intervalId = null;
}

function toggleSimulation() {
  if (state.running) {
    pauseSimulation();
  } else {
    startSimulation();
  }
}

function resetSimulation() {
  const wasRunning = state.running;
  pauseSimulation();

  state.phaseIndex  = 0;
  state.timeLeft    = 0;
  state.cycleCount  = 0;

  el('btn-start-stop').textContent = '시작';
  renderInitialState();

  if (wasRunning) {
    // 리셋 후 자동 재시작
    startSimulation();
  }
}

// ─── 속도 변경 ──────────────────────────────────────────────────
function changeSpeed(value) {
  state.speed = parseInt(value, 10);
  el('speed-label').textContent = `${state.speed}x`;

  if (state.running) {
    // 인터벌 재시작
    clearInterval(state.intervalId);
    const intervalMs = Math.round(1000 / state.speed);
    state.intervalId = setInterval(tick, intervalMs);
  }
}

// ─── 지속 시간 업데이트 ────────────────────────────────────────
function updateDuration(key, value) {
  const parsed = parseInt(value, 10);
  if (isNaN(parsed) || parsed < 1) return;
  state.durations[key] = parsed;
  updateDurationLabels();
}

function updateDurationLabels() {
  el('dur-ns-green').textContent  = `${state.durations.nsGreen}s`;
  el('dur-ns-yellow').textContent = `${state.durations.nsYellow}s`;
  el('dur-ew-green').textContent  = `${state.durations.ewGreen}s`;
  el('dur-ew-yellow').textContent = `${state.durations.ewYellow}s`;
}

// ─── 키보드 단축키 ────────────────────────────────────────────
document.addEventListener('keydown', (e) => {
  if (e.code === 'Space') {
    e.preventDefault();
    toggleSimulation();
  } else if (e.code === 'KeyR') {
    resetSimulation();
  }
});

// ─── 초기화 ──────────────────────────────────────────────────
renderInitialState();
