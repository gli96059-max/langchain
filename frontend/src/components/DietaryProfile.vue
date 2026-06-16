<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  visible: { type: Boolean, default: false },
  profile: { type: Object, default: () => ({ allergies: '', restrictions: '', preferences: '' }) },
})
const emit = defineEmits(['close', 'save'])

const form = ref({ allergies: '', restrictions: '', preferences: '' })

watch(() => props.visible, (v) => {
  if (v) form.value = { ...props.profile }
}, { immediate: true })

function save() {
  emit('save', { ...form.value })
}
</script>

<template>
  <Teleport to="body">
    <div v-if="visible" class="modal-overlay" @click.self="emit('close')">
      <div class="modal-panel">
        <div class="modal-header">
          <h3>🍽️ 饮食档案</h3>
          <button class="close-btn" @click="emit('close')">✕</button>
        </div>
        <div class="modal-body">
          <div class="field-group">
            <label>过敏源</label>
            <textarea
              v-model="form.allergies"
              placeholder="例如: 花生、海鲜、牛奶..."
              rows="2"
            ></textarea>
            <span class="field-hint">注意避开这些食材</span>
          </div>
          <div class="field-group">
            <label>饮食限制</label>
            <textarea
              v-model="form.restrictions"
              placeholder="例如: 素食、纯素、低卡、高蛋白、无麸质..."
              rows="2"
            ></textarea>
            <span class="field-hint">遵守这些饮食方式</span>
          </div>
          <div class="field-group">
            <label>口味偏好</label>
            <textarea
              v-model="form.preferences"
              placeholder="例如: 少油、少盐、少糖、微辣、清淡..."
              rows="2"
            ></textarea>
            <span class="field-hint">推荐菜谱时优先考虑</span>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-cancel" @click="emit('close')">取消</button>
          <button class="btn-save" @click="save">保存</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-panel {
  background: var(--color-card);
  border-radius: var(--radius-lg);
  width: 440px;
  max-width: 90vw;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
  overflow: hidden;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 22px;
  border-bottom: 1px solid var(--color-border);
}

.modal-header h3 {
  margin: 0;
  font-size: 17px;
  font-weight: 600;
  color: var(--color-text);
}

.close-btn {
  background: none;
  border: none;
  font-size: 18px;
  cursor: pointer;
  color: var(--color-text-muted);
  padding: 4px;
  line-height: 1;
}

.close-btn:hover {
  color: var(--color-text);
}

.modal-body {
  padding: 20px 22px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.field-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field-group label {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text);
}

.field-group textarea {
  padding: 10px 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  font-size: 14px;
  color: var(--color-text);
  background: var(--color-bg);
  resize: vertical;
  font-family: var(--font-sans);
  line-height: 1.5;
}

.field-group textarea:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 2px rgba(232, 115, 74, 0.15);
}

.field-hint {
  font-size: 11px;
  color: var(--color-text-muted);
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 14px 22px;
  border-top: 1px solid var(--color-border);
}

.btn-cancel {
  padding: 8px 20px;
  border: 1px solid var(--color-border);
  background: var(--color-card);
  color: var(--color-text);
  border-radius: var(--radius-sm);
  font-size: 14px;
  cursor: pointer;
  font-family: var(--font-sans);
}

.btn-cancel:hover {
  background: var(--color-bg);
}

.btn-save {
  padding: 8px 20px;
  border: none;
  background: var(--color-primary);
  color: #fff;
  border-radius: var(--radius-sm);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  font-family: var(--font-sans);
}

@media (max-width: 768px) {
  .modal-panel {
    width: 100vw;
    max-width: 100vw;
    max-height: 90vh;
    border-radius: var(--radius-lg) var(--radius-lg) 0 0;
    margin-top: auto;
  }
  .modal-overlay {
    align-items: flex-end;
  }
  .modal-header {
    padding: 16px 18px;
  }
  .modal-body {
    padding: 16px 18px;
    padding-bottom: calc(16px + env(safe-area-inset-bottom, 0px));
  }
  .modal-footer {
    padding: 12px 18px;
    padding-bottom: calc(12px + env(safe-area-inset-bottom, 0px));
  }
  .field-group textarea {
    font-size: 16px;
    padding: 12px;
  }
  .btn-cancel, .btn-save {
    flex: 1;
    text-align: center;
    padding: 12px 16px;
  }
}
</style>
