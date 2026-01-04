/**
 * History module for displaying and managing transcription history.
 * T018-T022: loadHistory, renderHistoryTable, onRecordClick, new indicator, empty state
 */

// History elements (will be populated after DOM load)
const historyEls = {
  historyLoading: null,
  historyEmpty: null,
  historyTable: null,
  historyTableBody: null,
  viewAllHistory: null,
  // Modal elements
  tagsModal: null,
  tagsInput: null,
  tagsModalClose: null,
  tagsModalCancel: null,
  tagsModalSave: null,
  deleteModal: null,
  deleteModalCancel: null,
  deleteModalConfirm: null,
}

// Current active menu and modal state
let activeMenu = null
let currentEditTaskId = null
let currentDeleteTaskId = null

// Initialize history elements
function initHistoryElements() {
  historyEls.historyLoading = document.getElementById('historyLoading')
  historyEls.historyEmpty = document.getElementById('historyEmpty')
  historyEls.historyTable = document.getElementById('historyTable')
  historyEls.historyTableBody = document.getElementById('historyTableBody')
  historyEls.viewAllHistory = document.getElementById('viewAllHistory')
  // Modal elements
  historyEls.tagsModal = document.getElementById('tagsModal')
  historyEls.tagsInput = document.getElementById('tagsInput')
  historyEls.tagsModalClose = document.getElementById('tagsModalClose')
  historyEls.tagsModalCancel = document.getElementById('tagsModalCancel')
  historyEls.tagsModalSave = document.getElementById('tagsModalSave')
  historyEls.deleteModal = document.getElementById('deleteModal')
  historyEls.deleteModalCancel = document.getElementById('deleteModalCancel')
  historyEls.deleteModalConfirm = document.getElementById('deleteModalConfirm')

  // Set up modal event listeners
  setupModalListeners()
}

/**
 * Format duration in seconds to MM:SS or HH:MM:SS
 */
function formatDuration(seconds) {
  if (!seconds || seconds <= 0) return '-'
  const hours = Math.floor(seconds / 3600)
  const mins = Math.floor((seconds % 3600) / 60)
  const secs = Math.floor(seconds % 60)
  if (hours > 0) {
    return `${hours}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

/**
 * Format date to relative time or date string
 */
function formatRelativeTime(dateStr) {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  const now = new Date()
  const diff = now - date
  const seconds = Math.floor(diff / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)
  const days = Math.floor(hours / 24)

  if (seconds < 60) return '刚刚'
  if (minutes < 60) return `${minutes} 分钟前`
  if (hours < 24) return `${hours} 小时前`
  if (days < 7) return `${days} 天前`

  // Format as date
  return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

/**
 * Get source type display label and class
 */
function getSourceTypeInfo(sourceType) {
  const types = {
    youtube: { label: 'YouTube', class: 'youtube' },
    upload: { label: '上传', class: 'upload' },
    url: { label: '链接', class: 'url' },
  }
  return types[sourceType] || { label: sourceType, class: '' }
}

/**
 * Fetch history records from API
 */
async function fetchHistory(page = 1, limit = 5) {
  const res = await fetch(`/history?page=${page}&limit=${limit}`)
  if (!res.ok) {
    throw new Error('Failed to fetch history')
  }
  return res.json()
}

/**
 * Mark a record as viewed via API
 */
async function markAsViewed(taskId) {
  try {
    const res = await fetch(`/history/${taskId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ viewed: true })
    })
    return res.ok
  } catch (e) {
    console.error('Failed to mark as viewed:', e)
    return false
  }
}

/**
 * Handle click on a history record
 * T020: Auto mark-as-viewed and navigate to result page
 */
async function onRecordClick(taskId, event) {
  // Mark as viewed (don't wait for response)
  markAsViewed(taskId)

  // Remove the new indicator dot
  const row = event.target.closest('tr')
  if (row) {
    const indicator = row.querySelector('.history-new-indicator')
    if (indicator) {
      indicator.remove()
    }
  }

  // Navigate to result page
  window.location.href = `/static/result.html?task_id=${taskId}`
}

