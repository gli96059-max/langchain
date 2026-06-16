<script setup>
import { ref, reactive, nextTick, onUnmounted } from 'vue'
import StepReader from './StepReader.vue'
import { saveRecipe } from '../api/index.js'

const props = defineProps({
  recipe: { type: Object, required: true },
  showSave: { type: Boolean, default: false },
  saved: { type: Boolean, default: false },
  showDelete: { type: Boolean, default: false },
  sessionId: { type: String, default: null },
})

const emit = defineEmits(['save', 'saved-change', 'delete'])

const showSteps = ref(false)
const showReader = ref(false)
const showShareCard = ref(false)
const shareCanvasRef = ref(null)
const timers = reactive({})

// ── Visual step enhancement ───────────────────────────────────────

const ACTION_EMOJIS = [
  ['切|剁|切片|切块|切丁|切丝', '🔪'],
  ['炒|翻炒|爆炒', '🔥'],
  ['煎|炸|油煎|油炸', '🍳'],
  ['煮|焯|汆|烫', '💧'],
  ['蒸', '♨️'],
  ['烤|烘|焗', '🔥'],
  ['炖|焖|煲|卤', '🫕'],
  ['拌|搅拌|搅匀|混合', '🥢'],
  ['腌|腌制|入味', '🧂'],
  ['洗|清洗|冲洗|泡发', '🚿'],
  ['剥|去壳|去皮', '🫘'],
  ['调|调味|加', '🧂'],
  ['倒|加入|放入|下锅', '📥'],
  ['盛|装盘|出锅', '🍽️'],
  ['擀|揉|捏|搓', '👐'],
  ['盖|焖|捂', '🫗'],
]

function enhanceStep(text) {
  const parts = { text, heat: null, time: null, action: null }

  // Extract heat level
  const heatMatch = text.match(/([小中大])火/)
  if (heatMatch) {
    parts.heat = heatMatch[1]
  }

  // Extract time
  const timeMatch = text.match(/(\d+)\s*[分钟分秒]/)
  if (timeMatch) {
    parts.time = timeMatch[0]
  }

  // Detect action emoji
  for (const [pattern, emoji] of ACTION_EMOJIS) {
    if (new RegExp(pattern).test(text)) {
      parts.action = emoji
      break
    }
  }

  return parts
}

function handleShare() {
  showShareCard.value = true
  nextTick(() => drawShareCard())
}

