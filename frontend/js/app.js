/**
 * Go면접 면접 연습 - 앱 초기화 및 라우팅 모듈
 * API 호출 유틸리티, 뷰 전환, 네비게이션 관리
 * BYOK (Bring Your Own Key) 헤더 주입 + 키 검증 UI
 */

import { renderInterviewHome, cleanupInterview } from './interview.js';
import { renderRecordsView } from './records.js';

// ============================================
// BYOK 상태 관리
// ============================================

const BYOK_STORAGE_KEY = 'gofactory.openrouter_key';
const BYOK_MODEL_STORAGE_KEY = 'gofactory.openrouter_model';
const BYOK_REMEMBER_KEY = 'gofactory.byok_remember';

/**
 * 현재 활성 OpenRouter 키. 메모리 보관이 기본; remember=true일 때만 localStorage 미러링.
 * 키 자체는 절대 console.log·DOM 텍스트에 직접 출력하지 않는다.
 */
const byokState = {
  key: '',
  model: '',
  remember: false,
  validated: null, // null | true | false
};

/**
 * 현재 BYOK 키 반환 (빈 문자열이면 미설정).
 */
export function byokKey() {
  return byokState.key || '';
}

/**
 * 현재 BYOK 모델 ID 반환.
 */
export function byokModel() {
  return byokState.model || '';
}

// ============================================
// API 유틸리티
// ============================================

const API_BASE = '/api';

/**
 * BYOK 헤더를 빌드한다. 키가 없으면 빈 객체.
 * @returns {Record<string,string>}
 */
function buildByokHeaders() {
  const headers = {};
  const key = byokKey();
  if (key) {
    headers['X-OpenRouter-Key'] = key;
    const model = byokModel();
    if (model) headers['X-LLM-Model'] = model;
  }
  return headers;
}

/**
 * API 호출 래퍼 함수
 * JSON 헤더 + BYOK 헤더 자동 주입, 에러 처리 포함.
 * 응답 헤더 X-Backend-Used 를 읽어 backend 배지를 갱신한다.
 * @param {string} endpoint - API 엔드포인트 (예: '/daily-quote')
 * @param {object} options - fetch 옵션 (method, body 등)
 * @returns {Promise<object>} 응답 JSON 데이터
 * @throws {Error} 서버 에러 시 detail 메시지를 포함한 Error
 */
export async function apiCall(endpoint, options = {}) {
  const userHeaders = options.headers || {};
  const headers = {
    'Content-Type': 'application/json',
    ...buildByokHeaders(),
    ...userHeaders,
  };

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  // 백엔드가 어떤 LLM을 썼는지 배지 갱신 (성공·실패와 무관)
  const backendUsed = response.headers.get('X-Backend-Used');
  if (backendUsed) updateBackendBadge(backendUsed);

  if (!response.ok) {
    let detail = '서버 오류가 발생했습니다.';
    try {
      const errorData = await response.json();
      if (errorData.detail) {
        detail = errorData.detail;
      }
    } catch {
      // JSON 파싱 실패 시 기본 메시지 사용
    }
    throw new Error(detail);
  }

  return response.json();
}

// ============================================
// 뷰 전환 로직
// ============================================

let currentView = 'home';

/**
 * 뷰를 전환한다 (홈 ↔ 기록/통계)
 * @param {string} viewName - 'home' 또는 'records'
 */
function showView(viewName) {
  const app = document.getElementById('app');
  const navHome = document.getElementById('nav-home');
  const navRecords = document.getElementById('nav-records');

  // 이전 뷰 정리
  if (currentView === 'home') {
    cleanupInterview();
  }

  currentView = viewName;

  // 네비게이션 active 상태 업데이트
  navHome.classList.toggle('active', viewName === 'home');
  navRecords.classList.toggle('active', viewName === 'records');

  // 뷰 렌더링
  app.innerHTML = '';

  if (viewName === 'home') {
    renderHomeView(app);
  } else if (viewName === 'records') {
    renderRecordsView(app);
  }
}

/**
 * 홈 뷰 렌더링
 * 오늘의 명언 + 직무 선택 + 면접 시작 버튼
 */
