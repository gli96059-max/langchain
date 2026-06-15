<script setup>
import { ref } from 'vue'

const props = defineProps({
  recipe: { type: Object, required: true },
})

const showSteps = ref(false)

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
</script>

<template>
  <div class="recipe-card">
    <div class="card-header">
      <div class="card-title-row">
        <h3 class="recipe-name">{{ recipe.name }}</h3>
        <span class="difficulty-badge" :class="difficultyClass(recipe.difficulty)">
          {{ difficultyLabel(recipe.difficulty) }}
        </span>
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
            <span class="step-text">{{ step }}</span>
          </div>
        </div>
      </div>

      <!-- Reason -->
      <div class="reason-text">
        💬 {{ recipe.reason }}
      </div>
    </div>

    <!-- Links -->
    <div v-if="recipe.reference_url" class="card-footer">
      <a
        :href="recipe.reference_url"
        target="_blank"
        rel="noopener"
        class="reference-link"
      >
        查看参考来源 →
      </a>
    </div>
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

.step-text {
  color: var(--color-text);
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
