<script setup>
import { ref, computed, watch } from 'vue'
import { saveShoppingList } from '../api/index.js'

const props = defineProps({
  visible: { type: Boolean, default: false },
  recipes: { type: Array, default: () => [] },
})
const emit = defineEmits(['close'])

// ── Categorisation ─────────────────────────────────────

const CATEGORIES = [
  { name: '🥬 蔬菜', keys: ['菜', '瓜', '萝卜', '番茄', '土豆', '茄', '笋', '菌', '菇', '耳', '藕', '山药', '芋', '芹', '菠', '莴', '芦笋'] },
  { name: '🍎 水果', keys: ['果', '蕉', '桃', '梨', '橙', '橘', '柚', '莓', '枣', '柿', '芒'] },
  { name: '🥩 肉类', keys: ['肉', '鸡', '鸭', '鹅', '猪', '牛', '羊', '排骨', '里脊', '五花', '腿', '翅', '爪', '肝', '肠', '肚', '腰', '心', '舌', '腊'] },
  { name: '🦐 海鲜', keys: ['鱼', '虾', '蟹', '贝', '蛤', '蛏', '蚝', '鱿鱼', '章鱼', '海带', '紫菜', '鲍鱼', '海参', '带子'] },
  { name: '🥛 蛋奶', keys: ['蛋', '奶', '酪', '黄油', '奶油', '芝士', '酸奶'] },
  { name: '🌾 主食/豆制品', keys: ['米', '饭', '粉', '面', '饼', '馒', '包', '饺', '豆', '腐', '千张', '面筋', '年糕', '燕麦'] },
  { name: '🧂 调味料', keys: ['盐', '糖', '酱', '油', '醋', '酒', '椒', '辣', '麻', '香', '桂', '八', '生', '蚝', '淀', '粉', '姜', '蒜', '葱', '芝', '胡', '料', '豉', '卤'] },
  { name: '🫙 干货/其他', keys: [] },
]

// Priority match: returns first matching category (or 干货/其他 as fallback)
function categorize(name) {
  const n = name.toLowerCase()
  for (let i = 0; i < CATEGORIES.length - 1; i++) {
    if (CATEGORIES[i].keys.some(k => n.includes(k))) return CATEGORIES[i].name
  }
  return CATEGORIES[CATEGORIES.length - 1].name
}

// ── State ──────────────────────────────────────────────

const selectedNames = ref(new Set())
const removedIngs = ref(new Set())       // Set<lowercase name>
const checkedIngs = ref(new Set())       // Set<lowercase name>

function resetState() {
  selectedNames.value = new Set(props.recipes.map(r => r.name))
  removedIngs.value = new Set()
  checkedIngs.value = new Set()
}

watch(() => props.visible, (v) => { if (v) resetState() })
watch(() => props.recipes, (r) => { if (props.visible) resetState() })

function toggleRecipe(name) {
  const next = new Set(selectedNames.value)
  next.has(name) ? next.delete(name) : next.add(name)
  selectedNames.value = next
}
function selectAll() { selectedNames.value = new Set(props.recipes.map(r => r.name)) }
function deselectAll() { selectedNames.value = new Set() }

function removeIng(key) {
  const next = new Set(removedIngs.value)
  next.add(key)
  removedIngs.value = next
}
function restoreAllRemoved() { removedIngs.value = new Set() }

function toggleCheck(key) {
  const next = new Set(checkedIngs.value)
  next.has(key) ? next.delete(key) : next.add(key)
  checkedIngs.value = next
}

// ── Computed ───────────────────────────────────────────

const selectedRecipes = computed(() =>
  props.recipes.filter(r => selectedNames.value.has(r.name))
)

const allIngredients = computed(() => {
  const seen = new Map()
  for (const r of selectedRecipes.value) {
    if (!r.ingredients) continue
    for (const ing of r.ingredients) {
      const key = ing.trim().toLowerCase()
      if (!seen.has(key)) {
        seen.set(key, { text: ing.trim(), sources: [r.name], category: categorize(key) })
      } else {
        const entry = seen.get(key)
        if (!entry.sources.includes(r.name)) entry.sources.push(r.name)
      }
    }
  }
  return Array.from(seen.values())
})

const activeIngredients = computed(() =>
  allIngredients.value.filter(i => !removedIngs.value.has(i.text.toLowerCase()))
)

const groupedIngredients = computed(() => {
  const groups = new Map()
  for (const item of activeIngredients.value) {
    const cat = item.category
    if (!groups.has(cat)) groups.set(cat, [])
    groups.get(cat).push(item)
  }
  // Return in category order
  const result = []
  for (const cat of CATEGORIES) {
    const items = groups.get(cat.name)
    if (items && items.length > 0) {
      const done = items.filter(i => checkedIngs.value.has(i.text.toLowerCase())).length
      result.push({ name: cat.name, items, total: items.length, done })
    }
  }
  return result
})

