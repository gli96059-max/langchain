<script setup>
import { ref } from 'vue'
import { deleteSession, updateSessionTitle, batchDeleteSessions } from '../api/index.js'

const props = defineProps({
  sessions: { type: Array, default: () => [] },
  activeId: { type: String, default: null },
  open: { type: Boolean, default: true },
})

const emit = defineEmits([
  'select', 'new-session', 'close-sidebar', 'sessions-updated',
  'show-library', 'show-shopping-lists',
])

// ── Long-press detection ──────────────────────────────

let longPressTimer = null
let longPressTriggered = false
const touchPos = ref({ x: 0, y: 0 })
const ctxMenu = ref({ show: false, session: null, x: 0, y: 0 })

function onTouchStart(e, session) {
  longPressTriggered = false
  const touch = e.touches[0]
  touchPos.value = { x: touch.clientX, y: touch.clientY }
  longPressTimer = setTimeout(() => {
    longPressTriggered = true
    showCtxMenu(touchPos.value.x, touchPos.value.y, session)
  }, 600)
}

function onTouchEnd() {
  clearTimeout(longPressTimer)
  // If long-press was triggered, don't emit select (handled by context menu)
  if (longPressTriggered) return
  // If not in batch mode and not triggered, normal click is handled by @click on the item
}

function onTouchMove(e) {
  // If finger moved more than 10px, cancel long-press (scrolling)
  if (longPressTimer) {
    const touch = e.touches[0]
    const dx = Math.abs(touch.clientX - touchPos.value.x)
    const dy = Math.abs(touch.clientY - touchPos.value.y)
    if (dx > 10 || dy > 10) {
      clearTimeout(longPressTimer)
      longPressTimer = null
    }
  }
}

function showCtxMenu(x, y, session) {
  // Clamp to viewport
  const menuW = 180, menuH = 140
  const vw = window.innerWidth, vh = window.innerHeight
  ctxMenu.value = {
    show: true,
    session,
    x: Math.min(x, vw - menuW - 8),
    y: Math.min(y, vh - menuH - 8),
  }
}

// ── Context menu actions ──────────────────────────────

function closeCtx() { ctxMenu.value.show = false }

function confirmDelete(session) {
  closeCtx()
  if (!confirm(`确定删除「${session.title}」？`)) return
  doDelete(session.id)
}

async function doDelete(id) {
  await deleteSession(id)
  emit('sessions-updated')
}

// ── Rename ────────────────────────────────────────────

const renamingId = ref(null)
const renameText = ref('')

function startRename(session) {
  closeCtx()
  renamingId.value = session.id
  renameText.value = session.title
  // Focus input after render
  setTimeout(() => {
    const input = document.querySelector('.rename-input')
    if (input) { input.focus(); input.select() }
  }, 50)
}

async function confirmRename() {
  const id = renamingId.value
  renamingId.value = null
  if (!id || !renameText.value.trim()) return
  await updateSessionTitle(id, renameText.value.trim())
  emit('sessions-updated')
}

function cancelRename() {
  renamingId.value = null
  renameText.value = ''
}

// ── Batch delete ──────────────────────────────────────

const batchMode = ref(false)
const selectedForDelete = ref(new Set())

function enterBatchMode() {
  closeCtx()
  batchMode.value = true
  selectedForDelete.value = new Set()
}

function exitBatchMode() {
  batchMode.value = false
  selectedForDelete.value = new Set()
}

function toggleSelect(id) {
  const next = new Set(selectedForDelete.value)
  next.has(id) ? next.delete(id) : next.add(id)
  selectedForDelete.value = next
}

function selectAll() {
  selectedForDelete.value = new Set(props.sessions.map(s => s.id))
}

async function executeBatchDelete() {
  const ids = Array.from(selectedForDelete.value)
  if (!ids.length) return
  if (!confirm(`确定删除选中的 ${ids.length} 个对话？`)) return
  await batchDeleteSessions(ids)
  exitBatchMode()
  emit('sessions-updated')
}

// ── Helpers ───────────────────────────────────────────

function formatTime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  const now = new Date()
  const diff = now - d
  const days = Math.floor(diff / 86400000)
  if (days === 0) return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  if (days === 1) return '昨天'
  if (days < 7) return `${days}天前`
  return d.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}
</script>

