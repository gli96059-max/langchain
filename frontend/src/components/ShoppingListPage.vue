<script setup>
import { ref, computed, onMounted } from 'vue'
import { listShoppingLists, getShoppingList, updateShoppingList, deleteShoppingList } from '../api/index.js'

const emit = defineEmits(['close'])

// ── Views ──
// 'list' | 'detail'
const view = ref('list')
const lists = ref([])
const activeList = ref(null)
const loading = ref(false)

// ── List view ──

async function loadLists() {
  loading.value = true
  try { lists.value = await listShoppingLists() }
  catch { /* ignore */ }
  loading.value = false
}

// ── Detail view ──

async function openList(id) {
  loading.value = true
  try {
    activeList.value = await getShoppingList(id)
    view.value = 'detail'
  } catch { /* ignore */ }
  loading.value = false
}

function closeDetail() {
  view.value = 'list'
  activeList.value = null
  loadLists()
}

async function toggleItem(itemKey) {
  if (!activeList.value) return
  const items = activeList.value.items.map(it => ({
    ...it,
    checked: it.text?.toLowerCase() === itemKey ? !it.checked : it.checked,
  }))
  activeList.value = await updateShoppingList(activeList.value.id, items)
}

async function handleDelete(id, e) {
  e.stopPropagation()
  if (!confirm('确定删除该清单？')) return
  await deleteShoppingList(id)
  await loadLists()
}

function listProgress(items) {
  if (!items || !items.length) return { done: 0, total: 0 }
  const done = items.filter(i => i.checked).length
  return { done, total: items.length }
}

function formatTime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  const now = new Date()
  const diff = now - d
  const days = Math.floor(diff / 86400000)
  if (days === 0) return '今天'
  if (days === 1) return '昨天'
  if (days < 7) return `${days}天前`
  return d.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

const activeProgress = computed(() =>
  activeList.value ? listProgress(activeList.value.items) : { done: 0, total: 0 }
)

const groupedItems = computed(() => {
  if (!activeList.value) return []
  const groups = new Map()
  for (const item of activeList.value.items) {
    const cat = item.category || '🫙 其他'
    if (!groups.has(cat)) groups.set(cat, [])
    groups.get(cat).push(item)
  }
  const ORDER = ['🥬 蔬菜', '🍎 水果', '🥩 肉类', '🦐 海鲜', '🥛 蛋奶', '🌾 主食/豆制品', '🧂 调味料', '🫙 干货/其他']
  const result = []
  for (const cat of ORDER) {
    if (groups.has(cat)) {
      const items = groups.get(cat)
      const done = items.filter(i => i.checked).length
      result.push({ name: cat, items, done, total: items.length })
    }
  }
  // Any uncategorized
  for (const [cat, items] of groups) {
    if (!ORDER.includes(cat)) {
      result.push({ name: cat, items, done: items.filter(i => i.checked).length, total: items.length })
    }
  }
  return result
})

onMounted(loadLists)
</script>

<template>
  <div class="sl-page">
    <!-- Header -->
    <div class="sl-header">
      <button class="back-btn" @click="view === 'detail' ? closeDetail() : emit('close')">
        ← {{ view === 'detail' ? '返回清单' : '返回' }}
      </button>
      <h2>🛒 小斐的购物清单</h2>
    </div>

    <!-- List view -->
    <template v-if="view === 'list'">
      <div v-if="loading" class="sl-loading">加载中...</div>
      <div v-else-if="!lists.length" class="sl-empty">
        <p>暂无保存的购物清单</p>
        <p class="sl-empty-hint">在聊天中打开购物清单后，点击"保存清单"即可保存到这里</p>
      </div>
      <div v-else class="sl-list">
        <div
          v-for="lst in lists"
          :key="lst.id"
          class="sl-card"
          @click="openList(lst.id)"
        >
          <div class="sl-card-top">
            <span class="sl-card-title">{{ lst.name }}</span>
            <button class="sl-card-delete" @click="(e) => handleDelete(lst.id, e)" title="删除">✕</button>
          </div>
          <div class="sl-card-meta">
            <span class="sl-card-progress" :class="{ done: listProgress(lst.items).done === listProgress(lst.items).total }">
              {{ listProgress(lst.items).done }}/{{ listProgress(lst.items).total }} 已购
            </span>
            <span class="sl-card-time">{{ formatTime(lst.updated_at) }}</span>
          </div>
          <!-- Mini progress bar -->
          <div class="sl-progress-bar">
            <div
              class="sl-progress-fill"
              :style="{ width: listProgress(lst.items).total ? (listProgress(lst.items).done / listProgress(lst.items).total * 100) + '%' : '0%' }"
            ></div>
          </div>
        </div>
      </div>
    </template>

    <!-- Detail view -->
    <template v-else-if="activeList">
      <div class="sl-detail-header">
        <div class="sl-detail-title">{{ activeList.name }}</div>
        <div class="sl-detail-progress">
          已购 {{ activeProgress.done }}/{{ activeProgress.total }}
        </div>
        <div class="sl-progress-bar">
          <div class="sl-progress-fill" :style="{ width: activeProgress.total ? (activeProgress.done / activeProgress.total * 100) + '%' : '0%' }"></div>
        </div>
      </div>

      <div class="sl-detail-body">
        <div v-for="group in groupedItems" :key="group.name" class="sl-group">
          <div class="sl-group-header">
            <span>{{ group.name }}</span>
            <span class="sl-group-count">{{ group.done }}/{{ group.total }}</span>
          </div>
          <div
            v-for="item in group.items"
            :key="item.text"
            class="sl-item"
            :class="{ checked: item.checked }"
            @click="toggleItem(item.text?.toLowerCase())"
          >
            <span class="sl-item-check">{{ item.checked ? '☑' : '□' }}</span>
            <span class="sl-item-text">{{ item.text }}</span>
            <span v-if="item.source_recipe && !item.checked" class="sl-item-src">{{ item.source_recipe }}</span>
          </div>
        </div>

        <button class="sl-delete-btn" @click="handleDelete(activeList.id, $event)">
          删除清单
        </button>
      </div>
    </template>
  </div>
