/**
 * Go면접 면접 연습 - 앱 초기화 및 라우팅 모듈
 * API 호출 유틸리티, 뷰 전환, 네비게이션 관리
 */

import { renderInterviewHome, cleanupInterview } from './interview.js';
import { renderRecordsView } from './records.js';

// ============================================
// API 유틸리티
// ============================================

const API_BASE = '/api';

/**
 * API 호출 래퍼 함수
 * JSON 헤더 설정, 에러 처리 포함
 * @param {string} endpoint - API 엔드포인트 (예: '/daily-quote')
 * @param {object} options - fetch 옵션 (method, body 등)
 * @returns {Promise<object>} 응답 JSON 데이터
 * @throws {Error} 서버 에러 시 detail 메시지를 포함한 Error
 */
export async function apiCall(endpoint, options = {}) {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });

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
// 초기화
// ============================================

document.addEventListener('DOMContentLoaded', () => {
  // 네비게이션 버튼 이벤트 바인딩
  const navHome = document.getElementById('nav-home');
  const navRecords = document.getElementById('nav-records');

  navHome.addEventListener('click', () => showView('home'));
  navRecords.addEventListener('click', () => showView('records'));

  // 초기 홈 뷰 표시
  showView('home');
});
