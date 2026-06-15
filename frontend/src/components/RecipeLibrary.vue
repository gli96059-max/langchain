<script setup>
import { ref, onMounted } from 'vue'
import RecipeCard from './RecipeCard.vue'
import { listRecipes } from '../api/index.js'

const emit = defineEmits(['close'])

const recipes = ref([])
const loading = ref(true)

onMounted(async () => {
  try {
    recipes.value = await listRecipes()
  } catch { /* ignore */ }
  loading.value = false
})
</script>

<template>
  <div class="library">
    <div class="library-header">
      <button class="back-btn" @click="emit('close')">← 返回</button>
      <h2>📚 菜谱库</h2>
      <span class="recipe-count">{{ recipes.length }} 道菜</span>
    </div>

    <div v-if="loading" class="loading">加载中...</div>
    <div v-else-if="!recipes.length" class="empty">
      <p>暂无收藏的菜谱，开始对话后推荐的菜谱会自动保存到这里</p>
    </div>
    <div v-else class="recipe-grid">
      <RecipeCard
        v-for="(item, i) in recipes"
        :key="item.id || i"
        :recipe="item.recipe_data || item"
      />
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
}
</style>
