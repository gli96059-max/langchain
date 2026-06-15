<script setup>
import { ref, onMounted } from 'vue'
import SessionSidebar from './components/SessionSidebar.vue'
import ChatView from './components/ChatView.vue'
import DietaryProfile from './components/DietaryProfile.vue'
import RecipeLibrary from './components/RecipeLibrary.vue'
import { createSession, listSessions, listFavorites, addFavorite, removeFavorite, getDietaryProfile, updateDietaryProfile } from './api/index.js'

const sessions = ref([])
const activeSessionId = ref(null)
const sidebarOpen = ref(true)
const favorites = ref([])
const showDietary = ref(false)
const dietaryProfile = ref({ allergies: '', restrictions: '', preferences: '' })
const viewMode = ref('chat')

async function loadSessions() {
  sessions.value = await listSessions()
}

async function loadFavorites() {
  favorites.value = await listFavorites()
}

async function handleSelectSession(id) {
  activeSessionId.value = id
  if (window.innerWidth < 768) sidebarOpen.value = false
}

async function handleNewSession() {
  const data = await createSession()
  sessions.value.unshift(data.session)
  activeSessionId.value = data.session.id
  if (window.innerWidth < 768) sidebarOpen.value = false
}

async function handleFavorite(recipe) {
  await addFavorite(recipe.name, recipe)
  await loadFavorites()
}

async function handleUnfavorite(recipe) {
  const fav = favorites.value.find(f => f.recipe_data?.name === recipe.name)
  if (fav) {
    await removeFavorite(fav.id)
    await loadFavorites()
  }
}

async function loadDietaryProfile() {
  dietaryProfile.value = await getDietaryProfile()
}

async function handleSaveDietary(profile) {
  dietaryProfile.value = await updateDietaryProfile(profile.allergies, profile.restrictions, profile.preferences)
  showDietary.value = false
}

function handleShowLibrary() {
  viewMode.value = 'library'
  if (window.innerWidth < 768) sidebarOpen.value = false
}

onMounted(async () => {
  await handleNewSession()
  await loadFavorites()
  await loadDietaryProfile()
})
</script>

<template>
  <div class="app-layout">
    <SessionSidebar
      :sessions="sessions"
      :active-id="activeSessionId"
      :open="sidebarOpen"
      :favorites="favorites"
      @select="handleSelectSession"
      @new-session="handleNewSession"
      @close-sidebar="sidebarOpen = false"
      @sessions-updated="loadSessions"
      @show-library="handleShowLibrary"
    />
    <div class="main-area">
      <header class="top-bar">
        <div class="top-bar-left">
          <button class="menu-btn" @click="sidebarOpen = !sidebarOpen">
            <span></span><span></span><span></span>
          </button>
          <div class="brand" v-if="activeSessionId">
            <span class="brand-icon">🍳</span>
            <span class="brand-text">AI 私厨助手</span>
          </div>
        </div>
        <button v-if="activeSessionId" class="diet-btn" @click="showDietary = true" title="饮食档案">
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
      <ChatView
        v-else-if="activeSessionId"
        :session-id="activeSessionId"
        :favorites="favorites"
        @message-completed="loadSessions"
        @favorite="handleFavorite"
        @unfavorite="handleUnfavorite"
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
  justify-content: space-between;
  padding: 12px 20px;
  background: var(--color-card);
  border-bottom: 1px solid var(--color-border);
  z-index: 10;
}

.top-bar-left {
  display: flex;
  align-items: center;
  gap: 12px;
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

.diet-btn {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--color-text-secondary);
  padding: 6px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.diet-btn:hover {
  background: var(--color-primary-light);
  color: var(--color-primary);
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
