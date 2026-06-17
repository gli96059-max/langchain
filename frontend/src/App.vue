<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import SessionSidebar from './components/SessionSidebar.vue'
import ChatView from './components/ChatView.vue'
import DietaryProfile from './components/DietaryProfile.vue'
import RecipeLibrary from './components/RecipeLibrary.vue'
import ShoppingListPage from './components/ShoppingListPage.vue'
import LoginForm from './components/LoginForm.vue'
import { createSession, listSessions, getDietaryProfile, updateDietaryProfile, getSession, getToken } from './api/index.js'

const authenticated = ref(!!getToken())
const sessions = ref([])
const activeSessionId = ref(null)
const sidebarOpen = ref(false) // closed by default on mobile
const showDietary = ref(false)
const dietaryProfile = ref({ allergies: '', restrictions: '', preferences: '', difficulty_preference: '' })
const viewMode = ref('chat')

let unauthHandler = null

function handleAuthenticated() {
  authenticated.value = true
  loadSessions()
  loadDietaryProfile()
}

function handleUnauthorized() {
  authenticated.value = false
  activeSessionId.value = null
  sessions.value = []
  viewMode.value = 'chat'
}

async function loadSessions() {
  try {
    const all = await listSessions()
    sessions.value = all.filter(s => s.msg_count > 0)
    if (activeSessionId.value && !sessions.value.some(s => s.id === activeSessionId.value)) {
      activeSessionId.value = null
    }
  } catch {
    // If token invalid, the 401 handler will fire
  }
}

async function handleSelectSession(id) {
  activeSessionId.value = id
  sidebarOpen.value = false // close sidebar on mobile after selection
}

async function handleNewSession() {
  if (activeSessionId.value) {
    try {
      const data = await getSession(activeSessionId.value)
      if (data.messages && data.messages.length === 0) {
        sidebarOpen.value = false
        return
      }
    } catch { /* session invalid, proceed to create new */ }
  }
  const data = await createSession()
  activeSessionId.value = data.session.id
  sidebarOpen.value = false
}

async function loadDietaryProfile() {
  try {
    dietaryProfile.value = await getDietaryProfile()
  } catch { /* ignore */ }
}

async function handleSaveDietary(profile) {
  dietaryProfile.value = await updateDietaryProfile(profile.allergies, profile.restrictions, profile.preferences, profile.difficulty_preference)
  showDietary.value = false
}

function handleShowLibrary() {
  viewMode.value = 'library'
  sidebarOpen.value = false
}

function handleShowShoppingLists() {
  viewMode.value = 'shopping-lists'
  sidebarOpen.value = false
}

onMounted(async () => {
  if (authenticated.value) {
    await loadSessions()
    await loadDietaryProfile()
  }
  unauthHandler = () => handleUnauthorized()
  window.addEventListener('auth:unauthorized', unauthHandler)

  // iOS Safari height fix
  const setViewportHeight = () => {
    document.documentElement.style.setProperty('--vh', `${window.innerHeight * 0.01}px`)
  }
  setViewportHeight()
  window.addEventListener('resize', setViewportHeight)
})

onUnmounted(() => {
  if (unauthHandler) {
    window.removeEventListener('auth:unauthorized', unauthHandler)
  }
})
</script>

