<template>
  <div class="layout">
    <!-- 顶部主导航（RAGFlow 式：水平主菜单 + 右侧用户区） -->
    <el-header class="header">
      <div class="header-left">
        <!-- 窄屏汉堡按钮 -->
        <el-icon class="menu-toggle" :size="22" @click="drawerVisible = true" aria-label="打开导航菜单" role="button" tabindex="0" @keydown.enter="drawerVisible = true">
          <Menu />
        </el-icon>
        <div class="logo" @click="$router.push('/')">
          <span>LINK</span>
        </div>
        <el-menu
          v-if="!isNarrow"
          :default-active="$route.path"
          mode="horizontal"
          router
          class="top-menu"
        >
          <el-menu-item v-for="item in visibleMenus" :key="item.path" :index="item.path">
            <el-icon><component :is="item.icon" /></el-icon>
            <span>{{ item.title }}</span>
          </el-menu-item>
        </el-menu>
      </div>
      <div class="header-right">
        <!-- 消息铃铛：下拉预览最近消息（阶段三） -->
        <el-popover
          v-model:visible="bellVisible"
          placement="bottom-end"
          :width="340"
          trigger="click"
          popper-class="bell-pop"
          @show="loadRecent"
        >
          <template #reference>
            <el-badge :value="messageStore.unreadCount" :hidden="messageStore.unreadCount === 0" class="bell" aria-label="消息通知">
              <el-icon :size="20"><Bell /></el-icon>
            </el-badge>
          </template>
          <div class="bell-preview">
            <div class="bell-head">
              <span>最近消息</span>
              <el-link type="primary" @click="goMessages">查看全部</el-link>
            </div>
            <div v-if="recentLoading" class="bell-tip">加载中…</div>
            <div v-else-if="recentMessages.length === 0" class="bell-tip">暂无消息</div>
            <div
              v-for="m in recentMessages"
              :key="m.id"
              class="bell-item"
              :class="{ unread: m.isRead === 0 }"
              @click="openMessage(m)"
            >
              <span class="bell-dot" aria-hidden="true" />
              <div class="bell-body">
                <div class="bell-content">{{ m.msgContent }}</div>
                <div class="bell-time">{{ (m.createTime || '').slice(5, 16) }}</div>
              </div>
            </div>
          </div>
        </el-popover>
        <!-- 用户下拉 -->
        <el-dropdown @command="onUserCommand" trigger="click">
          <span class="user-info" aria-label="用户菜单">
            <el-avatar :size="28" class="avatar">{{ userStore.realName?.[0] || 'U' }}</el-avatar>
            <span class="user-name hide-narrow">{{ userStore.realName }}</span>
            <el-tag size="small" effect="plain" round class="hide-narrow">{{ userStore.role }}</el-tag>
            <el-icon class="hide-narrow"><ArrowDown /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="pwd">
                <el-icon><Lock /></el-icon>修改密码
              </el-dropdown-item>
              <el-dropdown-item v-if="userStore.hasRole(['管理员'])" command="nodeTemplates">
                <el-icon><Grid /></el-icon>节点模板
              </el-dropdown-item>
              <el-dropdown-item v-if="userStore.hasRole(['管理员'])" command="aiConfig">
                <el-icon><MagicStick /></el-icon>AI 设置
              </el-dropdown-item>
              <el-dropdown-item v-if="userStore.hasRole(['管理员'])" command="logs">
                <el-icon><Document /></el-icon>审计日志
              </el-dropdown-item>
              <el-dropdown-item command="logout" divided>
                <el-icon><SwitchButton /></el-icon>退出登录
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </el-header>

    <!-- 主内容区（内层路由同样走 page-fade 过渡） -->
    <el-main class="main">
      <router-view v-slot="{ Component }">
        <transition name="page-fade" mode="out-in">
          <component :is="Component" :key="$route.fullPath" />
        </transition>
      </router-view>
    </el-main>

    <!-- 窄屏抽屉导航 -->
    <el-drawer v-model="drawerVisible" direction="ltr" size="260px" :with-header="false" class="nav-drawer">
      <div class="drawer-head">
        <div class="logo">
          <span>LINK</span>
        </div>
      </div>
      <el-menu :default-active="$route.path" router class="drawer-menu">
        <el-menu-item v-for="item in visibleMenus" :key="item.path" :index="item.path" @click="drawerVisible = false">
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.title }}</span>
        </el-menu-item>
      </el-menu>
    </el-drawer>

    <!-- 修改密码弹窗 -->
    <el-dialog v-model="pwdDialogVisible" title="修改密码" width="min(400px, 92vw)">
      <el-form :model="pwdForm" label-width="80px">
        <el-form-item label="原密码">
          <el-input v-model="pwdForm.oldPassword" type="password" show-password />
        </el-form-item>
        <el-form-item label="新密码">
          <el-input v-model="pwdForm.newPassword" type="password" show-password />
        </el-form-item>
        <el-form-item label="确认新密码">
          <el-input v-model="pwdForm.confirmPassword" type="password" show-password placeholder="请再次输入新密码" @keyup.enter="submitPwd" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="pwdDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="pwdLoading" @click="submitPwd">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ArrowDown, Bell, Collection, DataAnalysis, Document, Files,
  FolderOpened, Grid, Lock, MagicStick, Menu, SwitchButton, User, UserFilled
} from '@element-plus/icons-vue'
import request from '@/utils/request'
import { markRead, myMessages } from '@/api/message'
import { useMessageStore } from '@/stores/message'
import { useUserStore } from '@/stores/user'
import { useIsMobile } from '@/composables/useIsMobile'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const messageStore = useMessageStore()

