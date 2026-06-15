<script setup>
import { ref } from 'vue'

const props = defineProps({
  disabled: { type: Boolean, default: false },
})

const emit = defineEmits(['send'])

const text = ref('')
const imageBase64 = ref(null)
const imagePreview = ref(null)
const fileInput = ref(null)

function handleFileSelect(e) {
  const file = e.target.files?.[0]
  if (!file) return
  if (!file.type.startsWith('image/')) {
    alert('请选择图片文件')
    return
  }
  const reader = new FileReader()
  reader.onload = () => {
    const result = reader.result
    imageBase64.value = result.split(',')[1] || result
    imagePreview.value = result
  }
  reader.readAsDataURL(file)
  e.target.value = ''
}

function removeImage() {
  imageBase64.value = null
  imagePreview.value = null
}

function handleSubmit() {
  if (props.disabled) return
  if (!text.value.trim() && !imageBase64.value) return

  emit('send', { text: text.value, imageBase64: imageBase64.value })
  text.value = ''
  removeImage()
}

function handleKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSubmit()
  }
}
</script>

<template>
  <div class="chat-input-area">
    <div class="input-container">
      <!-- Image preview -->
      <div v-if="imagePreview" class="image-preview">
        <img :src="imagePreview" alt="食材图片" />
        <button class="remove-img" @click="removeImage">&times;</button>
      </div>

      <div class="input-row">
        <button
          class="action-btn upload-btn"
          :disabled="disabled"
          @click="fileInput?.click()"
          title="上传食材图片"
        >
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
            <circle cx="8.5" cy="8.5" r="1.5"/>
            <polyline points="21 15 16 10 5 21"/>
          </svg>
        </button>
        <input
          ref="fileInput"
          type="file"
          accept="image/*"
          style="display:none"
          @change="handleFileSelect"
        />

        <textarea
          v-model="text"
          :placeholder="imagePreview ? '描述一下食材...' : '输入食材清单或上传食材照片...'"
          :disabled="disabled"
          class="text-input"
          rows="1"
          @keydown="handleKeydown"
          @input="$el?.style && ($el.style.height = 'auto')"
        ></textarea>

        <button
          class="action-btn send-btn"
          :disabled="disabled || (!text.trim() && !imageBase64)"
          @click="handleSubmit"
          title="发送"
        >
          <svg v-if="!disabled" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="22" y1="2" x2="11" y2="13"/>
            <polygon points="22 2 15 22 11 13 2 9 22 2"/>
          </svg>
          <span v-else class="spinner"></span>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.chat-input-area {
  border-top: 1px solid var(--color-border);
  background: var(--color-card);
  padding: 16px 20px;
}

.input-container {
  max-width: 760px;
  margin: 0 auto;
}

.image-preview {
  position: relative;
  display: inline-block;
  margin-bottom: 8px;
}

.image-preview img {
  height: 80px;
  width: auto;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
  object-fit: cover;
}

.remove-img {
  position: absolute;
  top: -6px;
  right: -6px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--color-danger);
  color: #fff;
  border: none;
  font-size: 14px;
  line-height: 1;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.input-row {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 8px 8px 8px 12px;
  transition: border-color 0.2s;
}

.input-row:focus-within {
  border-color: var(--color-primary);
}

.text-input {
  flex: 1;
  border: none;
  background: transparent;
  font-size: 15px;
  color: var(--color-text);
  outline: none;
  resize: none;
  font-family: var(--font-sans);
  line-height: 1.5;
  max-height: 120px;
}

.text-input::placeholder {
  color: var(--color-text-muted);
}

.action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: none;
  border-radius: 50%;
  cursor: pointer;
  transition: all 0.2s;
  flex-shrink: 0;
  background: transparent;
  color: var(--color-text-secondary);
}

.action-btn:hover:not(:disabled) {
  background: var(--color-border);
  color: var(--color-text);
}

.send-btn {
  background: var(--color-primary);
  color: #fff;
}

.send-btn:hover:not(:disabled) {
  background: var(--color-primary-hover);
}

.send-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.spinner {
  display: block;
  width: 18px;
  height: 18px;
  border: 2px solid #fff;
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