async function drawShareCard() {
  const canvas = shareCanvasRef.value
  if (!canvas) return
  const r = props.recipe
  const ctx = canvas.getContext('2d')
  const W = 600
  const colLeft = 40
  const maxW = W - 80

  // Load image first if available
  let img = null
  if (r.image_url) {
    try {
      img = await new Promise((resolve) => {
        const i = new Image()
        i.crossOrigin = 'anonymous'
        i.onload = () => resolve(i)
        i.onerror = () => resolve(null)
        i.src = r.image_url
      })
    } catch { img = null }
  }

  const hasImg = !!img
  const headerH = 100
  const imgH = hasImg ? 220 : 0
  const bodyTop = headerH + imgH + (hasImg ? 30 : 16)
  const H = Math.max(900, bodyTop + 500)
  canvas.width = W
  canvas.height = H

  // White background
  ctx.fillStyle = '#FFF8F3'
  ctx.fillRect(0, 0, W, H)

  // Orange header bar
  const grad = ctx.createLinearGradient(0, 0, W, 0)
  grad.addColorStop(0, '#E8734A')
  grad.addColorStop(1, '#D0603A')
  ctx.fillStyle = grad
  ctx.fillRect(0, 0, W, headerH)

  // Header text
  ctx.textAlign = 'center'
  ctx.fillStyle = '#fff'
  ctx.font = 'bold 30px "Microsoft YaHei", "PingFang SC", sans-serif'
  fillWrapped(ctx, `🍳 ${r.name || '菜谱推荐'}`, W / 2, 48, W - 80, 40)

  ctx.font = '15px "Microsoft YaHei", "PingFang SC", sans-serif'
  ctx.fillStyle = 'rgba(255,255,255,0.92)'
  const diff = r.difficulty || '未标注'
  const score = r.overall_score || '-'
  ctx.fillText(`难度: ${diff}    综合评分: ${score}`, W / 2, 82)

  // ── Recipe image ──
  if (hasImg) {
    const imgW = W - 80
    const imgX = 40
    const imgY = headerH + 16
    // Shadow below image
    ctx.fillStyle = 'rgba(0,0,0,0.08)'
    ctx.beginPath()
    ctx.ellipse(W / 2, imgY + imgH + 4, imgW / 2 - 10, 8, 0, 0, Math.PI * 2)
    ctx.fill()
    // Draw image with rounded corners
    ctx.save()
    roundRectPath(ctx, imgX, imgY, imgW, imgH, 14)
    ctx.clip()
    ctx.drawImage(img, imgX, imgY, imgW, imgH)
    ctx.restore()
    // Thin border
    ctx.strokeStyle = 'rgba(0,0,0,0.06)'
    ctx.lineWidth = 1
    roundRectPath(ctx, imgX, imgY, imgW, imgH, 14)
    ctx.stroke()
  }

  // Body
  let y = bodyTop
  ctx.textAlign = 'left'

  // ── Ingredients ──
  ctx.fillStyle = '#E8734A'
  ctx.font = 'bold 19px "Microsoft YaHei", "PingFang SC", sans-serif'
  ctx.fillText('📝 食材清单', colLeft, y)
  y += 30

  ctx.font = '16px "Microsoft YaHei", "PingFang SC", sans-serif'
  ctx.fillStyle = '#333'
  if (r.ingredients && r.ingredients.length) {
    for (const ing of r.ingredients.slice(0, 10)) {
      ctx.fillText(`• ${ing}`, colLeft + 12, y)
      y += 25
    }
  }
  y += 10

  // ── Steps ──
  ctx.fillStyle = '#E8734A'
  ctx.font = 'bold 19px "Microsoft YaHei", "PingFang SC", sans-serif'
  ctx.fillText('👨‍🍳 做法步骤', colLeft, y)
  y += 30

  ctx.font = '15px "Microsoft YaHei", "PingFang SC", sans-serif'
  ctx.fillStyle = '#444'
  if (r.steps && r.steps.length) {
    for (let i = 0; i < Math.min(r.steps.length, 6); i++) {
      const label = `${i + 1}.  `
      ctx.fillStyle = '#E8734A'
      ctx.font = 'bold 15px "Microsoft YaHei", "PingFang SC", sans-serif'
      ctx.fillText(label, colLeft, y)
      ctx.fillStyle = '#444'
      ctx.font = '15px "Microsoft YaHei", "PingFang SC", sans-serif'
      const remainW = maxW - ctx.measureText(label).width
      const textX = colLeft + ctx.measureText(label).width
      const stepText = r.steps[i]
      const lines = wrapTextLines(ctx, stepText, remainW)
      for (let li = 0; li < lines.length; li++) {
        if (li === 0) {
          ctx.fillText(lines[li], textX, y)
        } else {
          y += 22
          ctx.fillText(lines[li], colLeft + 20, y)
        }
      }
      y += 26
    }
  }
  y += 6

  // ── Reason ──
  if (r.reason) {
    const reasonLines = wrapTextLines(ctx, `💡 ${r.reason}`, maxW)
    const rh = Math.max(36, reasonLines.length * 20 + 12)
    ctx.fillStyle = '#FFF0E8'
    ctx.fillRect(colLeft - 8, y - 6, maxW + 16, rh)
    ctx.fillStyle = '#666'
    ctx.font = '14px "Microsoft YaHei", "PingFang SC", sans-serif'
    let ry = y + 14
    for (const line of reasonLines) {
      ctx.fillText(line, colLeft, ry)
      ry += 20
    }
    y += rh + 12
  }

  // ── Footer ──
  if (y < H - 28) y = H - 28
  ctx.fillStyle = '#BBB'
  ctx.font = '12px "Microsoft YaHei", "PingFang SC", sans-serif'
  ctx.textAlign = 'center'
  ctx.fillText('由 AI 私厨助手生成', W / 2, y)
}

function roundRectPath(ctx, x, y, w, h, r) {
  ctx.beginPath()
  ctx.moveTo(x + r, y)
  ctx.lineTo(x + w - r, y)
  ctx.quadraticCurveTo(x + w, y, x + w, y + r)
  ctx.lineTo(x + w, y + h - r)
  ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h)
  ctx.lineTo(x + r, y + h)
  ctx.quadraticCurveTo(x, y + h, x, y + h - r)
  ctx.lineTo(x, y + r)
  ctx.quadraticCurveTo(x, y, x + r, y)
  ctx.closePath()
}

// Helper: returns array of wrapped text lines
function wrapTextLines(ctx, text, maxWidth) {
  const lines = []
  let line = ''
  for (const ch of text) {
    const test = line + ch
    if (ctx.measureText(test).width > maxWidth && line) {
      lines.push(line)
      line = ch
    } else {
      line = test
    }
  }
  if (line) lines.push(line)
  return lines.length ? lines : ['']
}

// Helper: fill wrapped text (centered)
function fillWrapped(ctx, text, x, y, maxW, lineH) {
  const lines = wrapTextLines(ctx, text, maxW)
  for (const line of lines) {
    ctx.fillText(line, x, y)
    y += lineH
  }
}

