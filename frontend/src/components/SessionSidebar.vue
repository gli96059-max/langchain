<script setup>
import { ref } from 'vue'
import { deleteSession } from '../api/index.js'

const props = defineProps({
  sessions: { type: Array, default: () => [] },
  activeId: { type: String, default: null },
  open: { type: Boolean, default: true },
  favorites: { type: Array, default: () => [] },
})

const emit = defineEmits(['select', 'new-session', 'close-sidebar', 'sessions-updated', 'show-library'])
const showFavs = ref(true)

async function handleDelete(sessionId, e) {
  e.stopPropagation()
  if (!confirm('确定删除该对话？')) return
  await deleteSession(sessionId)
  emit('sessions-updated')
}

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
        <span>私厨助手</span>
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
    </div>

    <div v-if="favorites.length" class="fav-section">
      <button class="fav-toggle" @click="showFavs = !showFavs">
        <span class="fav-toggle-icon" :class="{ open: showFavs }">▸</span>
        <span class="fav-toggle-label">我的收藏</span>
        <span class="fav-count">{{ favorites.length }}</span>
      </button>
      <div v-if="showFavs" class="fav-list">
        <div
          v-for="fav in favorites"
          :key="fav.id"
          class="fav-item"
        >
          <span class="fav-icon">❤️</span>
          <span class="fav-name">{{ fav.recipe_data?.name || fav.name }}</span>
        </div>
      </div>
    </div>

    <div class="session-list">
      <div
        v-for="s in sessions"
        :key="s.id"
        class="session-item"
        :class="{ active: s.id === activeId }"
        @click="emit('select', s.id)"
      >
        <div class="session-info">
          <span class="session-title">{{ s.title }}</span>
          <span class="session-time">{{ formatTime(s.updated_at) }}</span>
        </div>
        <button
          class="delete-btn"
          @click="(e) => handleDelete(s.id, e)"
          title="删除对话"
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M2 4h10M5 4V2.5A.5.5 0 015.5 2h3a.5.5 0 01.5.5V4M11 4v7.5a1 1 0 01-1 1H4a1 1 0 01-1-1V4" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </button>
      </div>
    </div>
  </aside>

  <!-- Mobile overlay -->
  <div v-if="open" class="overlay" @click="emit('close-sidebar')"></div>
</template>

<style scoped>
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
    z-index: 100;
    transform: translateX(-100%);
  }
  .sidebar.open {
    transform: translateX(0);
  }
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

.sidebar-header {
  padding: 16px;
  border-bottom: 1px solid var(--color-border);
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

.new-chat-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  width: 100%;
  padding: 10px;
  background: var(--color-primary);
  color: #fff;
  border: none;
  border-radius: var(--radius-sm);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
  font-family: var(--font-sans);
}

.new-chat-btn:hover {
  background: var(--color-primary-hover);
}

.library-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  width: 100%;
  padding: 10px;
  background: var(--color-card);
  color: var(--color-text);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  font-family: var(--font-sans);
  margin-top: 6px;
}

.library-btn:hover {
  background: var(--color-bg);
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.session-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background 0.15s;
  margin-bottom: 2px;
}

.session-item:hover {
  background: var(--color-sidebar-hover);
}

.session-item.active {
  background: var(--color-sidebar-active);
}

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

.session-time {
  font-size: 12px;
  color: var(--color-text-muted);
}

.delete-btn {
  opacity: 0;
  background: none;
  border: none;
  cursor: pointer;
  color: var(--color-text-muted);
  padding: 4px;
  border-radius: 4px;
  transition: all 0.15s;
  flex-shrink: 0;
}

.session-item:hover .delete-btn {
  opacity: 1;
}

.delete-btn:hover {
  color: var(--color-danger);
  background: rgba(244, 67, 54, 0.08);
}

/* Favorites section */
.fav-section {
  border-bottom: 1px solid var(--color-border);
  padding: 8px;
}

.fav-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  padding: 8px 10px;
  background: none;
  border: none;
  cursor: pointer;
  font-family: var(--font-sans);
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-secondary);
  border-radius: var(--radius-sm);
  transition: background 0.15s;
}

.fav-toggle:hover {
  background: var(--color-sidebar-hover);
}

.fav-toggle-icon {
  font-size: 10px;
  transition: transform 0.2s;
}

.fav-toggle-icon.open {
  transform: rotate(90deg);
}

.fav-toggle-label {
  flex: 1;
  text-align: left;
}

.fav-count {
  font-size: 11px;
  color: var(--color-text-muted);
  background: var(--color-bg);
  padding: 1px 7px;
  border-radius: 10px;
}

.fav-list {
  display: flex;
  flex-direction: column;
  gap: 1px;
  margin-top: 4px;
}

.fav-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px 6px 28px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background 0.15s;
  font-size: 13px;
  color: var(--color-text);
}

.fav-item:hover {
  background: var(--color-sidebar-hover);
}

.fav-icon {
  font-size: 12px;
  flex-shrink: 0;
}

.fav-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