/**
 * Render a single history record row
 * T019: renderHistoryTable implementation
 * T021: New record red dot indicator
 */
function renderHistoryRow(record) {
  const tr = document.createElement('tr')
  const sourceInfo = getSourceTypeInfo(record.source_type)

  // Title cell with new indicator
  const titleCell = document.createElement('td')
  titleCell.setAttribute('data-label', '标题')
  const titleDiv = document.createElement('div')
  titleDiv.className = 'history-title-cell'

  // T021: Add red dot for unviewed records
  if (!record.viewed) {
    const indicator = document.createElement('span')
    indicator.className = 'history-new-indicator'
    indicator.title = '新记录'
    titleDiv.appendChild(indicator)
  }

  const titleLink = document.createElement('a')
  titleLink.className = 'history-title-link'
  titleLink.href = '#'
  titleLink.textContent = record.title || `转写任务 ${record.task_id.slice(0, 8)}`
  titleLink.title = record.title || ''
  titleLink.addEventListener('click', (e) => {
    e.preventDefault()
    onRecordClick(record.task_id, e)
  })
  titleDiv.appendChild(titleLink)
  titleCell.appendChild(titleDiv)
  tr.appendChild(titleCell)

  // Source type cell
  const sourceCell = document.createElement('td')
  sourceCell.setAttribute('data-label', '来源')
  const sourceBadge = document.createElement('span')
  sourceBadge.className = `history-source-badge ${sourceInfo.class}`
  sourceBadge.textContent = sourceInfo.label
  sourceCell.appendChild(sourceBadge)
  tr.appendChild(sourceCell)

  // Duration cell
  const durationCell = document.createElement('td')
  durationCell.setAttribute('data-label', '时长')
  durationCell.className = 'history-duration'
  durationCell.textContent = formatDuration(record.duration)
  tr.appendChild(durationCell)

  // Time cell
  const timeCell = document.createElement('td')
  timeCell.setAttribute('data-label', '时间')
  timeCell.className = 'history-time'
  timeCell.textContent = formatRelativeTime(record.created_at)
  tr.appendChild(timeCell)

  // Operations cell
  const opsCell = document.createElement('td')
  opsCell.setAttribute('data-label', '操作')
  opsCell.className = 'history-ops-cell'
  const opsBtn = document.createElement('button')
  opsBtn.className = 'history-ops-btn'
  opsBtn.title = '更多操作'
  opsBtn.innerHTML = `
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="1"/><circle cx="12" cy="5" r="1"/><circle cx="12" cy="19" r="1"/></svg>
  `
  opsBtn.addEventListener('click', (e) => {
    e.stopPropagation()
    showOperationMenu(record.task_id, opsBtn)
  })
  opsCell.appendChild(opsBtn)
  tr.appendChild(opsCell)

  return tr
}

/**
 * Render the history table with records
 * T019: Full table rendering
 * T022: Empty state display
 */
function renderHistoryTable(records) {
  if (!historyEls.historyTableBody) return

  // Clear existing content
  historyEls.historyTableBody.innerHTML = ''

  // T022: Show empty state if no records
  if (!records || records.length === 0) {
    historyEls.historyTable.hidden = true
    historyEls.historyEmpty.hidden = false
    return
  }

  // Render records
  historyEls.historyEmpty.hidden = true
  historyEls.historyTable.hidden = false

  records.forEach(record => {
    const row = renderHistoryRow(record)
    historyEls.historyTableBody.appendChild(row)
  })
}

/**
 * Show loading state
 */
function showHistoryLoading() {
  if (historyEls.historyLoading) historyEls.historyLoading.hidden = false
  if (historyEls.historyEmpty) historyEls.historyEmpty.hidden = true
  if (historyEls.historyTable) historyEls.historyTable.hidden = true
}

/**
 * Hide loading state
 */