function wrapText(ctx, text, x, y, maxW, lineH) {
  let line = ''
  let cx = x
  for (const ch of text) {
    const test = line + ch
    if (ctx.measureText(test).width > maxW) {
      ctx.fillText(line, cx, y)
      y += lineH
      cx = x
      line = ch
    } else {
      line = test
    }
  }
  if (line) ctx.fillText(line, cx, y)
}

function downloadShareCard() {
  const canvas = shareCanvasRef.value
  if (!canvas) return
  const link = document.createElement('a')
  link.download = `${props.recipe.name || 'recipe'}.png`
  link.href = canvas.toDataURL('image/png')
  link.click()
}

const saving = ref(false)

async function saveToLibrary() {
  if (saving.value || props.saved) return
  saving.value = true
  try {
    await saveRecipe(props.sessionId, props.recipe)
    emit('save', props.recipe)
  } catch { /* ignore */ }
  saving.value = false
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
          <button
            v-if="showSave"
            class="save-btn"
            :class="{ saved }"
            :disabled="saving"
            @click="saveToLibrary"
            :title="saved ? '已保存' : '加入菜谱库'"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M19 21l-7-5-7 5V5a2 2 0 012-2h10a2 2 0 012 2v16z"/>
            </svg>
            {{ saved ? '已保存' : '保存' }}
          </button>
          <button
            v-if="showDelete"
            class="card-delete-btn"
            @click.stop="emit('delete', recipe)"
            title="删除"
          >
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <path d="M2 4h10M5 4V2.5A.5.5 0 015.5 2h3a.5.5 0 01.5.5V4M11 4v7.5a1 1 0 01-1 1H4a1 1 0 01-1-1V4" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/>
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

      <!-- Nutrition details -->
      <div v-if="recipe.nutrition" class="nutrition-row">
        <div class="nutrition-item">
          <span class="nutrition-value">{{ recipe.nutrition.calories || '-' }}</span>
          <span class="nutrition-label">千卡</span>
        </div>
        <div class="nutrition-item">
          <span class="nutrition-value">{{ recipe.nutrition.protein || '-' }}</span>
          <span class="nutrition-label">蛋白质</span>
        </div>
        <div class="nutrition-item">
          <span class="nutrition-value">{{ recipe.nutrition.fat || '-' }}</span>
          <span class="nutrition-label">脂肪</span>
        </div>
        <div class="nutrition-item">
          <span class="nutrition-value">{{ recipe.nutrition.carbs || '-' }}</span>
          <span class="nutrition-label">碳水</span>
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
            <span class="step-num">{{ enhanceStep(step).action || '' }}{{ i + 1 }}</span>
            <div class="step-content">
              <div class="step-text-wrap">
                <span class="step-text">{{ step }}</span>
                <div class="step-badges">
                  <span v-if="enhanceStep(step).heat" class="heat-badge" :class="enhanceStep(step).heat">
                    🔥 {{ enhanceStep(step).heat }}火
                  </span>
                  <span v-if="enhanceStep(step).time" class="time-badge">
                    ⏱ {{ enhanceStep(step).time }}
                  </span>
                </div>
              </div>
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
        <button class="share-link" @click="handleShare">
          📤 分享
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

    <!-- Share card modal -->
    <Teleport to="body">
      <div v-if="showShareCard" class="share-overlay" @click.self="showShareCard = false">
        <div class="share-modal">
          <div class="share-modal-header">
            <h3>📤 保存菜谱卡片</h3>
            <button class="share-close" @click="showShareCard = false">✕</button>
          </div>
          <div class="share-canvas-wrap">
            <canvas ref="shareCanvasRef"></canvas>
          </div>
          <div class="share-modal-footer">
            <button class="share-download-btn" @click="downloadShareCard">
              保存图片
            </button>
            <span class="share-hint">长按或右键可保存到相册</span>
          </div>
        </div>
      </div>
    </Teleport>

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
  flex-shrink: 0;
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

.save-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border: 1px solid var(--color-primary);
  background: var(--color-primary-light);
  color: var(--color-primary);
  border-radius: var(--radius-sm);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  font-family: var(--font-sans);
  transition: all 0.2s;
  white-space: nowrap;
}

.save-btn:hover {
  background: var(--color-primary);
  color: #fff;
}

.save-btn.saved {
  background: var(--color-success);
  border-color: var(--color-success);
  color: #fff;
}

.save-btn:disabled {
  opacity: 0.6;
  cursor: default;
}

