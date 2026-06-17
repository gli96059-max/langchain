<script setup>
import { ref, computed, onMounted } from 'vue'
import RecipeCard from './RecipeCard.vue'
import { listRecipes, deleteRecipe, batchDeleteRecipes } from '../api/index.js'

const emit = defineEmits(['close'])

const recipes = ref([])
const loading = ref(false)
const batchMode = ref(false)
const selectedForDelete = ref(new Set())

// Filters
const searchText = ref('')
const ingredientText = ref('')
const selectedDifficulty = ref('')
const selectedCuisine = ref('')
const selectedTaste = ref('')

let debounceTimer = null

const difficultyOptions = ['简单', '中等', '困难']
const cuisineOptions = ['中餐', '西餐', '日料', '韩餐', '东南亚']
const tasteOptions = ['清淡', '麻辣', '酸甜', '咸鲜', '甜', '辣']

const hasActiveFilters = computed(() =>
  searchText.value || ingredientText.value ||
  selectedDifficulty.value || selectedCuisine.value || selectedTaste.value
)

const activeFilterChips = computed(() => {
  const chips = []
  if (searchText.value) chips.push({ key: 'search', label: `"${searchText.value}"` })
  if (ingredientText.value) chips.push({ key: 'ingredient', label: `食材: ${ingredientText.value}` })
  if (selectedDifficulty.value) chips.push({ key: 'difficulty', label: selectedDifficulty.value })
  if (selectedCuisine.value) chips.push({ key: 'cuisine', label: selectedCuisine.value })
  if (selectedTaste.value) chips.push({ key: 'taste', label: selectedTaste.value })
  return chips
})

async function loadRecipes() {
  loading.value = true
  try {
    const params = {}
    if (searchText.value) params.search = searchText.value
    if (ingredientText.value) params.ingredient = ingredientText.value
    if (selectedDifficulty.value) params.difficulty = selectedDifficulty.value
    if (selectedCuisine.value) params.cuisine_type = selectedCuisine.value
    if (selectedTaste.value) params.taste = selectedTaste.value
    recipes.value = await listRecipes(params)
  } catch { /* ignore */ }
  loading.value = false
}

function debounceLoad(ms = 300) {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(loadRecipes, ms)
}

function onSearchInput() { debounceLoad(300) }
function onIngredientInput() { debounceLoad(400) }
function onDropdownChange() { debounceLoad(100) }

function removeFilter(key) {
  if (key === 'search') searchText.value = ''
  else if (key === 'ingredient') ingredientText.value = ''
  else if (key === 'difficulty') selectedDifficulty.value = ''
  else if (key === 'cuisine') selectedCuisine.value = ''
  else if (key === 'taste') selectedTaste.value = ''
  loadRecipes()
}

function clearAllFilters() {
  searchText.value = ''
  ingredientText.value = ''
  selectedDifficulty.value = ''
  selectedCuisine.value = ''
  selectedTaste.value = ''
  loadRecipes()
}

// ── Delete / Batch delete ──────────────────────────────────────────

function confirmDelete(recipe) {
  const name = recipe.recipe_data?.name || recipe.name || '这道菜'
  if (!confirm(`确定删除「${name}」？`)) return
  doDelete(recipe.id)
}

async function doDelete(id) {
  await deleteRecipe(id)
  recipes.value = recipes.value.filter(r => r.id !== id)
  selectedForDelete.value.delete(id)
}

function toggleSelect(id) {
  const next = new Set(selectedForDelete.value)
  next.has(id) ? next.delete(id) : next.add(id)
  selectedForDelete.value = next
}

function selectAll() {
  selectedForDelete.value = new Set(recipes.value.map(r => r.id))
}

function exitBatchMode() {
  batchMode.value = false
  selectedForDelete.value = new Set()
}

function enterBatchMode() {
  batchMode.value = true
  selectedForDelete.value = new Set()
}

async function executeBatchDelete() {
  const ids = Array.from(selectedForDelete.value)
  if (!ids.length) return
  if (!confirm(`确定删除选中的 ${ids.length} 道菜谱？`)) return
  await batchDeleteRecipes(ids)
  recipes.value = recipes.value.filter(r => !ids.includes(r.id))
  exitBatchMode()
}

onMounted(loadRecipes)
</script>