</template>

<style scoped>
.sl-page {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.sl-header {
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
.back-btn:hover { background: var(--color-bg); }

.sl-header h2 {
  flex: 1;
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

/* ── List view ── */

.sl-loading, .sl-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--color-text-muted);
  padding: 40px 20px;
  text-align: center;
}
.sl-empty-hint { font-size: 13px; margin-top: 8px; opacity: 0.7; }

.sl-list {
  flex: 1;
  overflow-y: auto;
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-width: 600px;
  margin: 0 auto;
  width: 100%;
}

.sl-card {
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 14px 16px;
  cursor: pointer;
  transition: box-shadow 0.15s;
}
.sl-card:hover { box-shadow: var(--shadow-md); }

.sl-card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.sl-card-title { font-size: 15px; font-weight: 600; color: var(--color-text); }

.sl-card-delete {
  background: none;
  border: none;
  font-size: 14px;
  color: var(--color-text-muted);
  cursor: pointer;
  padding: 4px;
  border-radius: 50%;
  line-height: 1;
}
.sl-card-delete:hover { background: rgba(244,67,54,0.1); color: var(--color-danger); }

.sl-card-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 6px;
  font-size: 12px;
}
.sl-card-progress { color: var(--color-primary); font-weight: 500; }
.sl-card-progress.done { color: var(--color-success); }
.sl-card-time { color: var(--color-text-muted); }

.sl-progress-bar {
  height: 4px;
  background: var(--color-border);
  border-radius: 2px;
  margin-top: 8px;
  overflow: hidden;
}
.sl-progress-fill {
  height: 100%;
  background: var(--color-primary);
  border-radius: 2px;
  transition: width 0.3s ease;
}
.sl-progress-fill.done { background: var(--color-success); }

/* ── Detail view ── */

.sl-detail-header {
  padding: 16px 20px;
  border-bottom: 1px solid var(--color-border);
}
.sl-detail-title { font-size: 18px; font-weight: 600; color: var(--color-text); }
.sl-detail-progress { font-size: 13px; color: var(--color-primary); margin-top: 4px; }

.sl-detail-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px 20px;
  max-width: 600px;
  margin: 0 auto;
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.sl-group { display: flex; flex-direction: column; }
.sl-group-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text);
  padding: 4px 8px 2px;
  border-bottom: 1px solid var(--color-border);
  margin-bottom: 2px;
}
.sl-group-count { font-size: 11px; font-weight: 400; color: var(--color-text-muted); }

.sl-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background 0.1s;
  user-select: none;
}
.sl-item:hover { background: var(--color-bg); }
.sl-item.checked { opacity: 0.5; }
.sl-item.checked .sl-item-text { text-decoration: line-through; }

.sl-item-check { font-size: 16px; color: var(--color-primary); flex-shrink: 0; }
.sl-item-text { flex: 1; font-size: 14px; color: var(--color-text); }

.sl-item-src {
  font-size: 11px;
  color: var(--color-text-muted);
  background: var(--color-bg);
  padding: 2px 8px;
  border-radius: 10px;
  white-space: nowrap;
  max-width: 100px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sl-delete-btn {
  align-self: center;
  margin-top: 8px;
  padding: 8px 24px;
  border: 1px solid var(--color-danger);
  background: none;
  color: var(--color-danger);
  border-radius: var(--radius-sm);
  font-size: 13px;
  cursor: pointer;
  font-family: var(--font-sans);
  transition: all 0.15s;
}
.sl-delete-btn:hover { background: var(--color-danger); color: #fff; }

@media (max-width: 768px) {
  .sl-header { padding: 12px 14px; padding-top: calc(12px + var(--safe-top, 0px)); }
  .sl-header h2 { font-size: 16px; }
  .back-btn { padding: 10px 14px; min-height: 40px; font-size: 14px; }
  .sl-list { padding: 12px 14px; }
  .sl-card { padding: 14px 16px; }
  .sl-card-delete { width: 32px; height: 32px; font-size: 16px; }
  .sl-detail-body { padding: 12px 14px; padding-bottom: calc(12px + var(--safe-bottom, 0px)); }
  .sl-item { padding: 12px 8px; min-height: 44px; }
  .sl-item-text { font-size: 15px; }
  .sl-delete-btn { padding: 12px 24px; min-height: 44px; width: 100%; text-align: center; }
}
</style>
