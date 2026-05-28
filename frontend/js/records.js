/**
 * Go면접 면접 연습 - 기록/통계 모듈
 * 면접 기록 조회, 직무별 필터링, 통계 표시
 */

import { apiCall } from './app.js';

// ============================================
// 기록/통계 뷰 렌더링
// ============================================

/**
 * 기록/통계 뷰 렌더링
 * @param {HTMLElement} container - 렌더링 대상 컨테이너
 */
export async function renderRecordsView(container) {
  container.innerHTML = `
    <div class="loading-indicator">
      <div class="spinner"></div>
      <span>기록을 불러오는 중...</span>
    </div>
  `;

  try {
    const [recordsData, statsData] = await Promise.all([
      fetchRecords(),
      fetchStats(),
    ]);
    renderRecordsContent(container, recordsData, statsData);
  } catch (error) {
    container.innerHTML = `<div class="error-message">${error.message}</div>`;
  }
}

/**
 * 기록 조회 API 호출
 */
async function fetchRecords(jobField = null) {
  const params = jobField ? `?job_field=${encodeURIComponent(jobField)}` : '';
  return await apiCall(`/records${params}`);
}

/**
 * 통계 조회 API 호출
 */
async function fetchStats() {
  return await apiCall('/stats');
}

/**
 * 기록/통계 콘텐츠 렌더링
 */
function renderRecordsContent(container, recordsData, statsData) {
  container.innerHTML = `
    <!-- 통계 카드 -->
    <div class="grid grid-cols-3 gap-3 mb-6">
      <div class="stats-card">
        <div class="stat-number">${statsData.total_interviews}</div>
        <div class="stat-label">총 연습 횟수</div>
      </div>
      <div class="stats-card">
        <div class="stat-number">${statsData.avg_score !== null ? statsData.avg_score.toFixed(1) : '-'}</div>
        <div class="stat-label">평균 점수</div>
      </div>
      <div class="stats-card">
        <div class="stat-number">${statsData.most_practiced_field || '-'}</div>
        <div class="stat-label">최다 연습 직무</div>
      </div>
    </div>

    <!-- 직무별 분포 -->
    ${Object.keys(statsData.job_distribution).length > 0 ? `
      <div class="bg-white rounded-xl border border-gray-200 p-4 mb-6 shadow-sm">
        <h3 class="text-sm font-bold text-gray-700 mb-3">직무별 분포</h3>
        <div id="distribution-bars">
          ${renderDistributionBars(statsData.job_distribution, statsData.total_interviews)}
        </div>
      </div>
    ` : ''}

    <!-- 필터 -->
    <div class="flex items-center gap-3 mb-4">
      <label class="text-sm text-gray-600 font-medium">직무 필터:</label>
      <select id="record-filter" class="px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:border-indigo-500">
        <option value="">전체</option>
        ${Object.keys(statsData.job_distribution).map(field => `
          <option value="${field}">${field}</option>
        `).join('')}
      </select>
    </div>

    <!-- 기록 목록 -->
    <div id="records-list">
      ${renderRecordsList(recordsData.records)}
    </div>
  `;

  // 필터 이벤트
  document.getElementById('record-filter').addEventListener('change', async (e) => {
    const filter = e.target.value || null;
    try {
      const filtered = await fetchRecords(filter);
      document.getElementById('records-list').innerHTML = renderRecordsList(filtered.records);
    } catch (error) {
      document.getElementById('records-list').innerHTML = `<div class="error-message">${error.message}</div>`;
    }
  });
}

/**
 * 직무별 분포 프로그레스 바 렌더링
 */
function renderDistributionBars(distribution, total) {
  return Object.entries(distribution)
    .sort((a, b) => b[1] - a[1])
    .map(([field, count]) => {
      const percentage = total > 0 ? (count / total) * 100 : 0;
      return `
        <div class="progress-bar-container">
          <div class="progress-bar-label">
            <span class="field-name">${field}</span>
            <span class="field-count">${count}회</span>
          </div>
          <div class="progress-bar-track">
            <div class="progress-bar-fill" style="width: ${percentage}%"></div>
          </div>
        </div>
      `;
    }).join('');
}

/**
 * 기록 목록 렌더링
 */
function renderRecordsList(records) {
  if (!records || records.length === 0) {
    return `<div class="text-center text-gray-500 py-8 text-sm">아직 면접 기록이 없습니다.</div>`;
  }

  return records.map(record => {
    const scoreHtml = record.score !== null
      ? `<span class="score-badge ${record.score >= 7 ? 'score-high' : record.score >= 4 ? 'score-mid' : 'score-low'}">${record.score}</span>`
      : '';

    return `
      <div class="record-item">
        <div class="record-meta">
          <span>📅 ${record.date}</span>
          <span>💼 ${record.job_field}</span>
          ${scoreHtml}
        </div>
        <div class="record-question">${record.question}</div>
      </div>
    `;
  }).join('');
}
