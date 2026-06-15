<script setup>
import { ref, onMounted } from 'vue'
import SessionSidebar from './components/SessionSidebar.vue'
import ChatView from './components/ChatView.vue'
import { createSession, listSessions, getSession } from './api/index.js'

const sessions = ref([])
const activeSessionId = ref(null)
const sessionMessages = ref([])
const sidebarOpen = ref(true)

async function loadSessions() {
  sessions.value = await listSessions()
}

async function handleSelectSession(id) {
  activeSessionId.value = id
  const data = await getSession(id)
  sessionMessages.value = data.messages || []
  if (window.innerWidth < 768) sidebarOpen.value = false
}

async function handleNewSession() {
  const data = await createSession()
  sessions.value.unshift(data.session)
  await handleSelectSession(data.session.id)
}

function handleMessagesUpdated(messages) {
  sessionMessages.value = messages
}

onMounted(async () => {
  await loadSessions()
  if (sessions.value.length > 0) {
    await handleSelectSession(sessions.value[0].id)
  }
})
</script>

<template>
  <div class="app-layout">
    <SessionSidebar
      :sessions="sessions"
      :active-id="activeSessionId"
      :open="sidebarOpen"
      @select="handleSelectSession"
      @new-session="handleNewSession"
      @close-sidebar="sidebarOpen = false"
      @sessions-updated="loadSessions"
    />
    <div class="main-area">
      <header class="top-bar">
        <button class="menu-btn" @click="sidebarOpen = !sidebarOpen">
          <span></span><span></span><span></span>
        </button>
        <div class="brand" v-if="activeSessionId">
          <span class="brand-icon">🍳</span>
          <span class="brand-text">AI 私厨助手</span>
        </div>
      </header>
      <ChatView
        v-if="activeSessionId"
        :key="activeSessionId"
        :session-id="activeSessionId"
        :initial-messages="sessionMessages"
        @messages-updated="handleMessagesUpdated"
      />
      <div v-else class="empty-state">
        <div class="empty-content">
          <span class="empty-icon">🍳</span>
          <h2>AI 私厨助手</h2>
          <p>上传食材照片或输入食材清单，AI 为你推荐美味菜谱</p>
          <button class="btn-primary" @click="handleNewSession">开始新对话</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.app-layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

.main-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.top-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 20px;
  background: var(--color-card);
  border-bottom: 1px solid var(--color-border);
  z-index: 10;
}

.menu-btn {
  display: none;
  flex-direction: column;
  gap: 4px;
  background: none;
  border: none;
  cursor: pointer;
  padding: 4px;
}

.menu-btn span {
  display: block;
  width: 20px;
  height: 2px;
  background: var(--color-text);
  border-radius: 2px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 8px;
}

.brand-icon {
  font-size: 24px;
}

.brand-text {
  font-size: 18px;
  font-weight: 600;
  color: var(--color-text);
}

@media (max-width: 768px) {
  .menu-btn {
    display: flex;
  }
}

.empty-state {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.empty-content {
  text-align: center;
  max-width: 400px;
  padding: 40px 20px;
}

.empty-icon {
  font-size: 64px;
  display: block;
  margin-bottom: 20px;
}

.empty-content h2 {
  font-size: 28px;
  color: var(--color-text);
  margin-bottom: 12px;
}

.empty-content p {
  color: var(--color-text-secondary);
  font-size: 16px;
  margin-bottom: 28px;
}

.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 28px;
  background: var(--color-primary);
  color: #fff;
  border: none;
  border-radius: var(--radius-md);
  font-size: 16px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
  font-family: var(--font-sans);
}

.btn-primary:hover {
  background: var(--color-primary-hover);
}
</style>
