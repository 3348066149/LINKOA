<template>
  <div class="login-page">
    <div class="login-shell">
      <!-- 左侧品牌区 -->
      <div class="brand-zone">
        <div class="brand-badge">
          <img class="brand-logo" src="/link-icon.png" alt="青岛领客文化传播有限公司" />
        </div>
        <p class="brand-kicker">LINKOA 数字化项目协同平台</p>
        <h1 class="brand-name">青岛领客文化传播有限公司</h1>
        <p class="brand-slogan">品牌与用户如此之近！</p>
        <div class="brand-divider" aria-hidden="true"></div>
        <div class="brand-points">
          <div class="point">
            <el-icon><DataAnalysis /></el-icon>
            <span>项目流程 · 节点把控 · 进度透明</span>
          </div>
          <div class="point">
            <el-icon><UserFilled /></el-icon>
            <span>客户专属门户 · 实时查看项目进度</span>
          </div>
          <div class="point">
            <el-icon><Link /></el-icon>
            <span>团队协作 · 文档沉淀 · 高效交付</span>
          </div>
        </div>
      </div>

      <!-- 右侧登录卡片 -->
      <div class="login-zone">
        <div class="login-card">
          <h2 class="login-title">系统登录</h2>
          <p class="login-sub">请输入账号密码登录系统</p>

          <!-- 内联错误提示：不用弹窗，错误原因直接呈现在表单内 -->
          <div v-if="errorMsg" class="form-alert" role="alert">
            <el-icon><WarningFilled /></el-icon>
            <span>{{ errorMsg }}</span>
          </div>

          <el-form :model="form" @keyup.enter="submit">
            <div class="field" :class="{ 'is-invalid': !!errorMsg }">
              <el-input
                v-model="form.username"
                placeholder="账号"
                size="large"
                :prefix-icon="User"
                autocomplete="username"
                aria-label="账号"
              />
            </div>
            <div class="field" :class="{ 'is-invalid': !!errorMsg }">
              <el-input
                v-model="form.password"
                type="password"
                placeholder="密码"
                size="large"
                show-password
                :prefix-icon="Lock"
                autocomplete="new-password"
                aria-label="密码"
              />
            </div>

            <div class="form-extra">
              <el-checkbox v-model="remember">记住账号</el-checkbox>
              <el-link type="primary" @click="onForgot">忘记密码？</el-link>
            </div>

            <el-button
              type="primary"
              size="large"
              class="login-btn"
              :loading="loading"
              @click="submit"
            >
              {{ loading ? '登录中…' : '登录' }}
            </el-button>
          </el-form>

          <div class="register">
            还没有账号？<el-link type="primary" @click="onRegister">联系管理员创建</el-link>
          </div>
        </div>
      </div>
    </div>

    <!-- 页面底部版权 / 版本 / 浏览器建议 -->
    <div class="page-footer">
      <span>© 2026 青岛领客文化传播有限公司　版权所有</span>
      <span class="dot">·</span>
      <span>V{{ version }}</span>
      <span class="dot">·</span>
      <span>建议使用 Chrome / Edge 浏览器</span>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { DataAnalysis, Link, Lock, User, UserFilled, WarningFilled } from '@element-plus/icons-vue'
import request from '@/utils/request'
import { useUserStore } from '@/stores/user'

/** 记住账号：仅存用户名，不存密码 */
const REMEMBER_KEY = 'linkoa_remember_username'
/** 登录页展示的版本号，与 MD 文档版本保持一致 */
const version = '1.4.17'

const router = useRouter()
const userStore = useUserStore()

const loading = ref(false)
const errorMsg = ref('')
const remember = ref(false)
const form = reactive({ username: '', password: '' })

onMounted(() => {
  const saved = localStorage.getItem(REMEMBER_KEY)
  if (saved) {
    form.username = saved
    remember.value = true
  }
})

// 重新输入时清掉上一次的错误提示，避免红框一直挂着
watch(() => [form.username, form.password], () => {
  if (errorMsg.value) errorMsg.value = ''
})

