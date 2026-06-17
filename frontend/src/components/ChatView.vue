<script setup>
import { ref, nextTick, watch, computed } from 'vue'
import { chatStream, readSSE, getSession } from '../api/index.js'
import RecipeCard from './RecipeCard.vue'
import ChatInput from './ChatInput.vue'
import ShoppingList from './ShoppingList.vue'

const props = defineProps({
  sessionId: { type: String, required: true },
})
const emit = defineEmits(['message-completed'])

const messages = ref([])
const isStreaming = ref(false)
const statusMsg = ref('')
const statusStep = ref('')
const messagesArea = ref(null)
const messagesEnd = ref(null)
const showShoppingList = ref(false)
const savedRecipeNames = ref(new Set())

const allRecipes = computed(() => {
  const list = []
  for (const msg of messages.value) {
    if (msg.role === 'assistant_recipes' && msg.recipes) {
      list.push(...msg.recipes)
    }
  }
  return list
})

watch(() => props.sessionId, async () => {
  const data = await getSession(props.sessionId)
  messages.value = (data.messages || []).map(m => {
    if (m.role === 'assistant_recipes') {
      try {
        const parsed = JSON.parse(m.content)
        return { role: 'assistant_recipes', recipes: parsed.recipes || [], summary: parsed.summary || '' }
      } catch { return m }
    }
    return m
  })
  statusMsg.value = ''
  statusStep.value = ''
  await nextTick()
  scrollToBottom()
}, { immediate: true })

async function handleSend({ text, imageBase64 }) {
  if (!text.trim() && !imageBase64) return
  if (isStreaming.value) return

  messages.value.push({
    role: 'user',
    content: text,
    image_url: imageBase64 ? `data:image/png;base64,${imageBase64}` : null,
  })
  isStreaming.value = true
  statusMsg.value = '⏳ 思考中...'
  statusStep.value = 'thinking'
  scrollToBottom()

  try {
    const response = await chatStream(props.sessionId, text, imageBase64)

    let pendingResponse = ''
    let pendingResult = null

    for await (const { event, data } of readSSE(response)) {
      if (event === 'status') {
        statusMsg.value = data.message || ''
        statusStep.value = data.step || ''
      } else if (event === 'response') {
        pendingResponse = data.text || ''
        statusStep.value = 'response'
      } else if (event === 'result') {
        pendingResult = data
        statusStep.value = 'done'
      } else if (event === 'error') {
        messages.value.push({ role: 'assistant', content: `❌ ${data.message}` })
        statusStep.value = 'error'
      }
      scrollToBottom()
    }

    if (pendingResult) {
      messages.value.push({
        role: 'assistant_recipes',
        recipes: pendingResult.recipes || [],
        summary: pendingResult.summary || '',
      })
    } else if (pendingResponse) {
      messages.value.push({ role: 'assistant', content: pendingResponse })
    }
  } catch (err) {
    console.error('[ChatView] SSE error:', err)
    messages.value.push({ role: 'assistant', content: `❌ 请求失败: ${err.message}` })
  } finally {
    isStreaming.value = false
    statusMsg.value = ''
    statusStep.value = ''
    scrollToBottom()
    emit('message-completed')
  }
}

function handleRecipeSave(recipe) {
  savedRecipeNames.value.add(recipe.name)
  savedRecipeNames.value = new Set(savedRecipeNames.value)
}

function isSaved(recipe) {
  return savedRecipeNames.value.has(recipe.name)
}

function scrollToBottom() {
  nextTick(() => {
    messagesEnd.value?.scrollIntoView({ behavior: 'smooth' })
  })
}
</script>