function hideHistoryLoading() {
  if (historyEls.historyLoading) historyEls.historyLoading.hidden = true
}

/**
 * Load and display history records
 * T018: Main loadHistory function
 */
async function loadHistory() {
  // Check if history elements exist (not on all pages)
  if (!document.getElementById('historyLoading')) return

  // Skip auto-load on full history page (has its own pagination script)
  if (document.querySelector('.history-page')) return

  initHistoryElements()
  showHistoryLoading()

  try {
    const data = await fetchHistory(1, 8) // Show 8 recent records on homepage
    hideHistoryLoading()
    renderHistoryTable(data.records)

    // Show/hide view all link based on total count
    if (historyEls.viewAllHistory) {
      historyEls.viewAllHistory.hidden = data.total <= 8
    }
  } catch (e) {
    console.error('Failed to load history:', e)
    hideHistoryLoading()
    renderHistoryTable([]) // Show empty state on error
  }
}

/**
 * Refresh history (can be called after transcription completes)
 */
async function refreshHistory() {
  await loadHistory()
}

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', loadHistory)
} else {
  loadHistory()
}

// ============== Operation Menu Functions (T028-T032) ==============

/**
 * T028: Show/hide operation menu dropdown
 */
function showOperationMenu(taskId, buttonEl) {
  // Close any existing menu
  closeAllMenus()

  // Create menu element
  const menu = document.createElement('div')
  menu.className = 'history-ops-menu'
  menu.innerHTML = `
    <button class="history-ops-menu-item" data-action="download-srt">
      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" x2="12" y1="15" y2="3"/></svg>
      下载 SRT
    </button>
    <button class="history-ops-menu-item" data-action="download-md">
      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/></svg>
      下载 Markdown
    </button>
    <button class="history-ops-menu-item" data-action="copy-link">
      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>
      复制链接
    </button>
    <div class="history-ops-divider"></div>
    <button class="history-ops-menu-item" data-action="edit-tags">
      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"/></svg>
      编辑标签
    </button>
    <button class="history-ops-menu-item danger" data-action="delete">
      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/></svg>
      删除
    </button>
  `

  // Add click handlers for menu items
  menu.querySelectorAll('.history-ops-menu-item').forEach(item => {
    item.addEventListener('click', (e) => {
      e.stopPropagation()
      const action = item.dataset.action
      handleMenuAction(action, taskId)
      closeAllMenus()
    })
  })

  // Position menu relative to button
  const cell = buttonEl.closest('.history-ops-cell')
  cell.appendChild(menu)

  // Trigger animation
  requestAnimationFrame(() => {
    menu.classList.add('active')
  })

  activeMenu = menu
}

/**
 * Close all open menus
 */
function closeAllMenus() {
  if (activeMenu) {
    activeMenu.remove()
    activeMenu = null
  }
}

/**
 * Handle menu action click
 */
function handleMenuAction(action, taskId) {
  switch (action) {
    case 'download-srt':
      downloadSRT(taskId)
      break
    case 'download-md':
      downloadMarkdown(taskId)
      break
    case 'copy-link':
      copyResultLink(taskId)
      break
    case 'edit-tags':
      editTags(taskId)
      break
    case 'delete':
      deleteRecord(taskId)
      break
  }
}

/**
 * T029: Download SRT file
 */
function downloadSRT(taskId) {
  window.open(`/artifacts/${taskId}/result.srt`, '_blank')
}

/**
 * T029: Download Markdown file
 */
function downloadMarkdown(taskId) {
  window.open(`/artifacts/${taskId}/result.md`, '_blank')
}

/**
 * T030: Copy result link to clipboard
 */
async function copyResultLink(taskId) {
  const url = `${window.location.origin}/static/result.html?task_id=${taskId}`
  try {
    await navigator.clipboard.writeText(url)
    showToast('链接已复制到剪贴板')
  } catch (e) {
    console.error('Failed to copy link:', e)
    showToast('复制失败，请手动复制')
  }
}

/**
 * T031: Open tags edit modal
 */
