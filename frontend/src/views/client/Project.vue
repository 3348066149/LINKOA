<template>
  <div class="client-layout">
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

    <main v-if="detail" class="client-main">
      <el-button link :icon="Back" class="back-btn" @click="$router.push('/client')">返回我的项目</el-button>

      <!-- 项目概览卡 -->
      <div class="overview-card">
        <div class="ov-head">
          <h2 class="ov-title">{{ detail.projectName }}</h2>
          <el-tag :type="detail.projectStatus === '进行中' ? 'success' : 'info'" effect="dark">{{ detail.projectStatus === '已归档' ? '已结项' : detail.projectStatus }}</el-tag>
        </div>
        <div class="ov-meta">
          <div class="meta-row"><span class="meta-label">项目参与者</span><span class="meta-value">{{ designerNames || '—' }}</span></div>
          <div class="meta-row"><span class="meta-label">项目对接人</span><span class="meta-value">{{ contactNames || '—' }}</span></div>
          <div class="meta-row"><span class="meta-label">项目描述</span><span class="meta-value">{{ detail.projectDesc || '—' }}</span></div>
          <div class="meta-row"><span class="meta-label">立项时间</span><span class="meta-value">{{ formatTime(detail.createTime) }}</span></div>
          <div class="meta-row"><span class="meta-label">预计结束时间</span><span class="meta-value">{{ formatTime(detail.expectTime) }}</span></div>
          <div v-if="deadlineInfo(detail.expectTime, detail.projectStatus)" class="deadline-badge" :class="`dl-${deadlineInfo(detail.expectTime, detail.projectStatus).type}`">
            {{ deadlineInfo(detail.expectTime, detail.projectStatus).label }}
          </div>
        </div>
      </div>

      <!-- 节点进度时间线 -->
      <h3 class="section-title">节点进度</h3>
      <div v-if="detail.nodes.length" class="node-list">
        <div v-for="(n, idx) in sortedNodes" :key="n.id" class="node-item" :class="{ done: n.formFilled }">
          <div class="node-rail">
            <div class="node-dot" :class="{ done: n.formFilled }">
              <el-icon v-if="n.formFilled"><Check /></el-icon>
              <span v-else>{{ idx + 1 }}</span>
            </div>
            <div v-if="idx < sortedNodes.length - 1" class="node-line" :class="{ done: n.formFilled }" />
          </div>
          <div class="node-card" @click="openForm(n)">
            <div class="node-head">
              <span class="node-title">{{ n.nodeTitle }}</span>
              <el-tag :type="n.formFilled ? 'success' : 'info'" size="small" effect="light">
                {{ n.formFilled ? '已完成' : '未开始' }}
              </el-tag>
            </div>
            <div v-if="n.nodeRemark" class="node-remark">{{ n.nodeRemark }}</div>
            <div v-if="n.formFilled" class="node-hint"><el-icon><Document /></el-icon> 点击查看已填内容</div>
            <div v-else class="node-hint pending"><el-icon><Clock /></el-icon> 该节点暂未更新</div>
          </div>
        </div>
      </div>
      <el-empty v-else description="该项目暂无节点" />

      <!-- 节点表单只读弹窗 -->
      <el-dialog v-model="formVisible" :title="`${currentNode?.nodeTitle || ''} - 已填内容`" width="min(560px, 92vw)">
        <el-descriptions v-if="currentFormFields.length" :column="1" border>
          <el-descriptions-item v-for="f in currentFormFields" :key="f.id || f.fieldLabel" :label="f.fieldLabel">
            <template v-if="f.fieldType === 'image' && f.fieldValue">
              <el-image
                :src="f.fieldValue.startsWith('http') ? f.fieldValue : `/uploads/${f.fieldValue}`"
                :preview-src-list="[f.fieldValue.startsWith('http') ? f.fieldValue : `/uploads/${f.fieldValue}`]"
                :preview-teleported="true"
                fit="cover"
                style="width: 120px; height: 120px; border-radius: 8px"
              />
            </template>
            <template v-else-if="f.fieldType === 'select' && Array.isArray(f.fieldValueParsed)">
              <el-tag v-for="(opt, i) in f.fieldValueParsed" :key="i" size="small" style="margin-right: 6px">{{ opt }}</el-tag>
            </template>
            <template v-else-if="f.fieldType === 'link' && f.fieldValue">
              <a
                :href="/^https?:\/\//i.test(f.fieldValue) ? f.fieldValue : `https://${f.fieldValue}`"
                target="_blank"
                rel="noopener"
                class="link-value"
              >{{ f.fieldValue }}</a>
            </template>
            <template v-else>
              <span :class="{ 'empty-value': !f.fieldValue }">{{ f.fieldValue || '未填写' }}</span>
            </template>
          </el-descriptions-item>
        </el-descriptions>
        <el-empty v-else description="该节点暂无表单内容" :image-size="60" />
        <div class="readonly-tip"><el-icon><Lock /></el-icon> 当前为只读视图，如需修改请联系我方负责人</div>
      </el-dialog>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Back, Check, Clock, Document, Lock } from '@element-plus/icons-vue'
import { projectDetail } from '@/api/project'
import { getNodeForm } from '@/api/projectNode'
import { useUserStore } from '@/stores/user'
import { deadlineInfo } from '@/utils/deadline'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const detail = ref(null)
const loading = ref(false)

// 表单只读
const formVisible = ref(false)
const currentNode = ref(null)
const currentFormFields = ref([])

const sortedNodes = computed(() => {
  if (!detail.value) return []
  // 按画布位置排序（左→右，再上→下），与删除重加节点后的实际流程顺序一致
  return [...detail.value.nodes].sort(
    (a, b) => Number(a.posX) - Number(b.posX) || Number(a.posY) - Number(b.posY) || a.sort - b.sort || a.id - b.id
  )
})

