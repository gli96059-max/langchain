<script setup>
import { ref, reactive, onUnmounted } from 'vue'
import StepReader from './StepReader.vue'

const props = defineProps({
  recipe: { type: Object, required: true },
  favorited: { type: Boolean, default: false },
})

const emit = defineEmits(['favorite', 'unfavorite'])

const showSteps = ref(false)
const showReader = ref(false)
const timers = reactive({})

function toggleFavorite() {
  if (props.favorited) {
    emit('unfavorite', props.recipe)
  } else {
    emit('favorite', props.recipe)
  }
}

function difficultyLabel(d) {
  const map = { '简单': '简单', '中等': '中等', '困难': '困难' }
  return map[d] || d
}

function difficultyClass(d) {
  const map = { '简单': 'easy', '中等': 'medium', '困难': 'hard' }
  return map[d] || ''
}

function scoreColor(score) {
  if (score >= 85) return 'var(--color-success)'
  if (score >= 70) return 'var(--color-warning)'
  return 'var(--color-text-muted)'
}

// ── Timer ──────────────────────────────────────────────────────────

function parseMinutes(text) {
  const m = text.match(/(\d+)\s*[分钟分]/)
  if (m) return parseInt(m[1]) * 60
  const s = text.match(/(\d+)\s*秒/)
  if (s) return parseInt(s[1])
  return null
}

function startTimer(stepIndex, stepText) {
  const total = parseMinutes(stepText)
  if (!total) return
  if (timers[stepIndex]) return

  const timer = reactive({ remaining: total, running: true, interval: null })
  timers[stepIndex] = timer

  timer.interval = setInterval(() => {
    timer.remaining--
    if (timer.remaining <= 0) {
      clearInterval(timer.interval)
      timer.remaining = 0
      timer.running = false
      timer.interval = null
    }
  }, 1000)
}

function stopTimer(stepIndex) {
  const t = timers[stepIndex]
  if (!t) return
  if (t.interval) clearInterval(t.interval)
  delete timers[stepIndex]
}

function formatTime(seconds) {
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  if (m > 0) return `${m}分${s > 0 ? s + '秒' : ''}`
  return `${s}秒`
}

onUnmounted(() => {
  Object.values(timers).forEach(t => {
    if (t.interval) clearInterval(t.interval)
  })
})
</script>

<template>
  <div class="recipe-card">
    <div class="card-header">
      <div class="card-title-row">
        <h3 class="recipe-name">{{ recipe.name }}</h3>
        <div class="card-actions">
          <button class="fav-btn" :class="{ active: favorited }" @click="toggleFavorite" title="收藏菜谱">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
              <path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z" :fill="favorited ? '#E8734A' : 'none'" :stroke="favorited ? '#E8734A' : '#999'" stroke-width="2"/>
            </svg>
          </button>
          <span class="difficulty-badge" :class="difficultyClass(recipe.difficulty)">
            {{ difficultyLabel(recipe.difficulty) }}
          </span>
        </div>
      </div>
    </div>

    <div class="card-body">
      <!-- Image -->
      <div v-if="recipe.image_url" class="recipe-image-wrapper">
        <img
          :src="recipe.image_url"
          :alt="recipe.name"
          class="recipe-image"
          @error="(e) => { e.target.style.display = 'none' }"
        />
      </div>

      <!-- Scores -->
      <div class="scores-row">
        <div class="score-item">
          <span class="score-label">综合评分</span>
          <span class="score-value" :style="{ color: scoreColor(recipe.overall_score) }">
            {{ recipe.overall_score }}
          </span>
        </div>
        <div class="score-divider"></div>
        <div class="score-item">
          <span class="score-label">营养评分</span>
          <span class="score-value" :style="{ color: scoreColor(recipe.nutrition_score) }">
            {{ recipe.nutrition_score }}
          </span>
        </div>
      </div>

      <!-- Ingredients -->
      <div class="section">
        <div class="section-title">食材</div>
        <div class="ingredient-tags">
          <span v-for="(ing, i) in recipe.ingredients" :key="i" class="ingredient-tag">
            {{ ing }}
          </span>
        </div>
      </div>

      <!-- Steps (collapsible) -->
      <div class="section">
        <button class="steps-toggle" @click="showSteps = !showSteps">
          <span class="section-title" style="margin-bottom: 0">做法步骤</span>
          <span class="toggle-icon" :class="{ open: showSteps }">▸</span>
        </button>
        <div v-if="showSteps && recipe.steps?.length" class="steps-list">
          <div v-for="(step, i) in recipe.steps" :key="i" class="step-item">
            <span class="step-num">{{ i + 1 }}</span>
            <div class="step-content">
              <span class="step-text">{{ step }}</span>
              <div v-if="parseMinutes(step)" class="step-timer">
                <button
                  v-if="!timers[i]"
                  class="timer-start-btn"
                  @click="startTimer(i, step)"
                  title="开始计时"
                >
                  ⏱ 计时
                </button>
                <div v-else class="timer-display" :class="{ done: !timers[i].remaining }">
                  <span class="timer-time">{{ formatTime(timers[i].remaining) }}</span>
                  <button class="timer-stop-btn" @click="stopTimer(i)" title="取消">✕</button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Reason -->
      <div class="reason-text">
        💬 {{ recipe.reason }}
      </div>
    </div>

    <!-- Links -->
    <div v-if="recipe.steps?.length" class="card-footer">
      <div class="footer-links">
        <button class="reader-link" @click="showReader = true" v-if="recipe.steps.length > 0">
          📖 阅读模式
        </button>
        <a
          v-if="recipe.reference_url"
          :href="recipe.reference_url"
          target="_blank"
          rel="noopener"
          class="reference-link"
        >
          查看参考来源 →
        </a>
      </div>
    </div>

    <StepReader
      :visible="showReader"
      :recipe="recipe"
      @close="showReader = false"
    />
  </div>
