<script setup>
import { ref } from 'vue'
import { login, register, setToken } from '../api/index.js'

const emit = defineEmits(['authenticated'])

const isLogin = ref(true)
const username = ref('')
const password = ref('')
const loading = ref(false)
const errorMsg = ref('')

function toggleMode() {
  isLogin.value = !isLogin.value
  errorMsg.value = ''
}

async function handleSubmit() {
  const name = username.value.trim()
  const pw = password.value
  if (!name) { errorMsg.value = '请输入用户名'; return }
  if (pw.length < 6) { errorMsg.value = '密码至少 6 位'; return }

  loading.value = true
  errorMsg.value = ''
  try {
    const fn = isLogin.value ? login : register
    const res = await fn(name, pw)
    setToken(res.token)
    emit('authenticated', res.user)
  } catch (e) {
    errorMsg.value = e.message
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="auth-screen">
    <div class="auth-card">
      <div class="auth-header">
        <span class="auth-icon">🍳</span>
        <h1>小斐的专属私厨助手</h1>
        <p class="auth-subtitle">{{ isLogin ? '登录' : '注册' }}后即可使用</p>
      </div>

      <form class="auth-form" @submit.prevent="handleSubmit">
        <div class="field">
          <label for="username">用户名</label>
          <input
            id="username"
            v-model="username"
            type="text"
            placeholder="请输入用户名"
            autocomplete="username"
            maxlength="50"
          />
        </div>
        <div class="field">
          <label for="password">密码</label>
          <input
            id="password"
            v-model="password"
            type="password"
            placeholder="至少 6 位密码"
            autocomplete="current-password"
          />
        </div>

        <p v-if="errorMsg" class="error-msg">{{ errorMsg }}</p>

        <button type="submit" class="submit-btn" :disabled="loading">
          {{ loading ? '处理中...' : isLogin ? '登录' : '注册' }}
        </button>
      </form>

      <p class="toggle-text">
        {{ isLogin ? '还没有账号？' : '已有账号？' }}
        <button class="link-btn" @click="toggleMode">
          {{ isLogin ? '去注册' : '去登录' }}
        </button>
      </p>
    </div>
  </div>
</template>

<style scoped>
.auth-screen {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100dvh;
  min-height: 100vh;
  background: var(--color-bg);
  padding: 20px;
  padding-top: max(20px, var(--safe-top, 0px));
  padding-bottom: max(20px, var(--safe-bottom, 0px));
}

.auth-card {
  width: 100%;
  max-width: 380px;
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 40px 32px;
  box-shadow: 0 4px 24px rgba(0,0,0,0.06);
}

.auth-header {
  text-align: center;
  margin-bottom: 32px;
}

.auth-icon {
  font-size: 48px;
  display: block;
  margin-bottom: 12px;
}

.auth-header h1 {
  font-size: 22px;
  font-weight: 600;
  margin: 0 0 6px 0;
  color: var(--color-text);
}

.auth-subtitle {
  font-size: 14px;
  color: var(--color-text-muted);
  margin: 0;
}

.auth-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.field label {
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-secondary);
}

.field input {
  padding: 12px 14px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: 16px !important;
  color: var(--color-text);
  background: var(--color-bg);
  outline: none;
  font-family: var(--font-sans);
  transition: border-color 0.2s;
  -webkit-appearance: none;
  appearance: none;
}

.field input:focus {
  border-color: var(--color-primary);
}

.error-msg {
  font-size: 13px;
  color: var(--color-danger);
  margin: 0;
  text-align: center;
}

.submit-btn {
  padding: 14px 0;
  background: var(--color-primary);
  color: #fff;
  border: none;
  border-radius: var(--radius-md);
  font-size: 16px;
  font-weight: 500;
  cursor: pointer;
  font-family: var(--font-sans);
  transition: background 0.2s;
  min-height: 48px;
  -webkit-tap-highlight-color: transparent;
}

.submit-btn:active {
  background: var(--color-primary-hover);
}

.submit-btn:disabled {
  opacity: 0.6;
  cursor: default;
}

.toggle-text {
  text-align: center;
  font-size: 13px;
  color: var(--color-text-muted);
  margin-top: 20px;
  margin-bottom: 0;
}

.link-btn {
  background: none;
  border: none;
  color: var(--color-primary);
  cursor: pointer;
  font-size: 13px;
  font-family: var(--font-sans);
  padding: 0;
  text-decoration: underline;
  min-height: 44px;
  -webkit-tap-highlight-color: transparent;
}

.link-btn:active {
  color: var(--color-primary-hover);
}

@media (max-width: 480px) {
  .auth-screen {
    padding: 16px;
    padding-top: max(16px, var(--safe-top, 0px));
    padding-bottom: max(16px, var(--safe-bottom, 0px));
    align-items: flex-start;
    padding-top: max(40px, var(--safe-top, 0px));
  }
  .auth-card {
    padding: 28px 20px;
    border-radius: var(--radius-md);
  }
  .auth-header h1 {
    font-size: 20px;
  }
  .auth-icon {
    font-size: 40px;
  }
}
</style>
