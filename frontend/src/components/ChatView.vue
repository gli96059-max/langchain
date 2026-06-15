<script setup>
import { ref, nextTick, watch } from 'vue'
import { chatStream, readSSE, getSession } from '../api/index.js'
import RecipeCard from './RecipeCard.vue'
import ChatInput from './ChatInput.vue'

const props = defineProps({
  sessionId: { type: String, required: true },
  initialMessages: { type: Array, default: () => [] },
})

const emit = defineEmits(['messages-updated'])

const messages = ref([...props.initialMessages])
const isStreaming = ref(false)
const statusMsg = ref('')
const statusStep = ref('')
const messagesEnd = ref(null)

watch(() => props.sessionId, async () => {
  const data = await getSession(props.sessionId)
  messages.value = data.messages || []
  statusMsg.value = ''
  statusStep.value = ''
  await nextTick()
  scrollToBottom()
})

async function handleSend({ text, imageBase64 }) {
  if (!text.trim() && !imageBase64) return
  if (isStreaming.value) return

  messages.value.push({ role: 'user', content: text, image_url: null })
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

    // Decide what to show:
    // - If recipes detected → show cards only (clean & visual)
    // - If no recipes → show text response
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
    messages.value.push({ role: 'assistant', content: `❌ 请求失败: ${err.message}` })
  } finally {
    isStreaming.value = false
    statusMsg.value = ''
    statusStep.value = ''

    const data = await getSession(props.sessionId)
    emit('messages-updated', data.messages || [])
    scrollToBottom()
  }
}

function scrollToBottom() {
  nextTick(() => {
    messagesEnd.value?.scrollIntoView({ behavior: 'smooth' })
  })
}
</script>

<template>
  <div class="chat-view">
    <div class="messages-area">
      <div class="messages-container">
        <template v-for="(msg, idx) in messages" :key="idx">
          <!-- User message -->
          <div v-if="msg.role === 'user'" class="message-row user-row">
            <div class="message-bubble user-bubble">
              <p>{{ msg.content }}</p>
              <span v-if="msg.image_url" class="img-badge">📷 已上传图片</span>
            </div>
          </div>

          <!-- Assistant text message -->
          <div v-else-if="msg.role === 'assistant'" class="message-row assistant-row">
            <div class="assistant-avatar">🍳</div>
            <div class="message-bubble assistant-bubble">
              <p style="white-space: pre-wrap;">{{ msg.content }}</p>
            </div>
          </div>

          <!-- Recipe cards -->
          <div v-else-if="msg.role === 'assistant_recipes'" class="message-row assistant-row">
            <div class="assistant-avatar">🍳</div>
            <div class="recipes-wrapper">
              <RecipeCard
                v-for="(recipe, ri) in msg.recipes"
                :key="ri"
                :recipe="recipe"
              />
              <div v-if="msg.summary" class="summary-text">
                <strong>💡 总结：</strong>{{ msg.summary }}
              </div>
            </div>
          </div>
        </template>

        <!-- Streaming status -->
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
}

.messages-area {
  flex: 1;
  overflow-y: auto;
  padding: 20px 0;
}

.messages-container {
  max-width: 760px;
  margin: 0 auto;
  padding: 0 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.message-row {
  display: flex;
  gap: 12px;
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
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: var(--color-primary-light);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  flex-shrink: 0;
}

.message-bubble {
  max-width: 85%;
  padding: 12px 16px;
  border-radius: var(--radius-md);
  font-size: 15px;
  line-height: 1.6;
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
}

.summary-text {
  background: var(--color-primary-light);
  padding: 14px 18px;
  border-radius: var(--radius-md);
  font-size: 14px;
  line-height: 1.6;
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
    padding: 0 12px;
  }
  .message-bubble {
    max-width: 90%;
    font-size: 14px;
  }
}
</style>