const totalCount = computed(() => activeIngredients.value.length)
const checkedCount = computed(() => activeIngredients.value.filter(i => checkedIngs.value.has(i.text.toLowerCase())).length)
const removedCount = computed(() => allIngredients.value.length - totalCount.value)
const anyRemoved = computed(() => removedCount.value > 0)

const copyText = computed(() => {
  const lines = ['🛒 购物清单', '─'.repeat(18)]
  for (const group of groupedIngredients.value) {
    if (!group.items.length) continue
    lines.push('', group.name)
    for (const item of group.items) {
      const done = checkedIngs.value.has(item.text.toLowerCase())
      lines.push(`${done ? '☑' : '□'} ${item.text}`)
    }
  }
  lines.push('', '─'.repeat(18), `已购: ${checkedCount.value}/${totalCount.value}`)
  return lines.join('\n')
})

function doCopy() {
  navigator.clipboard.writeText(copyText.value)
}

const savedHint = ref('')

async function doSave() {
  const active = activeIngredients.value
  if (!active.length) return

  // Auto-generate a list name from recipe names
  const recipeNames = selectedRecipes.value.map(r => r.name)
  const name = recipeNames.length <= 2
    ? recipeNames.join('、')
    : recipeNames.slice(0, 2).join('、') + ` 等${recipeNames.length}道菜`

  const items = active.map(i => ({
    text: i.text,
    category: i.category,
    source_recipe: i.sources[0] || '',
    checked: false,
  }))

  try {
    await saveShoppingList(name, '', items)
    savedHint.value = '已保存到购物清单'
    setTimeout(() => { savedHint.value = '' }, 2000)
  } catch { savedHint.value = '保存失败' }
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
          <!-- Recipe selection -->
          <div class="section">
            <div class="section-header">
              <span class="section-title">选择菜品</span>
              <span class="recipe-action" @click="selectedNames.size === recipes.length ? deselectAll() : selectAll()">
                {{ selectedNames.size === recipes.length ? '取消全选' : '全选' }}
              </span>
            </div>
            <div class="recipe-chips">
              <button
                v-for="r in recipes"
                :key="r.name"
                class="recipe-chip"
                :class="{ checked: selectedNames.has(r.name) }"
                @click="toggleRecipe(r.name)"
              >
                <span class="chip-check">{{ selectedNames.has(r.name) ? '☑' : '☐' }}</span>
                <span class="chip-name">{{ r.name }}</span>
              </button>
            </div>
            <div class="selected-hint" v-if="!selectedRecipes.length">请至少选择一道菜品</div>
          </div>

          <!-- Ingredient list -->
          <div class="section" v-if="selectedRecipes.length">
            <div class="section-header">
              <span class="section-title">
                食材清单
                <span class="progress" v-if="totalCount">已购 {{ checkedCount }}/{{ totalCount }}</span>
              </span>
            </div>

            <div v-if="!allIngredients.length" class="empty-hint">所选菜品暂无食材信息</div>
            <div v-else-if="!totalCount" class="empty-hint">已去掉全部食材，选点啥带上吧</div>
            <div v-else class="cats-wrap">
              <div v-for="group in groupedIngredients" :key="group.name" class="cat-group">
                <div class="cat-header">
                  <span>{{ group.name }}</span>
                  <span class="cat-count">{{ group.done }}/{{ group.total }}</span>
                </div>
                <div
                  v-for="item in group.items"
                  :key="item.text"
                  class="ing-item"
                  :class="{ checked: checkedIngs.has(item.text.toLowerCase()) }"
                  @click="toggleCheck(item.text.toLowerCase())"
                >
                  <span class="ing-check">{{ checkedIngs.has(item.text.toLowerCase()) ? '☑' : '□' }}</span>
                  <span class="ing-text">{{ item.text }}</span>
                  <span class="ing-source" v-if="item.sources.length > 1 && !checkedIngs.has(item.text.toLowerCase())">
                    {{ item.sources.join('、') }}
                  </span>
                  <span class="ing-source single" v-else-if="!checkedIngs.has(item.text.toLowerCase())">
                    {{ item.sources[0] }}
                  </span>
                  <button
                    class="ing-remove"
                    @click.stop="removeIng(item.text.toLowerCase())"
                    title="去掉该食材"
                  >✕</button>
                </div>
              </div>

              <!-- Removed recovery -->
              <div v-if="anyRemoved" class="removed-section">
                <button class="restore-bar" @click="restoreAllRemoved">
                  ＋ 已隐藏 {{ removedCount }} 种食材，点击恢复
                </button>
              </div>
            </div>
          </div>
        </div>

        <div class="modal-footer">
          <span v-if="savedHint" class="save-hint">{{ savedHint }}</span>
          <button class="btn-save" :disabled="!totalCount" @click="doSave">
            💾 保存清单
          </button>
          <button class="btn-copy" :disabled="!totalCount" @click="doCopy">
            📋 复制
          </button>
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
  width: 500px;
  max-width: 92vw;
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
  padding: 12px 22px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* ── Sections ── */

.section { display: flex; flex-direction: column; gap: 8px; }
.section-header { display: flex; align-items: center; justify-content: space-between; }
.section-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.progress {
  font-size: 12px;
  font-weight: 400;
  color: var(--color-primary);
  letter-spacing: 0;
}

.recipe-action {
  font-size: 12px;
  color: var(--color-primary);
  cursor: pointer;
  font-weight: 500;
}
.recipe-action:hover { text-decoration: underline; }

/* ── Recipe chips ── */

.recipe-chips { display: flex; flex-wrap: wrap; gap: 8px; }

.recipe-chip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 8px 14px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-card);
  cursor: pointer;
  font-size: 14px;
  color: var(--color-text);
  font-family: var(--font-sans);
  transition: all 0.15s;
}
.recipe-chip:hover { border-color: var(--color-primary); background: var(--color-primary-light); }
.recipe-chip.checked { border-color: var(--color-primary); background: var(--color-primary-light); }
.chip-check { font-size: 16px; flex-shrink: 0; }
.chip-name { font-weight: 500; }
.selected-hint { font-size: 13px; color: var(--color-text-muted); text-align: center; padding: 8px 0; }