<template>
  <div class="chat-view">
    <div class="messages-area" ref="messagesArea">
      <div class="messages-container">
        <template v-for="(msg, idx) in messages" :key="idx">
          <div v-if="msg.role === 'user'" class="message-row user-row">
            <div class="message-bubble user-bubble">
              <img v-if="msg.image_url" :src="msg.image_url" class="user-image" />
              <p v-if="msg.content">{{ msg.content }}</p>
              <span v-if="msg.image_url && !msg.content" class="img-badge">📷 食材图片</span>
            </div>
          </div>

          <div v-else-if="msg.role === 'assistant'" class="message-row assistant-row">
            <div class="assistant-avatar">🍳</div>
            <div class="message-bubble assistant-bubble">
              <p style="white-space: pre-wrap;">{{ msg.content }}</p>
            </div>
          </div>

          <div v-else-if="msg.role === 'assistant_recipes'" class="message-row assistant-row">
            <div class="assistant-avatar">🍳</div>
            <div class="recipes-wrapper">
              <RecipeCard
                v-for="(recipe, ri) in msg.recipes"
                :key="ri"
                :recipe="recipe"
                :show-save="true"
                :saved="isSaved(recipe)"
                :session-id="props.sessionId"
                @save="handleRecipeSave"
              />
              <div v-if="msg.summary" class="summary-text">
                <strong>💡 总结：</strong>{{ msg.summary }}
              </div>
            </div>
          </div>
        </template>

        <div v-if="allRecipes.length" class="shopping-bar">
          <button class="shopping-btn" @click="showShoppingList = true">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/>
              <path d="M1 1h4l2.68 13.39a2 2 0 002 1.61h9.72a2 2 0 002-1.61L23 6H6"/>
            </svg>
            一键购物清单（{{ allRecipes.length }} 道菜）
          </button>
          <ShoppingList
            :visible="showShoppingList"
            :recipes="allRecipes"
            @close="showShoppingList = false"
          />
        </div>

        <div v-if="isStreaming" class="message-row assistant-row">
          <div class="assistant-avatar">🍳</div>
          <div class="status-indicator" :class="statusStep">
            <div class="status-dot"></div>
            <span>{{ statusMsg }}</span>
          </div>
        </div>

        <div ref="messagesEnd"></div>
      </div>
    </div>

    <ChatInput
      :disabled="isStreaming"
      @send="handleSend"
    />
  </div>
</template>

<style scoped>
.chat-view {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.messages-area {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  -webkit-overflow-scrolling: touch;
  overscroll-behavior: contain;
  padding: 16px 0;
}

.messages-container {
  max-width: 760px;
  margin: 0 auto;
  padding: 0 16px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.message-row {
  display: flex;
  gap: 10px;
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.user-row {
  justify-content: flex-end;
}

.assistant-avatar {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: var(--color-primary-light);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 17px;
  flex-shrink: 0;
  margin-top: 2px;
}

.message-bubble {
  max-width: 85%;
  padding: 12px 16px;
  border-radius: var(--radius-md);
  font-size: 15px;
  line-height: 1.65;
}

.user-bubble {
  background: var(--color-primary);
  color: #fff;
  border-bottom-right-radius: 4px;
}

.assistant-bubble {
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-bottom-left-radius: 4px;
}

.user-image {
  display: block;
  max-width: 200px;
  max-height: 160px;
  width: auto;
  height: auto;
  border-radius: var(--radius-sm);
  margin-bottom: 6px;
  object-fit: contain;
  background: rgba(0,0,0,0.04);
}

.img-badge {
  display: inline-block;
  margin-top: 6px;
  font-size: 12px;
  opacity: 0.8;
}

.recipes-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 0;
}

.shopping-bar {
  display: flex;
  justify-content: center;
}

.shopping-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 12px 20px;
  background: var(--color-primary-light);
  color: var(--color-primary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  font-family: var(--font-sans);
  min-height: 44px;
  -webkit-tap-highlight-color: transparent;
}

.shopping-btn:active {
  background: var(--color-primary);
  color: #fff;
}

.summary-text {
  background: var(--color-primary-light);
  padding: 14px 18px;
  border-radius: var(--radius-md);
  font-size: 14px;
  line-height: 1.65;
  color: var(--color-text);
  border: 1px solid var(--color-border);
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: 14px;
  color: var(--color-text-secondary);
  border-bottom-left-radius: 4px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-primary);
  animation: pulse 1.5s ease-in-out infinite;
}

.status-indicator.done .status-dot {
  background: var(--color-success);
  animation: none;
}

.status-indicator.response .status-dot {
  background: var(--color-warning);
}

.status-indicator.error .status-dot {
  background: var(--color-danger);
  animation: none;
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(0.8); }
}

@media (max-width: 768px) {
  .messages-container {
    padding: 0 10px;
    gap: 12px;
  }
  .message-bubble {
    max-width: 92%;
    font-size: 14px;
    padding: 10px 14px;
  }
  .messages-area {
    padding: 10px 0;
  }
  .assistant-avatar {
    width: 30px;
    height: 30px;
    font-size: 15px;
  }
  .user-image {
    max-width: 160px;
    max-height: 130px;
  }
  .shopping-btn {
    width: 100%;
    justify-content: center;
    font-size: 14px;
  }
  .summary-text {
    font-size: 13px;
    padding: 12px 14px;
  }
  .status-indicator {
    font-size: 13px;
    padding: 8px 12px;
  }
}
</style>
