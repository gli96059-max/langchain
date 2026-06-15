<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  visible: { type: Boolean, default: false },
  recipe: { type: Object, default: null },
})
const emit = defineEmits(['close'])

const currentStep = ref(0)

const steps = computed(() => props.recipe?.steps || [])
const totalSteps = computed(() => steps.value.length)

const ACTION_EMOJIS = [
  ['切|剁|切片|切块|切丁|切丝', '🔪'],
  ['炒|翻炒|爆炒', '🔥'],
  ['煎|炸|油煎|油炸', '🍳'],
  ['煮|焯|汆|烫', '💧'],
  ['蒸', '♨️'],
  ['烤|烘|焗', '🔥'],
  ['炖|焖|煲|卤', '🫕'],
  ['拌|搅拌|搅匀|混合', '🥢'],
]

function enhanceStep(text) {
  const parts = { text, heat: null, time: null, action: null }
  const heatMatch = text.match(/([小中大])火/)
  if (heatMatch) parts.heat = heatMatch[1]
  const timeMatch = text.match(/(\d+)\s*[分钟分秒]/)
  if (timeMatch) parts.time = timeMatch[0]
  for (const [pattern, emoji] of ACTION_EMOJIS) {
    if (new RegExp(pattern).test(text)) { parts.action = emoji; break }
  }
  return parts
}

function next() {
  if (currentStep.value < totalSteps.value - 1) currentStep.value++
}

function prev() {
  if (currentStep.value > 0) currentStep.value--
}

function close() {
  currentStep.value = 0
  emit('close')
}
</script>

<template>
  <Teleport to="body">
    <div v-if="visible && recipe" class="reader-overlay" @click.self="close">
      <div class="reader-header">
        <button class="reader-close" @click="close">✕</button>
        <div class="reader-title">{{ recipe.name }}</div>
        <div class="reader-progress">{{ currentStep + 1 }} / {{ totalSteps }}</div>
      </div>

      <div class="reader-body" @click="next">
        <div class="step-display">
          <div class="step-number">
            {{ enhanceStep(steps[currentStep]).action || '' }} 步骤 {{ currentStep + 1 }}
          </div>
          <div class="reader-badges">
            <span v-if="enhanceStep(steps[currentStep]).heat" class="reader-heat" :class="enhanceStep(steps[currentStep]).heat">
              🔥 {{ enhanceStep(steps[currentStep]).heat }}火
            </span>
            <span v-if="enhanceStep(steps[currentStep]).time" class="reader-time">
              ⏱ {{ enhanceStep(steps[currentStep]).time }}
            </span>
          </div>
          <div class="step-content">{{ steps[currentStep] }}</div>
        </div>
      </div>

      <div class="reader-footer">
        <button class="reader-nav-btn" :disabled="currentStep === 0" @click="prev">上一步</button>
        <div class="reader-dots">
          <span
            v-for="(_, i) in steps"
            :key="i"
            class="reader-dot"
            :class="{ active: i === currentStep }"
            @click="currentStep = i"
          ></span>
        </div>
        <button
          v-if="currentStep < totalSteps - 1"
          class="reader-nav-btn primary"
          @click="next"
        >下一步</button>
        <button
          v-else
          class="reader-nav-btn primary"
          @click="close"
        >完成</button>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.reader-overlay {
  position: fixed;
  inset: 0;
  background: var(--color-card);
  z-index: 2000;
  display: flex;
  flex-direction: column;
  color: var(--color-text);
}

.reader-header {
  display: flex;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid var(--color-border);
  gap: 12px;
}

.reader-close {
  background: none;
  border: none;
  font-size: 20px;
  cursor: pointer;
  color: var(--color-text-muted);
  padding: 4px;
  flex-shrink: 0;
}

.reader-close:hover {
  color: var(--color-text);
}

.reader-title {
  flex: 1;
  font-size: 16px;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.reader-progress {
  font-size: 13px;
  color: var(--color-text-muted);
  flex-shrink: 0;
}

.reader-body {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 32px;
  cursor: pointer;
  user-select: none;
}

.step-display {
  text-align: center;
  max-width: 600px;
}

.step-number {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-primary);
  margin-bottom: 16px;
  text-transform: uppercase;
  letter-spacing: 2px;
}

.reader-badges {
  display: flex;
  justify-content: center;
  gap: 8px;
  margin-bottom: 20px;
}

.reader-heat {
  font-size: 13px;
  padding: 4px 14px;
  border-radius: 20px;
  font-weight: 500;
}

.reader-heat.小 {
  background: #FFF3E0;
  color: #E65100;
}

.reader-heat.中 {
  background: #FFF3E0;
  color: #E65100;
}

.reader-heat.大 {
  background: #FFEBEE;
  color: #C62828;
}

.reader-time {
  font-size: 13px;
  padding: 4px 14px;
  border-radius: 20px;
  background: var(--color-primary-light);
  color: var(--color-primary);
  font-weight: 500;
}

.step-content {
  font-size: 28px;
  line-height: 1.7;
  color: var(--color-text);
  font-weight: 450;
}

@media (max-width: 768px) {
  .step-content {
    font-size: 22px;
  }
  .reader-body {
    padding: 24px 20px;
  }
}

.reader-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-top: 1px solid var(--color-border);
  gap: 12px;
}

.reader-nav-btn {
  padding: 10px 24px;
  border: 1px solid var(--color-border);
  background: var(--color-card);
  color: var(--color-text);
  border-radius: var(--radius-sm);
  font-size: 14px;
  cursor: pointer;
  font-family: var(--font-sans);
  transition: all 0.2s;
  min-width: 80px;
}

.reader-nav-btn:disabled {
  opacity: 0.3;
  cursor: default;
}

.reader-nav-btn.primary {
  background: var(--color-primary);
  color: #fff;
  border-color: var(--color-primary);
  font-weight: 500;
}

.reader-nav-btn.primary:hover {
  background: var(--color-primary-hover);
}

.reader-dots {
  display: flex;
  align-items: center;
  gap: 6px;
}

.reader-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-border);
  cursor: pointer;
  transition: all 0.2s;
}

.reader-dot.active {
  background: var(--color-primary);
  width: 24px;
  border-radius: 4px;
}
</style>