// 窄屏（<900px）：顶栏菜单收进抽屉
const { isMobile: isNarrow } = useIsMobile(900)
const drawerVisible = ref(false)

// 顶部主菜单（V1.4：去掉侧边栏，改顶部主导航）
const menus = [
  { path: '/projects', title: '项目', icon: FolderOpened, roles: null },
  { path: '/customers', title: '客户', icon: UserFilled, roles: null },
  { path: '/templates', title: '模板', icon: Collection, roles: null },
  { path: '/files', title: '文件', icon: Files, roles: null },
  { path: '/messages', title: '消息', icon: Bell, roles: null },
  { path: '/reports', title: '报表', icon: DataAnalysis, roles: ['管理员'] },
  { path: '/system/users', title: '用户管理', icon: User, roles: ['管理员'] }
]
const visibleMenus = computed(() => menus.filter((m) => userStore.hasRole(m.roles)))

// 路由变化时刷新未读数
watch(() => route.path, () => messageStore.fetchUnread())

// ---- 消息中心增强（阶段三）：30s 轮询（页面不可见暂停）+ 铃铛预览 ----
const bellVisible = ref(false)
const recentMessages = ref([])
const recentLoading = ref(false)
let unreadTimer = null

async function loadRecent() {
  recentLoading.value = true
  try {
    const data = await myMessages({ pageNum: 1, pageSize: 5 })
    recentMessages.value = data.items || []
  } finally {
    recentLoading.value = false
  }
}

async function openMessage(m) {
  if (m.isRead === 0) {
    await markRead({ messageId: m.id }).catch(() => {})
    m.isRead = 1
    messageStore.fetchUnread()
  }
  bellVisible.value = false
  if (m.projectId) router.push(`/projects/${m.projectId}`)
  else router.push('/messages')
}

function goMessages() {
  bellVisible.value = false
  router.push('/messages')
}

function startUnreadPolling() {
  stopUnreadPolling()
  unreadTimer = setInterval(() => {
    // 页面不可见时不轮询，节省请求
    if (document.visibilityState === 'visible') messageStore.fetchUnread()
  }, 30000)
}
function stopUnreadPolling() {
  if (unreadTimer) {
    clearInterval(unreadTimer)
    unreadTimer = null
  }
}
function onVisibilityChange() {
  if (document.visibilityState === 'visible') messageStore.fetchUnread()
}

onMounted(() => {
  messageStore.fetchUnread()
  startUnreadPolling()
  document.addEventListener('visibilitychange', onVisibilityChange)
})
onBeforeUnmount(() => {
  stopUnreadPolling()
  document.removeEventListener('visibilitychange', onVisibilityChange)
})

// 修改密码
const pwdDialogVisible = ref(false)
const pwdLoading = ref(false)
const pwdForm = reactive({ oldPassword: '', newPassword: '', confirmPassword: '' })

async function submitPwd() {
  if (!pwdForm.oldPassword || !pwdForm.newPassword || !pwdForm.confirmPassword) {
    ElMessage.warning('请输入原密码、新密码并确认新密码')
    return
  }
  if (pwdForm.newPassword !== pwdForm.confirmPassword) {
    ElMessage.warning('两次输入的新密码不一致')
    return
  }
  pwdLoading.value = true
  try {
    await request.post('/user/updateMyPwd', pwdForm)
    ElMessage.success('密码修改成功')
    pwdDialogVisible.value = false
    pwdForm.oldPassword = ''
    pwdForm.newPassword = ''
    pwdForm.confirmPassword = ''
  } finally {
    pwdLoading.value = false
  }
}