.card-delete-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: 1px solid var(--color-border);
  background: var(--color-card);
  cursor: pointer;
  color: var(--color-text-muted);
  transition: all 0.2s;
  flex-shrink: 0;
}
.card-delete-btn:hover {
  color: var(--color-danger);
  border-color: var(--color-danger);
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

/* Nutrition details */
.nutrition-row {
  display: flex;
  align-items: center;
  justify-content: space-around;
  background: var(--color-bg);
  border-radius: var(--radius-sm);
  padding: 10px 12px;
  gap: 8px;
}

.nutrition-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1px;
}

.nutrition-value {
  font-size: 16px;
  font-weight: 700;
  color: var(--color-text);
}

.nutrition-label {
  font-size: 10px;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
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
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--color-primary-light);
  color: var(--color-primary);
  font-size: 13px;
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

.step-text-wrap {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.step-text {
  color: var(--color-text);
  line-height: 1.6;
}

.step-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.heat-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 500;
  white-space: nowrap;
}

.heat-badge.小 {
  background: #FFF3E0;
  color: #E65100;
}

.heat-badge.中 {
  background: #FFF3E0;
  color: #E65100;
}

.heat-badge.大 {
  background: #FFEBEE;
  color: #C62828;
}

.time-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  background: var(--color-primary-light);
  color: var(--color-primary);
  font-weight: 500;
  white-space: nowrap;
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

.share-link {
  font-size: 13px;
  color: var(--color-text-secondary);
  background: none;
  border: none;
  cursor: pointer;
  font-weight: 500;
  font-family: var(--font-sans);
  padding: 0;
}

.share-link:hover {
  color: var(--color-primary);
}

.share-toast {
  position: fixed;
  bottom: 80px;
  left: 50%;
  transform: translateX(-50%);
  background: var(--color-text);
  color: #fff;
  padding: 8px 20px;
  border-radius: 20px;
  font-size: 13px;
  z-index: 3000;
  animation: fadeIn 0.3s ease;
}

/* Share card modal */
.share-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 5000;
}

.share-modal {
  background: var(--color-card);
  border-radius: var(--radius-lg);
  width: 500px;
  max-width: 90vw;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
}

.share-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--color-border);
}

.share-modal-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.share-close {
  background: none;
  border: none;
  font-size: 18px;
  cursor: pointer;
  color: var(--color-text-muted);
  padding: 4px;
  line-height: 1;
}

.share-canvas-wrap {
  flex: 1;
  overflow: auto;
  padding: 16px;
  display: flex;
  justify-content: center;
  background: #f5f5f5;
}

.share-canvas-wrap canvas {
  max-width: 100%;
  height: auto;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.share-modal-footer {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 16px 20px;
  border-top: 1px solid var(--color-border);
}

.share-download-btn {
  padding: 10px 32px;
  background: var(--color-primary);
  color: #fff;
  border: none;
  border-radius: var(--radius-sm);
  font-size: 15px;
  font-weight: 500;
  cursor: pointer;
  font-family: var(--font-sans);
  transition: background 0.2s;
}

.share-download-btn:hover {
  background: var(--color-primary-hover);
}

.share-hint {
  font-size: 12px;
  color: var(--color-text-muted);
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

@media (max-width: 768px) {
  .recipe-card {
    border-radius: var(--radius-md);
  }
  .card-header {
    padding: 12px 14px 0;
  }
  .card-body {
    padding: 12px 14px;
    gap: 10px;
  }
  .recipe-name {
    font-size: 16px;
  }
  .recipe-image {
    height: 140px;
  }
  .score-value {
    font-size: 20px;
  }
  .nutrition-item {
    min-width: 0;
  }
  .nutrition-value {
    font-size: 14px;
  }
  .ingredient-tag {
    font-size: 12px;
    padding: 3px 8px;
  }
  .step-num {
    width: 24px;
    height: 24px;
    font-size: 12px;
  }
  .step-content {
    font-size: 13px;
  }
  .timer-start-btn, .timer-display {
    font-size: 11px;
    padding: 4px 10px;
  }
  .footer-links {
    flex-wrap: wrap;
    gap: 10px;
  }
  .card-footer {
    padding: 0 14px 12px;
  }
  .star {
    font-size: 28px;
  }

  /* Share card: bottom-sheet on mobile */
  .share-modal {
    width: 100vw;
    max-width: 100vw;
    max-height: 90vh;
    border-radius: var(--radius-lg) var(--radius-lg) 0 0;
  }
  .share-canvas-wrap {
    padding: 10px;
  }
  .share-canvas-wrap canvas {
    max-width: 100%;
    height: auto;
  }
  .share-download-btn {
    width: 100%;
    text-align: center;
  }

  /* Share card slides up from bottom */
  .share-overlay {
    align-items: flex-end;
  }
}
</style>