<template>
  <div class="library">
    <div class="library-header">
      <button class="back-btn" @click="emit('close')">← 返回</button>
      <h2>📚 小斐的菜谱库</h2>
      <span class="recipe-count">{{ recipes.length }} 道菜</span>
      <div class="header-actions">
        <button v-if="!batchMode && recipes.length" class="batch-toggle-btn" @click="enterBatchMode">
          批量删除
        </button>
        <button v-if="batchMode" class="batch-toggle-btn active" @click="exitBatchMode">
          取消
        </button>
      </div>
    </div>

    <!-- Batch mode bar -->
    <div v-if="batchMode" class="batch-bar">
      <span class="batch-count">已选 {{ selectedForDelete.size }} / {{ recipes.length }}</span>
      <div class="batch-actions">
        <button class="batch-btn" @click="selectAll">全选</button>
        <button class="batch-btn danger" :disabled="!selectedForDelete.size" @click="executeBatchDelete">
          删除 ({{ selectedForDelete.size }})
        </button>
      </div>
    </div>

    <!-- Search & Filter Bar -->
    <div class="filter-bar">
      <div class="search-row">
        <svg class="search-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
        </svg>
        <input
          v-model="searchText"
          placeholder="搜索菜名、关键词..."
          class="search-input"
          @input="onSearchInput"
        />
        <input
          v-model="ingredientText"
          placeholder="按食材筛选..."
          class="ingredient-input"
          @input="onIngredientInput"
        />
      </div>

      <div class="filter-row">
        <div class="filter-group">
          <label>难度</label>
          <select v-model="selectedDifficulty" @change="onDropdownChange">
            <option value="">全部</option>
            <option v-for="d in difficultyOptions" :key="d" :value="d">{{ d }}</option>
          </select>
        </div>
        <div class="filter-group">
          <label>菜系</label>
          <select v-model="selectedCuisine" @change="onDropdownChange">
            <option value="">全部</option>
            <option v-for="c in cuisineOptions" :key="c" :value="c">{{ c }}</option>
          </select>
        </div>
        <div class="filter-group">
          <label>口味</label>
          <select v-model="selectedTaste" @change="onDropdownChange">
            <option value="">全部</option>
            <option v-for="t in tasteOptions" :key="t" :value="t">{{ t }}</option>
          </select>
        </div>

        <button
          v-if="hasActiveFilters"
          class="clear-btn"
          @click="clearAllFilters"
        >
          清除筛选
        </button>
      </div>

      <!-- Active filter chips -->
      <div v-if="hasActiveFilters" class="active-filters">
        <span
          v-for="chip in activeFilterChips"
          :key="chip.key"
          class="filter-chip"
        >
          {{ chip.label }}
          <button class="chip-remove" @click="removeFilter(chip.key)">&times;</button>
        </span>
      </div>
    </div>

    <!-- Results -->
    <div v-if="loading" class="loading">搜索中...</div>
    <div v-else-if="!recipes.length" class="empty">
      <p v-if="hasActiveFilters">没有符合条件的菜谱，试试调整筛选条件</p>
      <p v-else>暂无菜谱，在对话中点击「保存」按钮将菜谱加入菜谱库</p>
    </div>
    <div v-else class="recipe-grid">
      <div
        v-for="(item, i) in recipes"
        :key="item.id || i"
        class="recipe-item"
        :class="{ 'batch-selected': batchMode && selectedForDelete.has(item.id) }"
        @click="batchMode ? toggleSelect(item.id) : null"
      >
        <div v-if="batchMode" class="batch-check" :class="{ checked: selectedForDelete.has(item.id) }">
          <svg v-if="selectedForDelete.has(item.id)" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
        </div>
        <RecipeCard
          :recipe="item.recipe_data || item"
          :show-delete="!batchMode"
          @delete="confirmDelete"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.library {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.library-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 20px;
  border-bottom: 1px solid var(--color-border);
}

.back-btn {
  padding: 6px 12px;
  background: none;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 13px;
  color: var(--color-text);
  font-family: var(--font-sans);
}

.back-btn:hover {
  background: var(--color-bg);
}

