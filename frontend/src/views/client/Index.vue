<template>
  <div class="client-layout">
    <!-- 简化顶栏 -->
    <header class="client-header">
      <div class="brand">
        <img class="brand-logo" src="/link-icon.png" alt="青岛领客文化传播有限公司" />
        <span class="brand-name">领客文化 · 客户门户</span>
      </div>
      <div class="header-right">
        <el-tag type="primary" effect="plain" size="small">{{ userStore.userInfo?.companyName || userStore.userInfo?.customerName || '客户' }}</el-tag>
        <span class="user-name">{{ userStore.realName }}</span>
        <el-button size="small" text @click="onLogout">退出登录</el-button>
      </div>
    </header>

    <main class="client-main">
      <h2 class="page-title">我的项目</h2>
      <p class="page-sub">以下为您单位名下的全部项目，点击查看节点进度</p>

      <!-- 待我审核（V1.4.19） -->
      <div v-if="pendingReviewsGrouped.length" class="pending-box">
        <div class="pending-head">
          <span class="pending-title">待我审核</span>
          <span class="pending-count">{{ pendingReviewsGrouped.length }} 个项目待处理</span>
        </div>
        <div class="pending-list">
          <div v-for="g in pendingReviewsGrouped" :key="g.projectId" class="pending-item" @click="$router.push(`/client/projects/${g.projectId}?reviewNodeId=${g.nodes[0].nodeId}`)">
            <div class="pending-info">
              <div class="pending-proj">{{ g.projectName }}</div>
              <div class="pending-nodes">{{ g.nodes.map(n => n.nodeTitle).join('、') }}</div>
            </div>
            <el-tag type="danger" effect="dark" size="small">待审 {{ g.nodes.length }}</el-tag>
          </div>
        </div>
      </div>

      <!-- 筛选栏：搜索 + 状态 + 立项时间范围 -->
      <div class="filter-bar">
        <el-input
          v-model="query.projectName"
          placeholder="搜索项目名称"
          clearable
          class="filter-search"
          :prefix-icon="Search"
          @keyup.enter="onSearch"
          @clear="onSearch"
        />
        <el-select v-model="query.projectStatus" placeholder="项目状态" clearable class="filter-status" @change="onSearch">
          <el-option label="进行中" value="进行中" />
          <el-option label="已结项" value="已归档" />
        </el-select>
        <el-date-picker
          v-model="createTimeRange"
          type="daterange"
          range-separator="至"
          start-placeholder="立项开始日期"
          end-placeholder="立项结束日期"
          value-format="YYYY-MM-DD"
          class="filter-date"
          @change="onSearch"
        />
        <el-button type="primary" :icon="Search" @click="onSearch">查询</el-button>
        <el-button :icon="Refresh" @click="onReset">重置</el-button>
      </div>

      <div v-if="loading" class="card-grid">
        <div v-for="i in 3" :key="i" class="proj-card skeleton-card">
          <el-skeleton :rows="4" animated />
        </div>
      </div>

      <div v-else-if="projects.length" class="card-grid">
        <div v-for="row in projects" :key="row.id" class="proj-card" @click="$router.push(`/client/projects/${row.id}`)">
          <div v-if="row.stageCount > 0 && row.projectStatus !== '已归档' && row.activeStagePlanTime" class="cd-strip" :class="`cd-${deadlineInfo(row.activeStagePlanTime, row.projectStatus, row.activeStageName).type}`">
            <span class="cd-label">{{ row.activeStageName ? '当前环节' : '距截止' }}</span>
            <span class="cd-value">{{ deadlineInfo(row.activeStagePlanTime, row.projectStatus, row.activeStageName).label }}</span>
            <span class="cd-date">{{ (row.activeStagePlanTime || '').slice(0, 10) }}</span>
          </div>
          <div class="proj-body">
            <div class="proj-info">
              <div class="proj-title-row">
                <span class="proj-name">{{ row.projectName }}</span>
                <el-tag :type="row.projectStatus === '进行中' ? 'success' : 'info'" size="small" effect="dark">
                  {{ row.projectStatus === '已归档' ? '已结项' : row.projectStatus }}
                </el-tag>
              </div>
              <div class="meta-row"><span class="meta-label">项目参与者</span><span class="meta-value">{{ row.designerNames || '—' }}</span></div>
              <div class="meta-row"><span class="meta-label">项目对接人</span><span class="meta-value">{{ row.contactNames || '—' }}</span></div>
              <div class="meta-row"><span class="meta-label">立项时间</span><span class="meta-value">{{ (row.createTime || '').slice(0, 10) || '—' }}</span></div>
              <div class="meta-row"><span class="meta-label">开始时间</span><span class="meta-value">{{ (row.startTime || '').slice(0, 10) || '—' }}</span></div>
              <div class="meta-row"><span class="meta-label">预计结束</span><span class="meta-value">{{ (row.expectTime || '').slice(0, 10) || '—' }}</span></div>
            </div>
            <div v-if="row.coverImage" class="proj-cover">
              <el-image :src="coverUrl(row.coverImage)" :preview-src-list="[coverUrl(row.coverImage)]" :preview-teleported="true" fit="cover" class="cover-img" :alt="row.projectName" @click.stop />
            </div>
          </div>
          <div class="proj-foot">
            <span class="foot-hint">点击卡片查看节点进度 ›</span>
            <el-button v-if="row.projectStatus === '已归档' && !row.evaluation" size="small" type="primary" @click.stop="openEvaluate(row)">去评价</el-button>
            <el-button v-if="row.evaluation" size="small" type="primary" plain @click.stop="openViewEvaluation(row)">查看评论</el-button>
          </div>
        </div>
      </div>

      <el-empty v-else description="暂无符合条件的项目">
        <p class="empty-hint">如有项目需求，请联系您的对接顾问</p>
      </el-empty>

      <div v-if="total > query.pageSize" class="pager-row">
        <el-pagination
          layout="total, prev, pager, next"
          :total="total"
          :current-page="query.pageNum"
          :page-size="query.pageSize"
          background
          @current-change="onPageChange"
        />
      </div>
    </main>

    <!-- 客户满意度评价弹窗 -->
    <el-dialog v-model="evalVisible" title="客户满意度评价" width="min(520px, 92vw)">
      <div v-if="evalProject" class="eval-form">
        <p class="eval-project">项目：{{ evalProject.projectName }}</p>
        <div class="eval-item">
          <span class="eval-label">设计满意度</span>
          <el-rate v-model="evalForm.designScore" />
        </div>
        <div class="eval-item">
          <span class="eval-label">服务响应速度</span>
          <el-rate v-model="evalForm.serviceScore" />
        </div>
        <div class="eval-item">
          <span class="eval-label">最终产品</span>
          <el-rate v-model="evalForm.productScore" />
        </div>
        <div class="eval-item remark">
          <span class="eval-label">备注</span>
          <el-input
            v-model="evalForm.customerRemark"
            type="textarea"
            :rows="4"
            maxlength="2000"
            show-word-limit
            placeholder="选填，最多 2000 字"
          />
        </div>
        <el-alert title="提交后不可修改" type="warning" :closable="false" show-icon class="eval-alert" />
      </div>
      <template #footer>
        <el-button @click="evalVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="onSubmitEvaluation">提交评价</el-button>
      </template>
    </el-dialog>

    <!-- 查看评论弹窗 -->
    <el-dialog v-model="viewEvalVisible" title="我的评价" width="min(520px, 92vw)">
      <p v-if="viewEvalProject" class="eval-project">项目：{{ viewEvalProject.projectName }}</p>
      <EvaluationStars v-if="viewEvalProject?.evaluation" :evaluation="viewEvalProject.evaluation" />
      <template #footer>
        <el-button @click="viewEvalVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { Refresh, Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { submitEvaluation } from '@/api/evaluation'