</template>

<style scoped>
.recipe-card {
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  transition: box-shadow 0.2s;
}

.recipe-card:hover {
  box-shadow: var(--shadow-md);
}

.card-header {
  padding: 16px 20px 0;
}

.card-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.recipe-name {
  font-size: 18px;
  font-weight: 600;
  color: var(--color-text);
  margin: 0;
}

.card-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.fav-btn {
  background: none;
  border: none;
  cursor: pointer;
  padding: 4px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.fav-btn:hover {
  background: rgba(232, 115, 74, 0.1);
}

.fav-btn.active:hover {
  background: rgba(232, 115, 74, 0.15);
}

.difficulty-badge {
  font-size: 12px;
  font-weight: 500;
  padding: 3px 10px;
  border-radius: 20px;
  white-space: nowrap;
}

.difficulty-badge.easy {
  background: #E8F5E9;
  color: #2E7D32;
}

.difficulty-badge.medium {
  background: #FFF3E0;
  color: #E65100;
}

.difficulty-badge.hard {
  background: #FFEBEE;
  color: #C62828;
}

.card-body {
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

/* Image */
.recipe-image-wrapper {
  border-radius: var(--radius-sm);
  overflow: hidden;
  max-height: 200px;
}

.recipe-image {
  width: 100%;
  height: 180px;
  object-fit: cover;
  display: block;
  border-radius: var(--radius-sm);
  background: var(--color-bg);
}

/* Scores */
.scores-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 20px;
  background: var(--color-primary-light);
  border-radius: var(--radius-sm);
  padding: 12px 16px;
}

.score-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.score-label {
  font-size: 12px;
  color: var(--color-text-secondary);
}

.score-value {
  font-size: 24px;
  font-weight: 700;
}

.score-divider {
  width: 1px;
  height: 36px;
  background: var(--color-border);
}

/* Sections */
.section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.section-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* Ingredients */
.ingredient-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.ingredient-tag {
  font-size: 13px;
  padding: 4px 10px;
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: 20px;
  color: var(--color-text);
}

/* Steps */
.steps-toggle {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  background: none;
  border: none;
  cursor: pointer;
  padding: 0;
  font-family: var(--font-sans);
}

.toggle-icon {
  font-size: 14px;
  color: var(--color-text-secondary);
  transition: transform 0.2s;
}

.toggle-icon.open {
  transform: rotate(90deg);
}

.steps-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.step-item {
  display: flex;
  gap: 10px;
  font-size: 14px;
  line-height: 1.5;
}

.step-num {
  flex-shrink: 0;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--color-primary-light);
  color: var(--color-primary);
  font-size: 12px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
}

.step-content {
  flex: 1;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
}

.step-text {
  color: var(--color-text);
}

.step-timer {
  flex-shrink: 0;
}

.timer-start-btn {
  font-size: 11px;
  padding: 2px 8px;
  border: 1px solid var(--color-primary);
  background: var(--color-primary-light);
  color: var(--color-primary);
  border-radius: 12px;
  cursor: pointer;
  white-space: nowrap;
  font-family: var(--font-sans);
  transition: all 0.2s;
}

.timer-start-btn:hover {
  background: var(--color-primary);
  color: #fff;
}

.timer-display {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  background: var(--color-primary);
  color: #fff;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
  animation: timerPulse 1s ease-in-out infinite;
}

.timer-display.done {
  background: var(--color-success);
  animation: none;
}

.timer-time {
  font-variant-numeric: tabular-nums;
}

.timer-stop-btn {
  background: none;
  border: none;
  color: rgba(255,255,255,0.7);
  cursor: pointer;
  font-size: 10px;
  padding: 0 2px;
  line-height: 1;
}

.timer-stop-btn:hover {
  color: #fff;
}

@keyframes timerPulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.85; }
}

/* Reason */
.reason-text {
  font-size: 14px;
  color: var(--color-text-secondary);
  font-style: italic;
  line-height: 1.5;
  padding: 10px 14px;
  background: var(--color-bg);
  border-radius: var(--radius-sm);
}

/* Footer */
.card-footer {
  padding: 0 20px 16px;
}

.footer-links {
  display: flex;
  align-items: center;
  gap: 16px;
}

.reader-link {
  font-size: 13px;
  color: var(--color-primary);
  background: none;
  border: none;
  cursor: pointer;
  font-weight: 500;
  font-family: var(--font-sans);
  padding: 0;
}

.reader-link:hover {
  text-decoration: underline;
}

.reference-link {
  font-size: 13px;
  color: var(--color-primary);
  text-decoration: none;
  font-weight: 500;
}

.reference-link:hover {
  text-decoration: underline;
}
</style>
