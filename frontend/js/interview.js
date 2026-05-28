/**
 * Go면접 면접 연습 - 면접 진행 모듈
 * 직무 선택, 질문 생성, 답변 제출, 피드백 표시
 */

import { apiCall } from './app.js';

// ============================================
// 상태 관리
// ============================================

let currentJobField = null;
let currentQuestion = null;
let isInterviewActive = false;

const JOB_FIELDS = ['반도체', '백엔드', '데이터', '마케팅', '기타'];

// ============================================
// 홈 화면 렌더링 (직무 선택 + 면접 시작)
// ============================================

/**
 * 면접 홈 UI 렌더링 (직무 선택 + 면접 시작 버튼)
 * @param {HTMLElement} container - 렌더링 대상 컨테이너
 */
export function renderInterviewHome(container) {
  container.innerHTML = `
    <div class="bg-white rounded-xl border border-gray-200 p-6 mt-4 shadow-sm">
      <h2 class="text-lg font-bold text-gray-800 mb-4">직무 분야 선택</h2>
      <div id="job-field-buttons" class="flex flex-wrap gap-2 mb-4">
        ${JOB_FIELDS.map(field => `
          <button class="job-field-btn px-4 py-2 rounded-lg border border-gray-300 text-sm font-medium text-gray-700 hover:border-indigo-400 hover:text-indigo-600 transition-colors" data-field="${field}">
            ${field}
          </button>
        `).join('')}
      </div>
      <div id="custom-field-container" class="hidden mb-4">
        <input type="text" id="custom-field-input" placeholder="직무 분야를 입력하세요" class="w-full px-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500">
      </div>
      <button id="start-interview-btn" class="w-full py-3 bg-gradient-to-r from-indigo-500 to-purple-600 text-white font-semibold rounded-lg hover:from-indigo-600 hover:to-purple-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed" disabled>
        면접 시작
      </button>
    </div>
  `;

  // 직무 선택 버튼 이벤트
  const buttons = container.querySelectorAll('.job-field-btn');
  buttons.forEach(btn => {
    btn.addEventListener('click', () => {
      // 모든 버튼 비활성 스타일
      buttons.forEach(b => {
        b.classList.remove('bg-indigo-500', 'text-white', 'border-indigo-500');
        b.classList.add('border-gray-300', 'text-gray-700');
      });
      // 선택된 버튼 활성 스타일
      btn.classList.remove('border-gray-300', 'text-gray-700');
      btn.classList.add('bg-indigo-500', 'text-white', 'border-indigo-500');

      const field = btn.dataset.field;
      const customContainer = document.getElementById('custom-field-container');
      const startBtn = document.getElementById('start-interview-btn');

      if (field === '기타') {
        customContainer.classList.remove('hidden');
        currentJobField = null;
        startBtn.disabled = true;
        // 커스텀 입력 변경 시 시작 버튼 활성화
        const customInput = document.getElementById('custom-field-input');
        customInput.addEventListener('input', () => {
          currentJobField = customInput.value.trim() || null;
          startBtn.disabled = !currentJobField;
        });
      } else {
        customContainer.classList.add('hidden');
        currentJobField = field;
        startBtn.disabled = false;
      }
    });
  });

  // 면접 시작 버튼 이벤트
  const startBtn = document.getElementById('start-interview-btn');
  startBtn.addEventListener('click', () => {
    if (currentJobField) {
      startInterview(container);
    }
  });
}

// ============================================
// 면접 진행
// ============================================

/**
 * 면접 세션 시작
 */
async function startInterview(container) {
  isInterviewActive = true;
  container.innerHTML = `
    <div class="loading-indicator">
      <div class="spinner"></div>
      <span>면접 질문을 생성하고 있습니다...</span>
    </div>
  `;

  try {
    const data = await apiCall('/question', {
      method: 'POST',
      body: JSON.stringify({ job_field: currentJobField }),
    });
    currentQuestion = data.question;
    renderQuestionView(container);
  } catch (error) {
    container.innerHTML = `
      <div class="error-message">${error.message}</div>
      <button id="retry-btn" class="mt-4 px-4 py-2 bg-indigo-500 text-white rounded-lg text-sm">다시 시도</button>
    `;
    document.getElementById('retry-btn').addEventListener('click', () => startInterview(container));
  }
}