import { listProjects } from '@/api/project'
import { listPendingReviews } from '@/api/review'
import EvaluationStars from '@/components/EvaluationStars.vue'
import { useUserStore } from '@/stores/user'
import { deadlineInfo } from '@/utils/deadline'

const router = useRouter()
const userStore = useUserStore()

const loading = ref(false)
const projects = ref([])
const total = ref(0)

const query = reactive({
  pageNum: 1,
  pageSize: 12,
  projectName: '',
  projectStatus: null,
  createTimeStart: null,
  createTimeEnd: null
})

// 立项时间范围（daterange，YYYY-MM-DD）
const createTimeRange = ref(null)

// 待我审核（V1.4.19）
const pendingReviews = ref([])
const pendingReviewsGrouped = computed(() => {
  const map = {}
  for (const r of pendingReviews.value) {
    if (!map[r.projectId]) map[r.projectId] = { projectId: r.projectId, projectName: r.projectName, nodes: [] }
    map[r.projectId].nodes.push(r)
  }
  return Object.values(map)
})

function buildParams() {
  const params = {
    pageNum: query.pageNum,
    pageSize: query.pageSize,
    projectName: query.projectName || null,
    projectStatus: query.projectStatus || null
  }
  if (createTimeRange.value && createTimeRange.value.length === 2) {
    params.createTimeStart = `${createTimeRange.value[0]} 00:00:00`
    params.createTimeEnd = `${createTimeRange.value[1]} 23:59:59`
  }
  return params
}

