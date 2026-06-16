# AI 私厨助手 (AI Chef Assistant)

基于 LangChain + FastAPI + Vue 3 的智能菜谱推荐助手。上传食材照片或输入食材清单，AI 自动推荐菜谱并提供烹饪指导。

## 功能特性

- **智能对话** — 通过 LangGraph Agent 与用户交互，理解食材信息并推荐菜谱
- **图片识别** — 上传食材照片，AI 自动识别并推荐可做菜品
- **菜谱推荐** — 覆盖简单/中等/困难三个难度档次的菜谱，每档推荐 1-2 道
- **菜谱库** — 手动保存喜欢的菜谱，支持搜索、筛选（难度/菜系/口味/食材）和批量管理
- **购物清单** — 选择菜品生成分类购物清单，支持按食材类别归类、勾选已购、跨会话持久保存
- **饮食档案** — 记录过敏源、饮食限制和口味偏好，推荐时自动适配
- **季节推荐** — 根据当前时令推荐应季食材和菜谱
- **会话管理** — 历史对话列表、长按菜单（重命名/删除/批量删除）、自动隐藏空对话
- **移动端适配** — 响应式布局、触摸优化、底部弹出式模态框
- **菜品分享** — 生成精美菜品卡片图片，支持分享和下载

## 技术栈

| 层 | 技术 |
|---|---|
| 前端 | Vue 3 (Composition API + `<script setup>`), Vite, SSE 流式接收 |
| 后端 | FastAPI, LangChain, LangGraph Agent |
| 模型 | Qwen 3.7-Plus (菜谱理解/提取) |
| 数据库 | SQLite (会话/消息/菜谱/购物清单/饮食档案) |
| 搜索 | Tavily API (菜谱搜索与图片) |

## 快速开始

### 环境准备

```bash
# 后端
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 前端
cd frontend
npm install
```

### 配置环境变量

创建 `.env` 文件：

```env
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
DASHSCOPE_API_KEY=your_dashscope_api_key
TAVILY_API_KEY=your_tavily_api_key
```

### 启动服务

```bash
# 终端 1：启动后端
uvicorn app.main:app --reload --port 8000

# 终端 2：启动前端开发服务器
cd frontend
npm run dev
```

访问 `http://localhost:5173` 即可使用。

### 生产构建

```bash
cd frontend
npm run build
```

构建后前端文件生成在 `frontend/dist/`，FastAPI 会自动 serve 该目录（SPA 回退）。

## 项目结构

```
langchain/
├── app/                    # FastAPI 后端
│   ├── api/
│   │   └── chef.py         # API 路由（会话、聊天、菜谱库、购物清单等）
│   ├── agents/
│   │   └── project.py      # LangGraph Agent 构建
│   ├── db.py               # SQLite 数据库层
│   ├── main.py             # FastAPI 应用入口
│   └── seasonal.py         # 季节性食材推荐
├── frontend/               # Vue 3 前端
│   └── src/
│       ├── App.vue         # 根组件
│       ├── api/index.js    # API 客户端
│       ├── components/     # Vue 组件
│       │   ├── ChatView.vue        # 聊天视图
│       │   ├── ChatInput.vue       # 输入框（文本+图片）
│       │   ├── RecipeCard.vue      # 菜谱卡片
│       │   ├── RecipeLibrary.vue   # 菜谱库
│       │   ├── SessionSidebar.vue  # 会话侧边栏
│       │   ├── ShoppingList.vue    # 购物清单弹窗
│       │   ├── ShoppingListPage.vue # 购物清单页面
│       │   ├── DietaryProfile.vue  # 饮食档案
│       │   └── StepReader.vue      # 步骤阅读模式
│       └── style.css       # 全局样式
├── model_config.py         # LLM 模型配置
├── tools.py                # Agent 工具（搜索）
└── .env                    # 环境变量（API Keys）
```

## API 概览

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/sessions` | 创建会话 |
| GET | `/api/sessions` | 会话列表 |
| GET | `/api/sessions/{id}` | 获取会话及消息 |
| PUT | `/api/sessions/{id}` | 重命名会话 |
| DELETE | `/api/sessions/{id}` | 删除会话 |
| POST | `/api/sessions/batch-delete` | 批量删除会话 |
| POST | `/api/chat/{session_id}` | 发送消息（SSE 流式返回） |
| GET | `/api/recipes` | 菜谱库列表（支持搜索/筛选） |
| POST | `/api/recipes` | 手动保存菜谱 |
| DELETE | `/api/recipes/{id}` | 删除菜谱 |
| POST | `/api/recipes/batch-delete` | 批量删除菜谱 |
| GET/POST | `/api/shopping-lists` | 购物清单列表/创建 |
| GET/PUT/DELETE | `/api/shopping-lists/{id}` | 购物清单详情/更新/删除 |
| GET/PUT | `/api/dietary-profile` | 饮食档案 |
| POST | `/api/upload` | 上传图片 |