/**
 * 질문 표시 및 답변 입력 UI
 */
function renderQuestionView(container) {
  container.innerHTML = `
    <div class="mb-2 text-sm text-gray-500">직무: <span class="font-medium text-indigo-600">${currentJobField}</span></div>
    <div class="question-box">${currentQuestion}</div>
    <textarea id="answer-input" class="w-full mt-4 p-4 border border-gray-300 rounded-lg text-sm resize-y min-h-[120px] focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500" placeholder="답변을 입력하세요..."></textarea>
    <button id="submit-answer-btn" class="w-full mt-3 py-3 bg-gradient-to-r from-indigo-500 to-purple-600 text-white font-semibold rounded-lg hover:from-indigo-600 hover:to-purple-700 transition-all">
      답변 제출
    </button>
  `;

  document.getElementById('submit-answer-btn').addEventListener('click', () => {
    const answer = document.getElementById('answer-input').value.trim();
    if (answer) {
      submitAnswer(container, answer);
    }
  });
}

/**
 * 답변 제출 및 평가 요청
 */
async function submitAnswer(container, answer) {
  container.innerHTML = `
    <div class="loading-indicator">
      <div class="spinner"></div>
      <span>AI가 답변을 평가하고 있습니다...</span>
    </div>
  `;

  try {
    const feedback = await apiCall('/evaluate', {
      method: 'POST',
      body: JSON.stringify({
        job_field: currentJobField,
        question: currentQuestion,
        answer: answer,
      }),
    });
    renderFeedbackView(container, feedback);
  } catch (error) {
    container.innerHTML = `
      <div class="error-message">${error.message}</div>
      <button id="retry-btn" class="mt-4 px-4 py-2 bg-indigo-500 text-white rounded-lg text-sm">다시 시도</button>
    `;
    document.getElementById('retry-btn').addEventListener('click', () => renderQuestionView(container));
  }
}

/**
 * 피드백 카드 렌더링
 */
function renderFeedbackView(container, feedback) {
  const scoreClass = feedback.score >= 7 ? 'score-high' : feedback.score >= 4 ? 'score-mid' : 'score-low';

  container.innerHTML = `
    <div class="feedback-card">
      <h4>📝 AI 피드백</h4>
      ${feedback.score !== null ? `
        <div class="feedback-section">
          <div class="feedback-section-title">논리성 점수</div>
          <div class="feedback-section-content">
            <span class="score-badge ${scoreClass}">${feedback.score}</span> / 10
          </div>
        </div>
      ` : ''}
      ${feedback.keywords ? `
        <div class="feedback-section">
          <div class="feedback-section-title">핵심 키워드</div>
          <div class="feedback-section-content">${feedback.keywords}</div>
        </div>
      ` : ''}
      ${feedback.improvements ? `
        <div class="feedback-section">
          <div class="feedback-section-title">개선점</div>
          <div class="feedback-section-content">${feedback.improvements}</div>
        </div>
      ` : ''}
      ${feedback.summary ? `
        <div class="feedback-section">
          <div class="feedback-section-title">총평</div>
          <div class="feedback-section-content">${feedback.summary}</div>
        </div>
      ` : ''}
    </div>
    <div class="flex gap-3 mt-4">
      <button id="next-question-btn" class="flex-1 py-3 bg-gradient-to-r from-indigo-500 to-purple-600 text-white font-semibold rounded-lg hover:from-indigo-600 hover:to-purple-700 transition-all">
        다음 질문
      </button>
      <button id="end-interview-btn" class="flex-1 py-3 border border-gray-300 text-gray-700 font-semibold rounded-lg hover:bg-gray-50 transition-all">
        면접 종료
      </button>
    </div>
  `;

  document.getElementById('next-question-btn').addEventListener('click', () => startInterview(container));
  document.getElementById('end-interview-btn').addEventListener('click', () => {
    isInterviewActive = false;
    currentQuestion = null;
    renderInterviewHome(container);
  });
}

// ============================================
// 정리
// ============================================

/**
 * 면접 상태 초기화 (뷰 전환 시 호출)
 */
export function cleanupInterview() {
  isInterviewActive = false;
  currentQuestion = null;
  currentJobField = null;
}