/* ── Ingredient groups ── */

.empty-hint { color: var(--color-text-muted); text-align: center; padding: 12px 0; font-size: 14px; }

.cats-wrap { display: flex; flex-direction: column; gap: 12px; }

.cat-group { display: flex; flex-direction: column; }

.cat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text);
  padding: 4px 8px 2px;
  border-bottom: 1px solid var(--color-border);
  margin-bottom: 2px;
}

.cat-count { font-size: 11px; font-weight: 400; color: var(--color-text-muted); }

.ing-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 7px 8px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background 0.12s;
  user-select: none;
}
.ing-item:hover { background: var(--color-bg); }
.ing-item.checked { opacity: 0.5; }
.ing-item.checked .ing-text { text-decoration: line-through; }

.ing-check { font-size: 16px; color: var(--color-text-muted); flex-shrink: 0; }
.ing-item.checked .ing-check { color: var(--color-primary); }

.ing-text { flex: 1; font-size: 14px; color: var(--color-text); }

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
.ing-source.single { opacity: 0.7; }
.ing-item.checked .ing-source { display: none; }

.ing-remove {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  border: none;
  background: transparent;
  color: var(--color-text-muted);
  font-size: 14px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all 0.15s;
  opacity: 0;
}
.ing-item:hover .ing-remove { opacity: 1; }
.ing-remove:hover { background: rgba(244, 67, 54, 0.1); color: var(--color-danger); }

/* ── Removed ── */

.removed-section { margin-top: 2px; }
.restore-bar {
  width: 100%;
  padding: 8px;
  background: none;
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-sm);
  font-size: 12px;
  color: var(--color-text-muted);
  cursor: pointer;
  font-family: var(--font-sans);
  transition: all 0.15s;
}
.restore-bar:hover { border-color: var(--color-primary); color: var(--color-primary); background: var(--color-primary-light); }

/* ── Footer ── */

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
  display: flex;
  align-items: center;
  gap: 5px;
}
.btn-copy:hover { background: var(--color-bg); }
.btn-copy:disabled { opacity: 0.4; cursor: default; }

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
.btn-close:hover { background: var(--color-primary-hover); }

.save-hint {
  font-size: 13px;
  color: var(--color-success);
  font-weight: 500;
  flex: 1;
  text-align: left;
}

.btn-save {
  padding: 8px 18px;
  border: 1px solid var(--color-primary);
  background: var(--color-primary-light);
  color: var(--color-primary);
  border-radius: var(--radius-sm);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  font-family: var(--font-sans);
  display: flex;
  align-items: center;
  gap: 4px;
}
.btn-save:hover { background: var(--color-primary); color: #fff; }
.btn-save:disabled { opacity: 0.4; cursor: default; background: var(--color-card); color: var(--color-text-muted); border-color: var(--color-border); }

@media (max-width: 768px) {
  .modal-panel { width: 100vw; max-width: 100vw; max-height: 85vh; border-radius: var(--radius-lg) var(--radius-lg) 0 0; margin-top: auto; }
  .modal-overlay { align-items: flex-end; }
  .modal-header { padding: 16px 18px; }
  .modal-body { padding: 12px 18px; padding-bottom: calc(12px + env(safe-area-inset-bottom, 0px)); }
  .modal-footer { padding: 12px 18px; padding-bottom: calc(12px + env(safe-area-inset-bottom, 0px)); }
  .recipe-chip { padding: 10px 14px; font-size: 14px; }
  .ing-item { padding: 10px 8px; }
  .ing-text { font-size: 15px; }
  .ing-source { max-width: 80px; }
  .ing-remove { width: 32px; height: 32px; font-size: 16px; opacity: 1; }
  .btn-copy, .btn-close { flex: 1; text-align: center; padding: 12px 16px; justify-content: center; }
}
</style>