.library-header h2 {
  flex: 1;
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.recipe-count {
  font-size: 13px;
  color: var(--color-text-muted);
}

.header-actions {
  display: flex;
  gap: 6px;
  flex-shrink: 0;
}

.batch-toggle-btn {
  padding: 5px 12px;
  background: none;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  font-size: 12px;
  color: var(--color-text-secondary);
  cursor: pointer;
  font-family: var(--font-sans);
  white-space: nowrap;
  transition: all 0.2s;
}
.batch-toggle-btn:hover { border-color: var(--color-primary); color: var(--color-primary); }
.batch-toggle-btn.active { border-color: var(--color-primary); color: var(--color-primary); }

/* Batch bar */
.batch-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  background: var(--color-primary-light);
  border-bottom: 1px solid var(--color-border);
  gap: 8px;
  flex-wrap: wrap;
}
.batch-count { font-size: 13px; font-weight: 500; color: var(--color-primary); }
.batch-actions { display: flex; gap: 6px; }
.batch-btn {
  padding: 4px 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-card);
  color: var(--color-text);
  font-size: 12px;
  cursor: pointer;
  font-family: var(--font-sans);
  white-space: nowrap;
}
.batch-btn.danger { border-color: var(--color-danger); color: var(--color-danger); }
.batch-btn.danger:hover { background: var(--color-danger); color: #fff; }
.batch-btn.danger:disabled { opacity: 0.3; cursor: default; background: var(--color-card); color: var(--color-text-muted); border-color: var(--color-border); }
.batch-btn:hover:not(:disabled) { background: var(--color-bg); }

/* ── Filter Bar ─────────────────────────────────────── */

.filter-bar {
  padding: 12px 20px;
  border-bottom: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  gap: 10px;
  background: var(--color-card);
}

.search-row {
  display: flex;
  gap: 8px;
  align-items: center;
  position: relative;
}

.search-icon {
  position: absolute;
  left: 12px;
  color: var(--color-text-muted);
  pointer-events: none;
}

.search-input {
  flex: 1;
  padding: 8px 12px 8px 36px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: 14px;
  color: var(--color-text);
  background: var(--color-bg);
  outline: none;
  font-family: var(--font-sans);
  transition: border-color 0.2s;
}

.search-input:focus {
  border-color: var(--color-primary);
}

.ingredient-input {
  width: 160px;
  padding: 8px 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: 14px;
  color: var(--color-text);
  background: var(--color-bg);
  outline: none;
  font-family: var(--font-sans);
  transition: border-color 0.2s;
}

.ingredient-input:focus {
  border-color: var(--color-primary);
}

.filter-row {
  display: flex;
  gap: 12px;
  align-items: flex-end;
  flex-wrap: wrap;
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.filter-group label {
  font-size: 11px;
  color: var(--color-text-muted);
  font-weight: 500;
}

.filter-group select {
  padding: 6px 28px 6px 10px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  font-size: 13px;
  color: var(--color-text);
  background: var(--color-bg);
  font-family: var(--font-sans);
  cursor: pointer;
  outline: none;
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg width='10' height='6' viewBox='0 0 10 6' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M1 1L5 5L9 1' stroke='%23999' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 8px center;
  min-width: 90px;
}

.filter-group select:focus {
  border-color: var(--color-primary);
}

.clear-btn {
  padding: 6px 14px;
  background: none;
  border: 1px solid var(--color-danger);
  color: var(--color-danger);
  border-radius: var(--radius-sm);
  font-size: 12px;
  cursor: pointer;
  font-family: var(--font-sans);
  white-space: nowrap;
  transition: all 0.2s;
}

.clear-btn:hover {
  background: var(--color-danger);
  color: #fff;
}

/* ── Active filter chips ────────────────────────────── */

.active-filters {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.filter-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px 4px 12px;
  background: var(--color-primary-light);
  border: 1px solid var(--color-border);
  border-radius: 20px;
  font-size: 12px;
  color: var(--color-text);
}

.chip-remove {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  border: none;
  background: transparent;
  color: var(--color-text-muted);
  font-size: 14px;
  cursor: pointer;
  padding: 0;
  line-height: 1;
}

.chip-remove:hover {
  background: var(--color-border);
  color: var(--color-text);
}

/* ── Results ────────────────────────────────────────── */

.loading {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-muted);
}

.empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-muted);
  padding: 40px 20px;
  text-align: center;
}

.recipe-item {
  position: relative;
  transition: background 0.15s;
  border-radius: var(--radius-lg);
}
.recipe-item.batch-selected {
  background: var(--color-primary-light);
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}
.batch-check {
  position: absolute;
  top: 16px;
  left: 16px;
  z-index: 2;
  width: 22px;
  height: 22px;
  border-radius: 4px;
  border: 2px solid var(--color-text-muted);
  background: rgba(255,255,255,0.9);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.15s;
}
.batch-check.checked {
  background: var(--color-primary);
  border-color: var(--color-primary);
}

.recipe-grid {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  max-width: 760px;
  margin: 0 auto;
  width: 100%;
  min-height: 0;
}

@media (max-width: 768px) {
  .library-header {
    padding: 12px 14px;
    padding-top: calc(12px + var(--safe-top, 0px));
  }
  .library-header h2 { font-size: 16px; }
  .back-btn { padding: 10px 14px; min-height: 40px; font-size: 14px; }
  .batch-toggle-btn { padding: 10px 14px; font-size: 13px; min-height: 40px; }
  .filter-bar {
    padding: 10px 14px;
  }
  .search-row {
    flex-direction: column;
  }
  .search-input, .ingredient-input {
    width: 100%;
    padding: 12px 14px;
    font-size: 16px;
  }
  .search-input { padding: 12px 14px 12px 36px; }
  .filter-row {
    flex-wrap: wrap;
    gap: 8px;
  }
  .filter-group {
    flex: 1;
    min-width: calc(50% - 8px);
  }
  .filter-group select {
    width: 100%;
    min-width: 0;
    padding: 10px 28px 10px 10px;
    font-size: 14px;
  }
  .clear-btn {
    width: 100%;
    text-align: center;
    padding: 12px;
    min-height: 44px;
    font-size: 14px;
  }
  .filter-chip {
    font-size: 12px;
    padding: 6px 10px 6px 12px;
  }
  .batch-bar { padding: 10px 14px; }
  .batch-btn { padding: 8px 16px; min-height: 40px; font-size: 13px; }
  .recipe-grid {
    padding: 14px;
    gap: 14px;
  }
}
</style>