async function loadData() {
  loading.value = true
  try {
    const data = await listProjects(buildParams())
    projects.value = data.items || []
    total.value = data.total || 0
  } finally {
    loading.value = false
  }
}

async function loadPending() {
  try {
    pendingReviews.value = await listPendingReviews()
  } catch {
    pendingReviews.value = []
  }
}

function onSearch() {
  query.pageNum = 1
  loadData()
}

function onReset() {
  query.projectName = ''
  query.projectStatus = null
  createTimeRange.value = null
  onSearch()
}

function onPageChange(page) {
  query.pageNum = page
  loadData()
}

// ---- 客户满意度评价 ----
const evalVisible = ref(false)
const evalProject = ref(null)
const submitting = ref(false)
const evalForm = reactive({
  designScore: 0,
  serviceScore: 0,
  productScore: 0,
  customerRemark: ''
})

function openEvaluate(row) {
  evalProject.value = row
  Object.assign(evalForm, {
    designScore: 0,
    serviceScore: 0,
    productScore: 0,
    customerRemark: ''
  })
  evalVisible.value = true
}

async function onSubmitEvaluation() {
  if (evalForm.designScore <= 0 || evalForm.serviceScore <= 0 || evalForm.productScore <= 0) {
    ElMessage.warning('请完成三项评分')
    return
  }
  try {
    await ElMessageBox.confirm('提交后不可修改，确认提交？', '提交确认', {
      type: 'warning',
      confirmButtonText: '确认提交',
      cancelButtonText: '再想想'
    })
  } catch {
    return
  }
  submitting.value = true
  try {
    await submitEvaluation({
      projectId: evalProject.value.id,
      designScore: evalForm.designScore,
      serviceScore: evalForm.serviceScore,
      productScore: evalForm.productScore,
      customerRemark: evalForm.customerRemark || null
    })
    ElMessage.success('评价提交成功')
    evalVisible.value = false
    loadData()
  } finally {
    submitting.value = false
  }
}

// ---- 查看评论弹窗 ----
const viewEvalVisible = ref(false)
const viewEvalProject = ref(null)

function openViewEvaluation(row) {
  viewEvalProject.value = row
  viewEvalVisible.value = true
}

function coverUrl(path) { return `/uploads/${path}` }

function onLogout() {
  userStore.logout()
  router.push('/login')
}

onMounted(() => { loadData(); loadPending() })
</script>