async function submit() {
  if (loading.value) return // 防重复提交
  if (!form.username || !form.password) {
    errorMsg.value = '请输入账号和密码'
    return
  }
  loading.value = true
  errorMsg.value = ''
  try {
    // silent: 跳过全局错误弹窗，错误改为表单内内联提示
    const data = await request.post('/login', form, { silent: true })
    // 登录成功后再决定是否记住账号，避免记住错误账号
    if (remember.value) localStorage.setItem(REMEMBER_KEY, form.username)
    else localStorage.removeItem(REMEMBER_KEY)

    userStore.setLogin(data.token, data.userInfo)
    ElMessage.success(`欢迎，${data.userInfo.realName}`)
    // 客户账号登录进入独立客户门户，其余进入 OA 工作台
    router.push(data.userInfo.role === '客户' ? '/client' : '/')
  } catch (e) {
    // 后端已区分「还可尝试 N 次」「账号已锁定 X 分钟」等，直接内联展示
    errorMsg.value = e?.message || '账号或密码错误'
  } finally {
    loading.value = false
  }
}

function onRegister() {
  ElMessage.info('系统账号由管理员创建，请联系管理员')
}

function onForgot() {
  ElMessage.info('请联系管理员重置密码')
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 18px;
  padding: 24px;
  position: relative;
  background:
    radial-gradient(1100px 640px at 88% -6%, rgba(226, 35, 26, 0.20), transparent 58%),
    radial-gradient(1050px 640px at -8% 108%, rgba(255, 255, 255, 0.08), transparent 62%),
    linear-gradient(152deg, #0e0e0e 0%, #191919 55%, #262626 100%);
}

/* 呼吸红晕层：慢速明暗脉动，让背景有生命感 */
.login-page::after {
  content: '';
  position: fixed;
  inset: 0;
  pointer-events: none;
  background: radial-gradient(1200px 700px at 88% -6%, rgba(226, 35, 26, 0.07), transparent 58%);
  animation: bg-breathe 7s ease-in-out infinite;
}
@keyframes bg-breathe {
  0%, 100% { opacity: 0.4; }
  50% { opacity: 1; }
}

/* 极淡的噪点纹理：只增加质感，不喧宾夺主 */
.login-page::before {
  content: '';
  position: fixed;
  inset: 0;
  pointer-events: none;
  opacity: 0.05;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='180' height='180'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='3'/%3E%3C/filter%3E%3Crect width='180' height='180' filter='url(%23n)'/%3E%3C/svg%3E");
}

.login-shell {
  display: flex;
  width: min(920px, 96vw);
  min-height: 520px;
  border-radius: 20px;
  overflow: hidden;
  /* 阴影柔化：原 0 24px 80px / .45 偏闷 */
  box-shadow: 0 18px 50px rgba(0, 0, 0, 0.5);
  background: rgba(255, 255, 255, 0.06);
  backdrop-filter: blur(14px);
  border: 1px solid rgba(255, 255, 255, 0.12);
}

/* ---- 品牌区 ---- */
.brand-zone {
  flex: 1.1;
  padding: 56px 40px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  text-align: center;
  color: #fff;
}
.brand-badge {
  padding: 16px 22px;
  background: #ffffff;
  border-radius: 18px;
  box-shadow: 0 14px 36px rgba(0, 0, 0, 0.45);
  margin-bottom: 22px;
}
.brand-logo {
  width: 190px;
  height: auto;
  max-width: 100%;
  display: block;
}
/* 公司名比 LOGO 低一级，拉开层级 */
.brand-name {
  font-size: 28px;
  font-weight: 700;
  letter-spacing: 2px;
  margin: 0 0 10px;
  color: #ffffff;
  line-height: 1.4;
}
.brand-kicker {
  font-size: 12px;
  letter-spacing: 4px;
  margin: 0 0 8px;
  color: rgba(255, 255, 255, 0.5);
  text-transform: uppercase;
}
.brand-slogan {
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 1px;
  margin: 0;
  color: #ff5c52;
  line-height: 1.4;
}
.brand-divider {
  width: 64px;
  height: 3px;
  border-radius: 2px;
  background: linear-gradient(90deg, #e2231a, #ff6b61);
  margin: 20px 0 24px;
  transform-origin: center;
  animation: breathe 3.6s ease-in-out infinite;
}
@keyframes breathe {
  0%, 100% { transform: scaleX(0.7); opacity: 0.7; }
  50% { transform: scaleX(1.15); opacity: 1; }
}
.brand-points {
  display: flex;
  flex-direction: column;
  gap: 10px;
  align-items: flex-start;
  text-align: left;
}
.point {
  display: flex;
  align-items: center;
  gap: 9px;
  font-size: 14px;
  /* 不刺眼：深底上避免纯白 */
  color: rgba(255, 255, 255, 0.72);
  transition: color 0.2s ease, transform 0.2s ease;
}
.point:hover {
  color: rgba(255, 255, 255, 0.95);
  transform: translateX(3px);
}
.point .el-icon {
  font-size: 18px;
  color: #ff5c52;
  flex-shrink: 0;
  transition: color 0.2s ease;
}
.point:hover .el-icon { color: #ff7a70; }

/* ---- 登录卡片区 ---- */
.login-zone {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fff;
  padding: 40px 28px;
}
.login-card { width: min(320px, 100%); }
.login-title { font-size: 24px; color: #1f2937; margin: 0 0 6px; font-weight: 700; }
.login-sub { font-size: 13px; color: var(--lk-text-3, #6f737a); margin: 0 0 22px; }

/* 内联错误提示 */
.form-alert {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 9px 12px;
  margin-bottom: 16px;
  border-radius: 10px;
  background: #fef0f0;
  border: 1px solid #fde2e2;
  color: #f56c6c;
  font-size: 13px;
  line-height: 1.5;
}
.form-alert .el-icon { flex-shrink: 0; font-size: 15px; }

.field { margin-bottom: 18px; }

/* 输入框：圆角统一 10px，加大图标与文字间距，明确聚焦/错误反馈 */
.field :deep(.el-input__wrapper) {
  border-radius: 10px;
  padding-left: 12px;
  box-shadow: 0 0 0 1px #dcdfe6 inset;
  transition: box-shadow 0.18s ease;
}
.field :deep(.el-input__prefix) { margin-right: 10px; }
.field :deep(.el-input__prefix-inner) > .el-icon { color: #9aa2ad; }
.field :deep(.el-input__inner) { letter-spacing: 0.3px; }

.field :deep(.el-input__wrapper:hover) { box-shadow: 0 0 0 1px #c4ccd8 inset; }
.field :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px #161616 inset, 0 0 0 3px rgba(226, 35, 26, 0.12);
}
.field.is-invalid :deep(.el-input__wrapper) {
  box-shadow: 0 0 0 1px #f56c6c inset;
}
.field.is-invalid :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px #f56c6c inset, 0 0 0 3px rgba(245, 108, 108, 0.14);
}

/* 记住账号 / 忘记密码 */
.form-extra {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: -4px 0 18px;
  font-size: 13px;
}
.form-extra :deep(.el-checkbox__label) { font-size: 13px; color: var(--lk-text-2, #545862); }

.login-btn {
  width: 100%;
  height: 44px;
  font-size: 15px;
  letter-spacing: 2px;
  border-radius: 10px;
  background: #161616;
  border-color: #161616;
  box-shadow: 0 6px 18px rgba(22, 22, 22, 0.4);
  transition: background 0.18s ease, box-shadow 0.18s ease, transform 0.1s ease;
}
.login-btn:hover {
  background: #000000;
  border-color: #000000;
  box-shadow: 0 9px 24px rgba(226, 35, 26, 0.32);
}
.login-btn:active {
  transform: translateY(1px);
  box-shadow: 0 3px 10px rgba(22, 22, 22, 0.3);
}
.login-btn.is-loading { opacity: 0.85; }

.register {
  text-align: center;
  margin-top: 18px;
  font-size: 13px;
  color: var(--lk-text-3, #6f737a);
}

/* ---- 页面底部 ---- */
.page-footer {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-wrap: wrap;
  gap: 6px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.45);
  text-align: center;
}
.page-footer .dot { opacity: 0.5; }

/* ---- 响应式：平板/手机改为上下布局，品牌在上、表单在下 ---- */
@media (max-width: 720px) {
  .login-page { padding: 16px; gap: 14px; justify-content: flex-start; padding-top: 24px; }
  .login-shell {
    flex-direction: column;
    width: 100%;
    min-height: 0;
    border-radius: 16px;
  }
  .brand-zone {
    flex: none;
    padding: 26px 22px 22px;
  }
  .brand-badge { padding: 12px 16px; margin-bottom: 16px; }
  .brand-logo { width: 132px; }
  .brand-slogan { font-size: 13px; letter-spacing: 0.5px; }
  .brand-name { font-size: 22px; letter-spacing: 1.5px; }
  .brand-divider { margin: 14px 0 0; }
  /* 小屏隐藏三条卖点，避免登录表单被挤到首屏之外 */
  .brand-points { display: none; }
  .login-zone { padding: 26px 22px 28px; }
  .login-card { width: 100%; max-width: 340px; }
  .page-footer { font-size: 11px; }
}
</style>