<template>
  <aside class="sidebar" :class="{ open }">
    <div class="sidebar-header">
      <div class="sidebar-brand">
        <span>🍳</span>
        <span>小斐的专属私厨助手</span>
      </div>
      <button class="new-chat-btn" @click="emit('new-session')">
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
          <path d="M8 3v10M3 8h10" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        </svg>
        新对话
      </button>
      <button class="library-btn" @click="emit('show-library')">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/>
        </svg>
        菜谱库
      </button>
      <button class="library-btn sl-btn" @click="emit('show-shopping-lists')">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/>
          <path d="M1 1h4l2.68 13.39a2 2 0 002 1.61h9.72a2 2 0 002-1.61L23 6H6"/>
        </svg>
        购物清单
      </button>
    </div>

    <!-- Batch mode bar -->
    <div v-if="batchMode" class="batch-bar">
      <span class="batch-count">已选 {{ selectedForDelete.size }} / {{ sessions.length }}</span>
      <div class="batch-actions">
        <button class="batch-btn" @click="selectAll">全选</button>
        <button class="batch-btn danger" :disabled="!selectedForDelete.size" @click="executeBatchDelete">
          删除 ({{ selectedForDelete.size }})
        </button>
        <button class="batch-btn" @click="exitBatchMode">取消</button>
      </div>
    </div>

    <div class="session-list">
      <div
        v-for="s in sessions"
        :key="s.id"
        class="session-item"
        :class="{
          active: s.id === activeId && !batchMode,
          'batch-mode': batchMode,
          'batch-selected': batchMode && selectedForDelete.has(s.id),
        }"
        @click="batchMode ? toggleSelect(s.id) : emit('select', s.id)"
        @touchstart="onTouchStart($event, s)"
        @touchend="onTouchEnd"
        @touchmove="onTouchMove"
        @contextmenu.prevent="showCtxMenu($event.clientX, $event.clientY, s)"
      >
        <div v-if="batchMode" class="batch-check" :class="{ checked: selectedForDelete.has(s.id) }">
          <svg v-if="selectedForDelete.has(s.id)" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
        </div>

        <div class="session-info">
          <!-- Inline rename input -->
          <input
            v-if="renamingId === s.id"
            v-model="renameText"
            class="rename-input"
            @keydown.enter="confirmRename"
            @keydown.escape="cancelRename"
            @blur="confirmRename"
          />
          <span v-else class="session-title">{{ s.title }}</span>
          <span class="session-time">{{ formatTime(s.updated_at) }}</span>
        </div>

        <button
          v-if="!batchMode && renamingId !== s.id"
          class="delete-btn"
          @click.stop="confirmDelete(s)"
          title="删除对话"
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M2 4h10M5 4V2.5A.5.5 0 015.5 2h3a.5.5 0 01.5.5V4M11 4v7.5a1 1 0 01-1 1H4a1 1 0 01-1-1V4" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </button>
      </div>
    </div>
  </aside>

  <!-- Context menu -->
  <Teleport to="body">
    <div v-if="ctxMenu.show" class="ctx-overlay" @click.self="closeCtx" @touchmove.prevent>
      <div class="ctx-menu" :style="{ left: ctxMenu.x + 'px', top: ctxMenu.y + 'px' }">
        <div class="ctx-item" @click="startRename(ctxMenu.session)">
          <span class="ctx-icon">✏️</span> 修改标题
        </div>
        <div class="ctx-divider"></div>
        <div class="ctx-item" @click="confirmDelete(ctxMenu.session)">
          <span class="ctx-icon">🗑️</span> <span class="ctx-danger">删除</span>
        </div>
        <div class="ctx-divider"></div>
        <div class="ctx-item" @click="enterBatchMode">
          <span class="ctx-icon">📋</span> 批量删除
        </div>
      </div>
    </div>
  </Teleport>

  <!-- Mobile overlay -->
  <div v-if="open" class="overlay" @click="emit('close-sidebar')"></div>
</template>

<style scoped>
/* ── Layout ── */
.sidebar {
  width: 280px;
  min-width: 280px;
  height: 100vh;
  background: var(--color-sidebar-bg);
  border-right: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  transition: transform 0.3s;
}

@media (max-width: 768px) {
  .sidebar {
    position: fixed;
    left: 0;
    top: 0;
    bottom: 0;
    z-index: 100;
    transform: translateX(-100%);
    padding-bottom: var(--safe-bottom, 0px);
  }
  .sidebar.open { transform: translateX(0); }
}