function renderHomeView(container) {
  // 명언 카드
  const quoteSection = document.createElement('div');
  quoteSection.id = 'quote-section';
  quoteSection.innerHTML = `
    <div class="quote-card">
      <p id="daily-quote">명언을 불러오는 중...</p>
    </div>
  `;
  container.appendChild(quoteSection);

  // 면접 시작 영역
  const interviewSection = document.createElement('div');
  interviewSection.id = 'interview-section';
  container.appendChild(interviewSection);

  // 면접 홈 UI 렌더링 (직무 선택 + 시작 버튼)
  renderInterviewHome(interviewSection);

  // 명언 로드
  loadDailyQuote();
}

/**
 * 오늘의 명언을 API에서 로드하여 표시
 */
async function loadDailyQuote() {
  const quoteEl = document.getElementById('daily-quote');
  if (!quoteEl) return;

  try {
    const data = await apiCall('/daily-quote');
    quoteEl.textContent = `💡 ${data.quote}`;
  } catch {
    quoteEl.textContent = '오늘도 면접 연습 화이팅! 🔥';
  }
}

// ============================================
// BYOK 백엔드 배지
// ============================================

/**
 * 상단 배지에 현재 백엔드 표시 ("📡 Bedrock" 또는 "🔑 OpenRouter").
 * @param {string} backend - "bedrock" | "openrouter"
 */
function updateBackendBadge(backend) {
  const badge = document.getElementById('backend-badge');
  if (!badge) return;
  if (backend === 'openrouter') {
    badge.textContent = '🔑 OpenRouter';
    badge.classList.remove('backend-badge-bedrock');
    badge.classList.add('backend-badge-openrouter');
  } else {
    badge.textContent = '📡 Bedrock';
    badge.classList.remove('backend-badge-openrouter');
    badge.classList.add('backend-badge-bedrock');
  }
}

// ============================================
// BYOK UI 로직
// ============================================

/**
 * BYOK 상태/입력값을 localStorage와 동기화.
 * remember=false면 localStorage에서 제거 (메모리만 유지).
 */
function persistByokIfNeeded() {
  try {
    if (byokState.remember && byokState.key) {
      localStorage.setItem(BYOK_STORAGE_KEY, byokState.key);
      localStorage.setItem(BYOK_MODEL_STORAGE_KEY, byokState.model || '');
      localStorage.setItem(BYOK_REMEMBER_KEY, '1');
    } else {
      localStorage.removeItem(BYOK_STORAGE_KEY);
      localStorage.removeItem(BYOK_MODEL_STORAGE_KEY);
      localStorage.setItem(BYOK_REMEMBER_KEY, '0');
    }
  } catch {
    // localStorage 사용 불가 환경 — 메모리 보관으로 폴백
  }
}

/**
 * localStorage 에서 이전 BYOK 설정 복구 (있는 경우).
 */
function restoreByokFromStorage() {
  try {
    const remember = localStorage.getItem(BYOK_REMEMBER_KEY) === '1';
    if (!remember) return;
    const key = localStorage.getItem(BYOK_STORAGE_KEY) || '';
    const model = localStorage.getItem(BYOK_MODEL_STORAGE_KEY) || '';
    byokState.key = key;
    byokState.model = model;
    byokState.remember = true;
  } catch {
    // ignore
  }
}

/**
 * /api/byok/models 호출 → select 채움. 기본 모델을 selected로.
 */
async function loadByokModels() {
  const select = document.getElementById('byok-model');
  if (!select) return;
  try {
    const data = await apiCall('/byok/models');
    select.innerHTML = '';
    const ids = Object.keys(data.models || {});
    for (const id of ids) {
      const opt = document.createElement('option');
      opt.value = id;
      opt.textContent = data.models[id];
      if (id === data.default) opt.selected = true;
      select.appendChild(opt);
    }
    // 복구된 모델이 있으면 우선 적용
    if (byokState.model && ids.includes(byokState.model)) {
      select.value = byokState.model;
    } else {
      byokState.model = select.value;
    }
  } catch {
    // 모델 로드 실패 → select 비워둠 (사용자에겐 텍스트 status로 알림)
  }
}

/**
 * 키 검증 결과를 status div에 렌더 (키 자체는 노출하지 않음).
 * @param {object} result - /api/byok/validate 응답
 */
