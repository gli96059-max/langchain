<script setup>
import { computed } from 'vue'

const props = defineProps({
  visible: { type: Boolean, default: false },
  recipes: { type: Array, default: () => [] },
})
const emit = defineEmits(['close'])

const allIngredients = computed(() => {
  const seen = new Set()
  const list = []
  for (const r of props.recipes) {
    if (!r.ingredients) continue
    for (const ing of r.ingredients) {
      const key = ing.trim().toLowerCase()
      if (!seen.has(key)) {
        seen.add(key)
        list.push({ text: ing, recipe: r.name })
      }
    }
  }
  return list
})

function copyList() {
  const text = allIngredients.value.map(i => `□ ${i.text}`).join('\n')
  navigator.clipboard.writeText(text)
}
</script>

<template>
  <Teleport to="body">
    <div v-if="visible" class="modal-overlay" @click.self="emit('close')">
      <div class="modal-panel">
        <div class="modal-header">
          <h3>🛒 购物清单</h3>
          <button class="close-btn" @click="emit('close')">✕</button>
        </div>
        <div class="modal-body">
          <p v-if="!allIngredients.length" class="empty-hint">暂无食材信息</p>
          <div v-else class="ing-list">
            <div v-for="(item, i) in allIngredients" :key="i" class="ing-item">
              <span class="ing-check">□</span>
              <span class="ing-text">{{ item.text }}</span>
              <span class="ing-source">{{ item.recipe }}</span>
            </div>
          </div>
          <div class="ing-count">共 {{ allIngredients.length }} 种食材</div>
        </div>
        <div class="modal-footer">
          <button class="btn-copy" @click="copyList">复制清单</button>
          <button class="btn-close" @click="emit('close')">关闭</button>
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
  width: 480px;
  max-width: 90vw;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
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

.modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px 22px;
}

.empty-hint {
  color: var(--color-text-muted);
  text-align: center;
  padding: 20px 0;
}

.ing-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.ing-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 8px;
  border-radius: var(--radius-sm);
  transition: background 0.15s;
}

.ing-item:hover {
  background: var(--color-bg);
}

.ing-check {
  font-size: 16px;
  color: var(--color-text-muted);
  flex-shrink: 0;
}

.ing-text {
  flex: 1;
  font-size: 14px;
  color: var(--color-text);
}

.ing-source {
  font-size: 11px;
  color: var(--color-text-muted);
  background: var(--color-bg);
  padding: 2px 8px;
  border-radius: 10px;
  white-space: nowrap;
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.ing-count {
  text-align: center;
  font-size: 12px;
  color: var(--color-text-muted);
  padding-top: 12px;
  margin-top: 8px;
  border-top: 1px solid var(--color-border);
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 14px 22px;
  border-top: 1px solid var(--color-border);
}

.btn-copy {
  padding: 8px 20px;
  border: 1px solid var(--color-border);
  background: var(--color-card);
  color: var(--color-text);
  border-radius: var(--radius-sm);
  font-size: 14px;
  cursor: pointer;
  font-family: var(--font-sans);
}

.btn-copy:hover {
  background: var(--color-bg);
}

.btn-close {
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

.btn-close:hover {
  background: var(--color-primary-hover);
}
</style>