<template>
  <LoginForm
    v-if="!authenticated"
    @authenticated="handleAuthenticated"
  />
  <div v-else class="app-layout">
    <SessionSidebar
      :sessions="sessions"
      :active-id="activeSessionId"
      :open="sidebarOpen"
      @select="handleSelectSession"
      @new-session="handleNewSession"
      @close-sidebar="sidebarOpen = false"
      @sessions-updated="loadSessions"
      @show-library="handleShowLibrary"
      @show-shopping-lists="handleShowShoppingLists"
    />
    <!-- Overlay for mobile sidebar -->
    <div v-if="sidebarOpen" class="sidebar-overlay" @click="sidebarOpen = false"></div>

    <div class="main-area">
      <header class="top-bar">
        <div class="top-bar-left">
          <button class="menu-btn" @click="sidebarOpen = !sidebarOpen" aria-label="菜单">
            <span></span><span></span><span></span>
          </button>
          <div class="brand" v-if="activeSessionId">
            <span class="brand-text">小斐的专属私厨助手</span>
          </div>
        </div>
        <button v-if="activeSessionId" class="diet-btn" @click="showDietary = true" title="饮食档案" aria-label="饮食档案">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="3"/>
            <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
          </svg>
        </button>
      </header>
      <DietaryProfile
        :visible="showDietary"
        :profile="dietaryProfile"
        @close="showDietary = false"
        @save="handleSaveDietary"
      />
      <RecipeLibrary
        v-if="viewMode === 'library'"
        @close="viewMode = 'chat'"
      />
      <ShoppingListPage
        v-else-if="viewMode === 'shopping-lists'"
        @close="viewMode = 'chat'"
      />
      <ChatView
        v-else-if="activeSessionId"
        :session-id="activeSessionId"
        @message-completed="loadSessions"
      />
      <div v-else class="empty-state">
        <div class="empty-content">
          <span class="empty-icon">🍳</span>
          <h2>小斐的专属私厨助手</h2>
          <p class="greeting">小斐你好呀～ 今天想吃什么？告诉我食材或者上传照片，我来帮你做好吃的！</p>
          <button class="btn-primary" @click="handleNewSession">开始新对话</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.app-layout {
  display: flex;
  height: 100dvh;
  height: 100vh;
  overflow: hidden;
  position: relative;
}

.sidebar-overlay {
  display: none;
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.35);
  z-index: 90;
  animation: fadeIn 0.2s ease;
}

.main-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  padding-top: var(--safe-top, 0px);
}

.top-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  padding-top: max(12px, var(--safe-top, 0px));
  background: var(--color-card);
  border-bottom: 1px solid var(--color-border);
  z-index: 10;
  min-height: 52px;
}

.top-bar-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.menu-btn {
  display: none;
  flex-direction: column;
  gap: 5px;
  background: none;
  border: none;
  cursor: pointer;
  padding: 8px;
  min-width: 44px;
  min-height: 44px;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
}

.menu-btn:active {
  background: var(--color-primary-light);
}

.menu-btn span {
  display: block;
  width: 22px;
  height: 2.5px;
  background: var(--color-text);
  border-radius: 2px;
}

.diet-btn {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--color-text-secondary);
  padding: 10px;
  min-width: 44px;
  min-height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  transition: all 0.2s;
}

.diet-btn:active {
  background: var(--color-primary-light);
  color: var(--color-primary);
}

.brand {
  display: flex;
  align-items: center;
  gap: 8px;
}

.brand-text {
  font-size: 17px;
  font-weight: 600;
  color: var(--color-text);
}

@media (max-width: 768px) {
  .menu-btn {
    display: flex;
  }
  .sidebar-overlay {
    display: block;
  }
  .brand-text {
    font-size: 15px;
  }
  .top-bar {
    padding: 8px 12px;
    min-height: 48px;
  }
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.empty-state {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding-bottom: 60px;
}

.empty-content {
  text-align: center;
  max-width: 340px;
  padding: 40px 24px;
}

.empty-icon {
  font-size: 64px;
  display: block;
  margin-bottom: 16px;
}

.empty-content h2 {
  font-size: 26px;
  color: var(--color-text);
  margin-bottom: 12px;
}

.empty-content p {
  color: var(--color-text-secondary);
  font-size: 16px;
  line-height: 1.7;
  margin-bottom: 28px;
}

.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 14px 32px;
  background: var(--color-primary);
  color: #fff;
  border: none;
  border-radius: var(--radius-md);
  font-size: 16px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
  font-family: var(--font-sans);
  min-height: 48px;
  -webkit-tap-highlight-color: transparent;
}

.btn-primary:active {
  background: var(--color-primary-hover);
  transform: scale(0.97);
}
</style>