function renderByokStatus(result) {
  const status = document.getElementById('byok-status');
  if (!status) return;
  status.innerHTML = '';
  if (!result) return;

  if (result.valid) {
    byokState.validated = true;
    const parts = ['✅ 키 유효'];
    if (result.label) parts.push(`라벨: ${escapeHtml(result.label)}`);
    if (result.credit_left !== null && result.credit_left !== undefined) {
      parts.push(`잔액: $${result.credit_left.toFixed(2)}`);
    }
    if (result.models_count !== null && result.models_count !== undefined) {
      parts.push(`모델: ${result.models_count}개`);
    }
    if (result.key_preview) parts.push(`(${escapeHtml(result.key_preview)})`);
    status.innerHTML = `<div class="byok-status-ok">${parts.join(' · ')}</div>`;
  } else {
    byokState.validated = false;
    const msg = result.error || '키 검증 실패';
    status.innerHTML = `<div class="byok-status-err">❌ ${escapeHtml(msg)}</div>`;
  }
}

/**
 * 간단 HTML escape (status 메시지 안전 렌더).
 */
function escapeHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

/**
 * BYOK 섹션 DOM 이벤트 바인딩.
 */
function bindByokUI() {
  const keyInput = /** @type {HTMLInputElement|null} */ (document.getElementById('byok-key'));
  const modelSelect = /** @type {HTMLSelectElement|null} */ (document.getElementById('byok-model'));
  const validateBtn = document.getElementById('byok-validate');
  const clearBtn = document.getElementById('byok-clear');
  const rememberBox = /** @type {HTMLInputElement|null} */ (document.getElementById('byok-remember'));
  const statusEl = document.getElementById('byok-status');
  if (!keyInput || !modelSelect || !validateBtn || !clearBtn || !rememberBox) return;

  // 복구 상태 반영
  if (byokState.key) keyInput.value = byokState.key;
  rememberBox.checked = byokState.remember;

  keyInput.addEventListener('input', () => {
    byokState.key = keyInput.value.trim();
    byokState.validated = null;
    if (statusEl) statusEl.innerHTML = '';
    persistByokIfNeeded();
  });

  modelSelect.addEventListener('change', () => {
    byokState.model = modelSelect.value;
    persistByokIfNeeded();
  });

  rememberBox.addEventListener('change', () => {
    byokState.remember = rememberBox.checked;
    persistByokIfNeeded();
  });

  clearBtn.addEventListener('click', () => {
    byokState.key = '';
    byokState.validated = null;
    keyInput.value = '';
    if (statusEl) statusEl.innerHTML = '';
    persistByokIfNeeded();
    updateBackendBadge('bedrock');
  });

  validateBtn.addEventListener('click', async () => {
    const key = keyInput.value.trim();
    if (!key) {
      if (statusEl) statusEl.innerHTML = '<div class="byok-status-err">❌ 키를 입력하세요.</div>';
      return;
    }
    if (statusEl) statusEl.innerHTML = '<div class="byok-status-pending">⏳ 검증 중...</div>';
    try {
      // validate 전용 호출: 헤더로 키 전달 (바디에 키 노출 회피)
      const response = await fetch(`${API_BASE}/byok/validate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-OpenRouter-Key': key,
        },
        body: JSON.stringify({}),
      });
      const result = await response.json();
      byokState.key = key;
      byokState.model = modelSelect.value;
      persistByokIfNeeded();
      renderByokStatus(result);
      // 키가 유효하면 다음 API 호출부터 자동으로 OpenRouter 사용 → 미리 배지 업데이트
      if (result.valid) updateBackendBadge('openrouter');
    } catch (err) {
      if (statusEl) {
        statusEl.innerHTML = `<div class="byok-status-err">❌ 네트워크 오류: ${escapeHtml(err.message)}</div>`;
      }
    }
  });
}

// ============================================
// 초기화
// ============================================

document.addEventListener('DOMContentLoaded', async () => {
  // BYOK 복구 + 모델 카탈로그 로드
  restoreByokFromStorage();
  bindByokUI();
  await loadByokModels();

  // 네비게이션 버튼 이벤트 바인딩
  const navHome = document.getElementById('nav-home');
  const navRecords = document.getElementById('nav-records');

  navHome.addEventListener('click', () => showView('home'));
  navRecords.addEventListener('click', () => showView('records'));

  // 초기 홈 뷰 표시
  showView('home');
});