// 项目参与者 / 我方负责人（顿号分隔）
const designerNames = computed(() => (detail.value?.designerList || []).map((d) => d.realName).join('、'))
const contactNames = computed(() => (detail.value?.contactList || []).map((c) => c.customerName).join('、'))

function formatTime(t) { return t ? t.slice(0, 16) : '—' }

async function loadData() {
  loading.value = true
  try {
    detail.value = await projectDetail(route.params.id)
  } finally {
    loading.value = false
  }
}

async function openForm(node) {
  if (!node.formFilled) return
  currentNode.value = node
  currentFormFields.value = []
  formVisible.value = true
  try {
    const data = await getNodeForm(node.id)
    currentFormFields.value = (data.fields || []).map((f) => ({
      ...f,
      fieldValueParsed: f.fieldType === 'select' && f.fieldValue ? safeParse(f.fieldValue) : null
    }))
  } catch {
    currentFormFields.value = []
  }
}

function safeParse(v) {
  try { return JSON.parse(v) } catch { return null }
}

function onLogout() {
  userStore.logout()
  router.push('/login')
}

onMounted(loadData)
</script>

<style scoped>
.client-layout { min-height: 100vh; background: var(--lk-bg, #f5f7fa); display: flex; flex-direction: column; }
.client-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 28px; height: 60px; background: #fff;
  border-bottom: 1px solid var(--lk-border, #ebeef5);
  position: sticky; top: 0; z-index: 10;
}
.brand { display: flex; align-items: center; gap: 10px; }
.brand-logo { height: 24px; width: auto; display: block; }
.brand-name { font-size: 16px; font-weight: 700; color: var(--lk-text-1, #303133); }
.header-right { display: flex; align-items: center; gap: 12px; }
.user-name { font-size: 13px; color: var(--lk-text-2, #606266); }

.client-main { flex: 1; padding: 20px 28px 40px; max-width: 960px; width: 100%; margin: 0 auto; box-sizing: border-box; }
.back-btn { margin-bottom: 12px; }

.overview-card { background: #fff; border: 1px solid var(--lk-border, #ebeef5); border-radius: 12px; padding: 20px; }
.ov-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 14px; }
.ov-title { font-size: 20px; font-weight: 700; color: var(--lk-text-1, #303133); margin: 0; word-break: break-all; }
.ov-meta { display: flex; flex-direction: column; gap: 8px; }
.meta-row { display: flex; gap: 8px; font-size: 13px; line-height: 1.5; }
.meta-label { color: var(--lk-text-3, #6f737a); flex-shrink: 0; min-width: 64px; }
.meta-value { color: var(--lk-text-1, #303133); word-break: break-all; }
.deadline-badge {
  display: inline-flex; align-items: center; margin-top: 6px;
  padding: 4px 14px; border-radius: 999px; color: #fff;
  font-size: 14px; font-weight: 700;
}
.dl-success { background: var(--lk-success, #67c23a); }
.dl-primary { background: var(--lk-primary, #409eff); }
.dl-warning { background: var(--lk-warning, #e6a23c); }
.dl-danger { background: var(--lk-danger, #f56c6c); animation: pulse 1.6s ease-in-out infinite; }
@keyframes pulse { 0%, 100% { filter: brightness(1); } 50% { filter: brightness(1.18); } }

.section-title { font-size: 17px; font-weight: 700; color: var(--lk-text-1, #303133); margin: 24px 0 14px; }

.node-list { display: flex; flex-direction: column; }
.node-item { display: flex; gap: 14px; }
.node-rail { display: flex; flex-direction: column; align-items: center; width: 28px; flex-shrink: 0; }
.node-dot {
  width: 28px; height: 28px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  background: var(--lk-fill, #f5f7fa);
  border: 2px solid var(--lk-border, #dcdfe6);
  color: var(--lk-text-3, #6f737a); font-size: 13px; font-weight: 700;
  flex-shrink: 0; z-index: 1;
}
.node-dot.done { background: var(--lk-success, #67c23a); border-color: var(--lk-success, #67c23a); color: #fff; }
.node-line { width: 2px; flex: 1; min-height: 24px; background: var(--lk-border, #dcdfe6); margin: 4px 0; }
.node-line.done { background: var(--lk-success, #67c23a); }

.node-card {
  flex: 1; margin-bottom: 14px;
  background: #fff; border: 1px solid var(--lk-border, #ebeef5); border-radius: 10px;
  padding: 14px 16px; cursor: pointer;
  transition: box-shadow 0.2s, border-color 0.2s;
}
.node-card:hover { border-color: var(--lk-primary, #409eff); box-shadow: var(--lk-shadow-md, 0 4px 14px rgba(64, 158, 255, 0.12)); }
.node-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.node-title { font-size: 15px; font-weight: 700; color: var(--lk-text-1, #303133); }
.node-remark { margin-top: 6px; font-size: 13px; color: var(--lk-text-2, #606266); line-height: 1.5; }
.node-hint { margin-top: 8px; font-size: 12px; color: var(--lk-primary, #409eff); display: flex; align-items: center; gap: 4px; }
.node-hint.pending { color: var(--lk-text-3, #6f737a); }
.empty-value { color: var(--lk-text-3, #6f737a); }
.link-value { color: var(--lk-primary, #409eff); word-break: break-all; }
.readonly-tip {
  margin-top: 12px; font-size: 12px; color: var(--lk-text-3, #6f737a);
  display: flex; align-items: center; gap: 4px;
}

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