.overlay {
  display: none;
}
@media (max-width: 768px) {
  .overlay {
    display: block;
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.3);
    z-index: 99;
  }
}

/* ── Header ── */
.sidebar-header {
  padding: 16px;
  border-bottom: 1px solid var(--color-border);
}

@media (max-width: 768px) {
  .sidebar-header {
    padding: 16px;
    padding-top: calc(16px + var(--safe-top, 0px));
  }
}

.sidebar-brand {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 18px;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: 16px;
}

.new-chat-btn, .library-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  width: 100%;
  padding: 10px;
  border-radius: var(--radius-sm);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  font-family: var(--font-sans);
}

.new-chat-btn {
  background: var(--color-primary);
  color: #fff;
  border: none;
}
.new-chat-btn:hover { background: var(--color-primary-hover); }

.library-btn {
  background: var(--color-card);
  color: var(--color-text);
  border: 1px solid var(--color-border);
  margin-top: 6px;
}
.library-btn:hover { background: var(--color-bg); border-color: var(--color-primary); color: var(--color-primary); }

@media (max-width: 768px) {
  .new-chat-btn, .library-btn { padding: 12px; font-size: 15px; }
}

/* ── Batch bar ── */
.batch-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  background: var(--color-primary-light);
  border-bottom: 1px solid var(--color-border);
  gap: 8px;
  flex-wrap: wrap;
}

.batch-count { font-size: 13px; font-weight: 500; color: var(--color-primary); }

.batch-actions { display: flex; gap: 6px; }

.batch-btn {
  padding: 4px 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-card);
  color: var(--color-text);
  font-size: 12px;
  cursor: pointer;
  font-family: var(--font-sans);
  white-space: nowrap;
}
.batch-btn.danger { border-color: var(--color-danger); color: var(--color-danger); }
.batch-btn.danger:hover { background: var(--color-danger); color: #fff; }
.batch-btn.danger:disabled { opacity: 0.3; cursor: default; background: var(--color-card); color: var(--color-text-muted); border-color: var(--color-border); }
.batch-btn:hover:not(:disabled) { background: var(--color-bg); }

/* ── Session list ── */
.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.session-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background 0.15s;
  margin-bottom: 2px;
  user-select: none;
  -webkit-user-select: none;
}
.session-item:hover { background: var(--color-sidebar-hover); }
.session-item.active { background: var(--color-sidebar-active); }
.session-item.batch-selected { background: var(--color-primary-light); }

@media (max-width: 768px) {
  .session-item { padding: 12px; }
}

/* Batch checkbox */
.batch-check {
  width: 20px;
  height: 20px;
  border-radius: 4px;
  border: 2px solid var(--color-text-muted);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all 0.15s;
}
.batch-check.checked { background: var(--color-primary); border-color: var(--color-primary); }

.session-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.session-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (max-width: 768px) {
  .session-title { font-size: 15px; }
}

.session-time {
  font-size: 12px;
  color: var(--color-text-muted);
}

/* Rename input */
.rename-input {
  width: 100%;
  padding: 4px 8px;
  border: 1px solid var(--color-primary);
  border-radius: var(--radius-sm);
  font-size: 14px;
  font-family: var(--font-sans);
  color: var(--color-text);
  background: var(--color-card);
  outline: none;
}

/* Delete button */
.delete-btn {
  opacity: 0;
  background: none;
  border: none;
  cursor: pointer;
  color: var(--color-text-muted);
  padding: 6px;
  border-radius: 4px;
  transition: all 0.15s;
  flex-shrink: 0;
}
.session-item:hover .delete-btn { opacity: 1; }
.delete-btn:hover { color: var(--color-danger); background: rgba(244, 67, 54, 0.08); }

@media (max-width: 768px) {
  .delete-btn { opacity: 1; padding: 8px; }
}

/* ── Context menu ── */
.ctx-overlay {
  position: fixed;
  inset: 0;
  z-index: 10000;
  background: transparent;
}

.ctx-menu {
  position: fixed;
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  min-width: 160px;
  overflow: hidden;
  z-index: 10001;
}

.ctx-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  font-size: 14px;
  color: var(--color-text);
  cursor: pointer;
  transition: background 0.1s;
}
.ctx-item:hover { background: var(--color-bg); }

.ctx-icon { font-size: 15px; }
.ctx-danger { color: var(--color-danger); }

.ctx-divider {
  height: 1px;
  background: var(--color-border);
  margin: 0;
}
</style>