<style scoped>
.client-layout { min-height: 100vh; background: var(--lk-bg, #f5f7fa); display: flex; flex-direction: column; }

.client-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 28px;
  height: 60px;
  background: #fff;
  border-bottom: 1px solid var(--lk-border, #ebeef5);
  position: sticky;
  top: 0;
  z-index: 10;
}
.brand { display: flex; align-items: center; gap: 10px; }
.brand-logo { height: 24px; width: auto; display: block; }
.brand-name { font-size: 16px; font-weight: 700; color: var(--lk-text-1, #303133); }
.header-right { display: flex; align-items: center; gap: 12px; }
.user-name { font-size: 13px; color: var(--lk-text-2, #606266); }

.client-main { flex: 1; padding: 24px 28px; max-width: 1280px; width: 100%; margin: 0 auto; box-sizing: border-box; }
.page-title { font-size: 22px; font-weight: 700; color: var(--lk-text-1, #303133); margin: 0 0 4px; }
.page-sub { font-size: 13px; color: var(--lk-text-3, #6f737a); margin: 0 0 16px; }
.empty-hint { color: var(--lk-text-3, #6f737a); font-size: 13px; }

/* 待我审核（V1.4.19） */
.pending-box {
  background: linear-gradient(135deg, #fff5f5 0%, #fff 100%);
  border: 1px solid #fbc4c4;
  border-radius: 12px;
  padding: 14px 16px;
  margin-bottom: 16px;
}
.pending-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.pending-title { font-size: 15px; font-weight: 700; color: var(--lk-danger, #f56c6c); }
.pending-count { font-size: 12px; color: var(--lk-text-3, #6f737a); }
.pending-list { display: flex; flex-direction: column; gap: 8px; }
.pending-item {
  display: flex; justify-content: space-between; align-items: center;
  padding: 10px 12px; background: #fff; border: 1px solid #fde2e2;
  border-radius: 8px; cursor: pointer; transition: all 0.15s;
}
.pending-item:hover { border-color: var(--lk-danger, #f56c6c); box-shadow: 0 2px 8px rgba(245, 108, 108, 0.15); }
.pending-info { min-width: 0; flex: 1; }
.pending-proj { font-size: 14px; font-weight: 600; color: var(--lk-text-1, #303133); }
.pending-nodes { font-size: 12px; color: var(--lk-text-3, #6f737a); margin-top: 2px; }

/* 筛选栏 */
.filter-bar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  padding: 14px 16px;
  margin-bottom: 18px;
  background: #fff;
  border: 1px solid var(--lk-border, #ebeef5);
  border-radius: 12px;
}
.filter-search { width: 220px; }
.filter-status { width: 130px; }
.filter-date { width: 280px; }

/* 项目卡片 */
.card-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; }
@media (max-width: 1200px) { .card-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 768px) { .card-grid { grid-template-columns: 1fr; gap: 12px; } }

.proj-card {
  border: 1px solid var(--lk-border, #ebeef5);
  border-radius: 12px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  background: #fff;
  cursor: pointer;
  transition: box-shadow 0.2s, border-color 0.2s, transform 0.2s;
}
.proj-card:hover { border-color: var(--lk-primary, #409eff); box-shadow: var(--lk-shadow-md, 0 6px 18px rgba(64, 158, 255, 0.14)); transform: translateY(-2px); }
.skeleton-card { padding: 20px 16px; cursor: default; }

.cd-strip { display: flex; align-items: baseline; gap: 8px; padding: 8px 14px; color: #fff; flex-wrap: wrap; }
.cd-label { font-size: 12px; opacity: 0.9; }
.cd-value { font-size: 19px; font-weight: 700; letter-spacing: 0.5px; }
.cd-date { font-size: 12px; opacity: 0.85; margin-left: auto; }
.cd-success { background: var(--lk-success, #67c23a); }
.cd-primary { background: var(--lk-primary, #409eff); }
.cd-warning { background: var(--lk-warning, #e6a23c); }
.cd-danger { background: var(--lk-danger, #f56c6c); animation: cd-pulse 1.6s ease-in-out infinite; }
.cd-done { background: #909399; justify-content: center; }
@keyframes cd-pulse { 0%, 100% { filter: brightness(1); } 50% { filter: brightness(1.18); } }

.proj-body { display: flex; gap: 12px; padding: 14px 16px 12px; flex: 1; min-height: 0; }
.proj-info { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 8px; }
.proj-title-row { display: flex; align-items: flex-start; justify-content: space-between; gap: 8px; }
.proj-name { font-size: 15px; font-weight: 700; line-height: 1.4; word-break: break-all; color: var(--lk-text-1, #303133); }
.meta-row { display: flex; gap: 8px; font-size: 13px; line-height: 1.5; }
.meta-label { color: var(--lk-text-3, #6f737a); flex-shrink: 0; }
.meta-value { color: var(--lk-text-1, #303133); min-width: 0; word-break: break-all; }

.proj-cover { width: 108px; min-height: 108px; border-radius: 10px; overflow: hidden; flex-shrink: 0; border: 1px solid var(--lk-border, #ebeef5); }
.cover-img { width: 100%; height: 100%; display: block; }

.proj-foot { border-top: 1px solid var(--lk-border, #ebeef5); padding: 10px 16px; display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.foot-hint { font-size: 12px; color: var(--lk-text-3, #6f737a); margin-right: auto; }

/* 评价弹窗 */
.eval-form .eval-project { font-weight: bold; margin: 0 0 14px; color: var(--lk-text-1, #303133); }
.eval-form .eval-item { display: flex; align-items: flex-start; gap: 12px; margin-bottom: 14px; }
.eval-form .eval-label { width: 96px; flex-shrink: 0; font-size: 13px; color: var(--lk-text-1, #303133); line-height: 32px; }
.eval-form .eval-item.remark .eval-label { line-height: 22px; padding-top: 6px; }
.eval-alert { margin-top: 4px; }

.pager-row { display: flex; justify-content: flex-end; margin-top: 18px; }

/* 移动端窄屏适配：防止品牌标题竖排换行 */
@media (max-width: 768px) {
  .client-header { padding: 0 12px; height: 52px; }
  .brand { gap: 6px; min-width: 0; }
  .brand-name { white-space: nowrap; font-size: 14px; }
  .header-right { gap: 6px; min-width: 0; }
  .header-right :deep(.el-tag) { max-width: 110px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .user-name { display: none; }
  .client-main { padding: 16px 12px; }
}

</style>
