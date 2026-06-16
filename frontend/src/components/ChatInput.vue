<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  disabled: { type: Boolean, default: false },
})

const emit = defineEmits(['send'])

const text = ref('')
const imageBase64 = ref(null)
const imagePreview = ref(null)
const fileInput = ref(null)

const MAX_DIM = 1024

const isMobile = ref(false)
function checkMobile() {
  isMobile.value = window.innerWidth < 768
}

onMounted(() => {
  checkMobile()
  window.addEventListener('resize', checkMobile)
})
onUnmounted(() => window.removeEventListener('resize', checkMobile))

function resizeImage(file) {
  return new Promise((resolve) => {
    const img = new Image()
    img.onload = () => {
      let { width, height } = img
      if (width > MAX_DIM || height > MAX_DIM) {
        if (width > height) {
          height = Math.round((height / width) * MAX_DIM)
          width = MAX_DIM
        } else {
          width = Math.round((width / height) * MAX_DIM)
          height = MAX_DIM
        }
      }
      const canvas = document.createElement('canvas')
      canvas.width = width
      canvas.height = height
      const ctx = canvas.getContext('2d')
      ctx.drawImage(img, 0, 0, width, height)
      resolve(canvas.toDataURL('image/jpeg', 0.85))
    }
    img.src = URL.createObjectURL(file)
  })
}

function handleFileSelect(e) {
  const file = e.target.files?.[0]
  if (!file) return
  if (!file.type.startsWith('image/')) {
    alert('请选择图片文件')
    return
  }
  resizeImage(file).then(dataUrl => {
    imageBase64.value = dataUrl.split(',')[1] || dataUrl
    imagePreview.value = dataUrl
  })
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

@media (max-width: 768px) {
  .chat-input-area {
    padding: 10px 10px;
    padding-bottom: calc(10px + env(safe-area-inset-bottom, 0px));
  }
  .input-row {
    padding: 6px 6px 6px 10px;
    gap: 6px;
  }
  .action-btn {
    width: 40px;
    height: 40px;
  }
  .action-btn svg {
    width: 20px;
    height: 20px;
  }
  .text-input {
    font-size: 16px;
    padding: 6px 0;
  }
  .image-preview img {
    height: 64px;
  }
}
</style>