async function onUserCommand(cmd) {
  if (cmd === 'pwd') {
    pwdDialogVisible.value = true
  } else if (cmd === 'nodeTemplates') {
    router.push('/system/nodeTemplates')
  } else if (cmd === 'aiConfig') {
    router.push('/system/aiConfig')
  } else if (cmd === 'logs') {
    router.push('/system/logs')
  } else if (cmd === 'logout') {
    await ElMessageBox.confirm('确定退出登录吗？', '提示', { type: 'warning' })
    userStore.logout()
    router.push('/login')
  }
}
</script>

<style scoped>
.layout { min-height: 100vh; background: var(--lk-bg-page); }
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: var(--lk-header-height);
  padding: 0 clamp(12px, 2vw, 24px);
  background: var(--lk-bg-card);
  border-bottom: 1px solid var(--lk-border-light);
  box-shadow: var(--lk-shadow-sm);
  position: sticky;
  top: 0;
  z-index: 100;
}
.header-left {
  display: flex;
  align-items: center;
  gap: 32px;
  flex: 1;
  min-width: 0;
}
.logo {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 17px;
  font-weight: bold;
  color: var(--lk-text-1);
  cursor: pointer;
  white-space: nowrap;
  flex-shrink: 0;
}
.top-menu {
  flex: 1;
  min-width: 0;
  border-bottom: none !important;
}
.top-menu :deep(.el-menu-item) {
  height: 60px;
  line-height: 60px;
  padding: 0 16px;
  font-size: 14px;
}
.top-menu :deep(.el-menu-item.is-active) {
  color: var(--lk-primary);
  border-bottom: 2px solid var(--lk-primary);
  background: transparent;
}
.header-right {
  display: flex;
  align-items: center;
  gap: 20px;
  flex-shrink: 0;
}
.bell { cursor: pointer; display: flex; align-items: center; }
.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 6px;
  transition: background 0.15s;
}
.user-info:hover { background: var(--lk-bg-hover); }
.avatar { background: var(--lk-primary); color: #fff; font-size: 13px; }
.user-name { font-size: 14px; color: var(--lk-text-1); }
.main { padding: var(--lk-main-padding); background: var(--lk-bg-page); }

/* ---- 响应式：<900px 汉堡菜单 + 抽屉 ---- */
.menu-toggle {
  display: none;
  cursor: pointer;
  color: var(--lk-text-2, #606266);
  border-radius: 6px;
  padding: 4px;
  flex-shrink: 0;
}
.menu-toggle:hover { background: var(--lk-bg-hover, #f5f7fa); }
.drawer-head {
  display: flex;
  align-items: center;
  padding: 14px 8px;
  border-bottom: 1px solid var(--lk-border-light, #e4e7ed);
  margin-bottom: 8px;
}
.drawer-menu { border-right: none; }

@media (max-width: 899px) {
  .menu-toggle { display: inline-flex; }
  .header-left { gap: 8px; }
  .hide-narrow { display: none !important; }
  .header-right { gap: 10px; }
  .top-menu { display: none; }
}
</style>

<!-- 铃铛预览 popover 样式（挂载于 body，须为全局样式） -->
<style>
.bell-pop { padding: 0 !important; border-radius: 12px; overflow: hidden; }
.bell-preview { max-height: 400px; overflow-y: auto; }
.bell-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  border-bottom: 1px solid var(--lk-border-light, #e4e7ed);
  font-size: 14px;
  font-weight: 600;
  color: var(--lk-text-1, #1f2937);
}
.bell-tip { text-align: center; color: var(--lk-text-3, #909399); font-size: 13px; padding: 28px 0; }
.bell-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 14px;
  cursor: pointer;
  transition: background 0.15s;
}
.bell-item:hover { background: var(--lk-bg-hover, #f5f7fa); }
.bell-item.unread .bell-content { font-weight: 600; color: var(--lk-text-1, #303133); }
.bell-dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: var(--lk-border-light, #e4e7ed);
  margin-top: 6px; flex-shrink: 0;
}
.bell-item.unread .bell-dot { background: var(--lk-primary, #409eff); }
.bell-body { flex: 1; min-width: 0; }
.bell-content { font-size: 13px; color: var(--lk-text-2, #606266); line-height: 1.5; word-break: break-all; }
.bell-time { font-size: 12px; color: var(--lk-text-3, #909399); margin-top: 3px; }
</style>