async function editTags(taskId) {
  currentEditTaskId = taskId

  // Fetch current tags
  try {
    const res = await fetch(`/history/${taskId}`)
    if (res.ok) {
      const record = await res.json()
      historyEls.tagsInput.value = (record.tags || []).join(', ')
    }
  } catch (e) {
    historyEls.tagsInput.value = ''
  }

  historyEls.tagsModal.hidden = false
  historyEls.tagsInput.focus()
}

/**
 * Save tags from modal
 */
async function saveTags() {
  if (!currentEditTaskId) return

  const tagsString = historyEls.tagsInput.value.trim()
  const tags = tagsString ? tagsString.split(/[,，]/).map(t => t.trim()).filter(t => t) : []

  try {
    const res = await fetch(`/history/${currentEditTaskId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tags })
    })

    if (res.ok) {
      showToast('标签已更新')
      closeTagsModal()
      refreshHistory()
    } else {
      showToast('更新失败')
    }
  } catch (e) {
    console.error('Failed to save tags:', e)
    showToast('更新失败')
  }
}

/**
 * Close tags modal
 */
function closeTagsModal() {
  historyEls.tagsModal.hidden = true
  currentEditTaskId = null
  historyEls.tagsInput.value = ''
}

/**
 * T032: Show delete confirmation modal
 */
function deleteRecord(taskId) {
  currentDeleteTaskId = taskId
  historyEls.deleteModal.hidden = false
}

/**
 * Confirm delete action
 */
async function confirmDelete() {
  if (!currentDeleteTaskId) return

  try {
    const res = await fetch(`/history/${currentDeleteTaskId}`, {
      method: 'DELETE'
    })

    if (res.ok) {
      showToast('记录已删除')
      closeDeleteModal()
      refreshHistory()
    } else {
      showToast('删除失败')
    }
  } catch (e) {
    console.error('Failed to delete record:', e)
    showToast('删除失败')
  }
}

/**
 * Close delete modal
 */
function closeDeleteModal() {
  historyEls.deleteModal.hidden = true
  currentDeleteTaskId = null
}

/**
 * Show toast notification
 */
function showToast(message) {
  // Remove existing toast
  const existingToast = document.querySelector('.toast')
  if (existingToast) existingToast.remove()

  const toast = document.createElement('div')
  toast.className = 'toast'
  toast.textContent = message
  document.body.appendChild(toast)

  setTimeout(() => {
    toast.remove()
  }, 3000)
}

/**
 * Set up modal event listeners
 */
function setupModalListeners() {
  // Tags modal
  if (historyEls.tagsModalClose) {
    historyEls.tagsModalClose.addEventListener('click', closeTagsModal)
  }
  if (historyEls.tagsModalCancel) {
    historyEls.tagsModalCancel.addEventListener('click', closeTagsModal)
  }
  if (historyEls.tagsModalSave) {
    historyEls.tagsModalSave.addEventListener('click', saveTags)
  }

  // Delete modal
  if (historyEls.deleteModalCancel) {
    historyEls.deleteModalCancel.addEventListener('click', closeDeleteModal)
  }
  if (historyEls.deleteModalConfirm) {
    historyEls.deleteModalConfirm.addEventListener('click', confirmDelete)
  }

  // Close menus when clicking outside
  document.addEventListener('click', (e) => {
    if (!e.target.closest('.history-ops-cell')) {
      closeAllMenus()
    }
  })

  // Close modals on backdrop click
  if (historyEls.tagsModal) {
    historyEls.tagsModal.querySelector('.modal-backdrop')?.addEventListener('click', closeTagsModal)
  }
  if (historyEls.deleteModal) {
    historyEls.deleteModal.querySelector('.modal-backdrop')?.addEventListener('click', closeDeleteModal)
  }
}

// Export functions for use in app.js and history.html
window.historyModule = {
  loadHistory,
  refreshHistory,
  markAsViewed,
  showOperationMenu,
  initHistoryElements,
}
