<template>
  <div>
    <!-- 筛选栏（PRD 9.8） -->
    <el-card class="filter-card">
      <el-form inline @submit.prevent>
        <el-form-item label="项目名称">
          <el-input v-model="query.projectName" placeholder="模糊搜索" clearable style="width: 180px" @keyup.enter="onSearch" />
        </el-form-item>
        <el-form-item label="客户单位">
          <el-select v-model="query.categoryId" placeholder="全部单位" clearable style="width: 180px" @change="onSearch">
            <el-option v-for="c in categoryOptions" :key="c.id" :label="c.categoryName" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="项目状态">
          <el-select v-model="query.projectStatus" placeholder="全部状态" clearable style="width: 140px" @change="onSearch">
            <el-option label="进行中" value="进行中" />
            <el-option label="已归档" value="已归档" />
          </el-select>
        </el-form-item>
        <el-form-item label="排序">
          <el-select v-model="query.sortField" style="width: 130px" @change="onSearch">
            <el-option label="创建时间" value="createTime" />
            <el-option label="名称" value="projectName" />
            <el-option label="截止时间" value="expectTime" />
            <el-option label="状态" value="projectStatus" />
          </el-select>
          <el-button class="sort-dir" :icon="query.sortOrder === 'asc' ? SortUp : SortDown" :title="query.sortOrder === 'asc' ? '升序' : '降序'" @click="toggleSortOrder" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="onSearch">搜索</el-button>
          <el-button :icon="Refresh" @click="onReset">重置</el-button>
          <el-button v-if="canWrite" type="primary" :icon="Plus" @click="openCreate">新建项目</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 项目卡片网格（一行约 3 个，间隔 16px） -->
    <el-card>
      <!-- 加载骨架 -->
      <div v-if="loading" class="card-grid">
        <div v-for="i in query.pageSize > 6 ? 6 : query.pageSize" :key="i" class="proj-card skeleton-card">
          <el-skeleton :rows="3" animated />
        </div>
      </div>

      <template v-else>
        <div v-if="tableData.length" class="card-grid">
          <div v-for="row in tableData" :key="row.id" class="proj-card">
            <!-- 醒目倒计时条 -->
            <div v-if="deadlineInfo(row.expectTime, row.projectStatus)" class="cd-strip" :class="`cd-${deadlineInfo(row.expectTime, row.projectStatus).type}`">
              <span class="cd-label">距截止</span>
              <span class="cd-value">{{ deadlineInfo(row.expectTime, row.projectStatus).label }}</span>
              <span class="cd-date">{{ formatTime(row.expectTime) }}</span>
            </div>

            <div class="proj-body">
              <div class="proj-info">
                <div class="proj-title-row">
                  <el-link type="primary" class="proj-name" @click="$router.push(`/projects/${row.id}`)">
                    {{ row.projectName }}
                  </el-link>
                  <el-tag :type="row.projectStatus === '进行中' ? 'success' : 'info'" size="small" effect="dark">
                    {{ row.projectStatus }}
                  </el-tag>
                </div>
                <div class="proj-meta">
                  <div class="meta-row"><span class="meta-label">客户单位</span><span class="meta-value">{{ row.companyName || '—' }}</span></div>
                  <div class="meta-row"><span class="meta-label">我方设计师</span><span class="meta-value">{{ row.designerNames || '—' }}</span></div>
                  <div class="meta-row"><span class="meta-label">客户对接人</span><span class="meta-value">{{ row.contactNames || '—' }}</span></div>
                  <div class="meta-row"><span class="meta-label">立项时间</span><span class="meta-value">{{ (row.createTime || '').slice(0, 10) }}</span></div>
                </div>
              </div>
              <!-- 右侧封面图：不打开项目就知道是什么项目，点击可全屏查看大图 -->
              <div
                class="proj-cover"
                :class="{ placeholder: !row.coverImage }"
                :title="row.coverImage ? '点击查看大图' : '暂无封面图，点编辑上传'"
                @click="onCoverClick(row)"
              >
                <el-image
                  v-if="row.coverImage"
                  :src="coverUrl(row.coverImage)"
                  :preview-src-list="[coverUrl(row.coverImage)]"
                  :preview-teleported="true"
                  fit="cover"
                  class="cover-img"
                  :alt="row.projectName"
                />
                <div v-else class="cover-ph">
                  <el-icon :size="30"><Picture /></el-icon>
                  <span>暂无封面</span>
                </div>
              </div>
            </div>

            <div class="proj-foot">
              <el-button size="small" type="primary" @click="$router.push(`/projects/${row.id}`)">查看</el-button>
              <el-button v-if="canWrite" size="small" :icon="Edit" :loading="editLoading" @click="openQuickEdit(row)">编辑</el-button>
              <template v-if="row.projectStatus === '已归档'">
                <el-button v-if="row.evaluation" size="small" type="warning" link @click="openViewEvaluation(row)">查看评价</el-button>
                <span v-else class="no-eval-tag">暂未评价</span>
              </template>
              <span class="foot-spacer" />
              <template v-if="canWrite">
                <el-button v-if="row.projectStatus === '进行中'" size="small" type="warning" link @click="onArchive(row)">归档</el-button>
                <el-button v-else size="small" type="success" link @click="onUnArchive(row)">取消归档</el-button>
                <el-button size="small" type="danger" link @click="onDelete(row)">删除</el-button>
              </template>
            </div>
          </div>
        </div>

        <!-- 空状态引导 -->
        <el-empty v-else description="暂无项目">
          <el-button v-if="canWrite" type="primary" :icon="Plus" @click="openCreate">新建项目</el-button>
          <p v-else class="empty-hint">暂无项目，请联系管理员创建</p>
        </el-empty>
      </template>

      <el-pagination
        v-model:current-page="query.pageNum"
        v-model:page-size="query.pageSize"
        :total="total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        class="pagination"
        @change="loadData"
      />
    </el-card>

    <!-- 新建项目弹窗 -->
    <el-dialog v-model="createVisible" title="新建项目" width="min(560px, 92vw)">
      <el-form :model="createForm" label-width="110px">
        <el-form-item label="项目名称" required>
          <el-input v-model="createForm.projectName" maxlength="256" />
        </el-form-item>
        <el-form-item label="客户单位" required>
          <el-select v-model="createForm.categoryId" placeholder="请选择客户单位" style="width: 100%" @change="onCreateCategoryChange">
            <el-option v-for="c in categoryOptions" :key="c.id" :label="c.categoryName" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="客户对接人" required>
          <el-select v-model="createForm.contactCustomerIds" multiple placeholder="选择该单位下的对接人（可多选）" style="width: 100%" :disabled="!createForm.categoryId">
            <el-option v-for="c in contactsOf(createForm.categoryId)" :key="c.id" :label="c.customerName" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="项目描述">
          <el-input v-model="createForm.projectDesc" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="预计截止时间">
          <el-date-picker v-model="createForm.expectTime" type="datetime" value-format="YYYY-MM-DD HH:mm:ss" style="width: 100%" placeholder="选择截止时间，项目卡片将显示倒计时" />
        </el-form-item>
        <el-form-item label="项目参与人">
          <el-select v-model="createForm.designerRelUserIdList" multiple style="width: 100%">
            <el-option v-for="u in designerOptions" :key="u.id" :label="u.realName" :value="u.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="流程模板">
          <el-select v-model="createForm.templateId" placeholder="不选择则创建空项目" clearable style="width: 100%">
            <el-option v-for="t in templateOptions" :key="t.id" :label="t.templateName" :value="t.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="submitCreate">创建</el-button>
      </template>
    </el-dialog>

    <!-- 卡片快捷编辑弹窗：不改代码不进详情页，直接改项目 -->
    <el-dialog v-model="editVisible" title="编辑项目" width="min(560px, 92vw)">
      <el-form :model="editForm" label-width="110px">
        <el-form-item label="封面图">
          <div class="cover-editor">
            <div class="cover-preview">
              <el-image
                v-if="editForm.coverImage"
                :src="coverUrl(editForm.coverImage)"
                :preview-src-list="[coverUrl(editForm.coverImage)]"
                :preview-teleported="true"
                fit="cover"
                class="cover-preview-img"
                alt="封面"
              />
              <el-icon v-else :size="22"><Picture /></el-icon>
            </div>
            <div class="cover-actions">
              <el-upload
                :show-file-list="false"
                accept=".jpg,.jpeg,.png,.webp"
                :before-upload="beforeCoverUpload"
                :http-request="(opt) => doCoverUpload(opt.file)"
              >
                <el-button size="small" :icon="Upload">{{ editForm.coverImage ? '更换封面' : '上传封面' }}</el-button>
              </el-upload>
              <el-button v-if="editForm.coverImage" size="small" type="danger" link :icon="Delete" @click="doCoverRemove">移除封面</el-button>
              <p class="cover-tip">jpg / png / webp，≤5MB；显示在卡片右侧，用于快速识别项目</p>
            </div>
          </div>
        </el-form-item>
        <el-form-item label="项目名称" required>
          <el-input v-model="editForm.projectName" maxlength="256" />
        </el-form-item>
        <el-form-item label="客户单位" required>
          <el-select v-model="editForm.categoryId" placeholder="请选择客户单位" style="width: 100%" @change="onEditCategoryChange">
            <el-option v-for="c in categoryOptions" :key="c.id" :label="c.categoryName" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="客户对接人" required>
          <el-select v-model="editForm.contactCustomerIds" multiple placeholder="选择该单位下的对接人（可多选）" style="width: 100%" :disabled="!editForm.categoryId">
            <el-option v-for="c in contactsOf(editForm.categoryId)" :key="c.id" :label="c.customerName" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="预计截止时间">
          <el-date-picker v-model="editForm.expectTime" type="datetime" value-format="YYYY-MM-DD HH:mm:ss" style="width: 100%" placeholder="设置后卡片显示倒计时" />
        </el-form-item>
        <el-form-item label="项目参与人">
          <template v-if="isAdmin">
            <el-select v-model="editForm.designerRelUserIdList" multiple style="width: 100%">
              <el-option v-for="u in designerOptions" :key="u.id" :label="u.realName" :value="u.id" />
            </el-select>
          </template>
          <template v-else>
            <el-tag v-for="d in editForm.designerList" :key="d.userId" class="designer-tag">{{ d.realName }}</el-tag>
            <span class="empty-text">（仅管理员可调整）</span>
          </template>
        </el-form-item>
        <el-form-item label="项目描述">
          <el-input v-model="editForm.projectDesc" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitEdit">保存</el-button>
      </template>
    </el-dialog>

    <!-- 查看客户评价弹窗 -->
    <el-dialog v-model="evalViewVisible" title="客户评价" width="min(520px, 92vw)">
      <EvaluationStars v-if="viewEvaluation" :evaluation="viewEvaluation" />
      <div v-else class="empty-text">暂无评价</div>
      <template #footer>
        <el-button @click="evalViewVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Edit, Picture, Plus, Refresh, Search, SortDown, SortUp, Upload } from '@element-plus/icons-vue'
import { listCategories, listCustomers } from '@/api/customer'
import EvaluationStars from '@/components/EvaluationStars.vue'
import {
  archiveProject, createProject, deleteProject, listProjects, projectDetail,
  removeProjectCover, unArchiveProject, updateProjectBase, uploadProjectCover
} from '@/api/project'
import { listTemplates } from '@/api/template'
import { listUsers } from '@/api/sysUser'
import { useUserStore } from '@/stores/user'
import { deadlineInfo } from '@/utils/deadline'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const canWrite = computed(() => ['管理员'].includes(userStore.role))
const isAdmin = computed(() => userStore.role === '管理员')

const loading = ref(false)
const tableData = ref([])
const total = ref(0)
const query = reactive({
  pageNum: 1, pageSize: 10, projectName: '', categoryId: null, projectStatus: null,
  sortField: 'createTime', sortOrder: 'desc'
})

const categoryOptions = ref([])
const customerOptions = ref([])
const templateOptions = ref([])
const designerOptions = ref([])

// 某客户单位下的对接人选项（V1.4.7）
function contactsOf(categoryId) {
  if (!categoryId) return []
  return customerOptions.value.filter((c) => c.categoryId === categoryId)
}

function formatTime(t) {
  return t ? t.slice(0, 16) : ''
}

function coverUrl(path) {
  return `/uploads/${path}`
}

// 卡片封面点击：有图则全屏预览大图（el-image 自带），无图且有权限则打开编辑弹窗上传
function onCoverClick(row) {
  if (!row.coverImage && canWrite.value) {
    openQuickEdit(row)
  }
}

// ---- 客户评价查看 ----
const evalViewVisible = ref(false)
const viewEvaluation = ref(null)

function openViewEvaluation(row) {
  viewEvaluation.value = row.evaluation
  evalViewVisible.value = true
}

async function loadData() {
  loading.value = true
  try {
    const data = await listProjects({ ...query })
    tableData.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function onSearch() {
  query.pageNum = 1
  loadData()
}

function toggleSortOrder() {
  query.sortOrder = query.sortOrder === 'asc' ? 'desc' : 'asc'
  loadData()
}

function onReset() {
  Object.assign(query, {
    pageNum: 1, pageSize: 10, projectName: '', categoryId: null, projectStatus: null,
    sortField: 'createTime', sortOrder: 'desc'
  })
  loadData()
}

// ---- 新建项目 ----
const createVisible = ref(false)
const creating = ref(false)
const createForm = reactive({
  projectName: '', categoryId: null, contactCustomerIds: [], projectDesc: '',
  expectTime: null, designerRelUserIdList: [], templateId: null
})

function openCreate() {
  Object.assign(createForm, {
    projectName: '', categoryId: null, contactCustomerIds: [], projectDesc: '',
    expectTime: null, designerRelUserIdList: [], templateId: null
  })
  createVisible.value = true
}

// 切换单位时清空已选对接人，避免残留其他单位的选项
function onCreateCategoryChange() {
  createForm.contactCustomerIds = []
}

async function submitCreate() {
  if (!createForm.projectName || !createForm.categoryId) {
    ElMessage.warning('请填写项目名称并选择客户单位')
    return
  }
  if (!createForm.contactCustomerIds.length) {
    ElMessage.warning('请至少选择一位客户对接人')
    return
  }
  creating.value = true
  try {
    const data = await createProject(createForm)
    ElMessage.success('项目创建成功')
    createVisible.value = false
    router.push(`/projects/${data.projectId}`)
  } finally {
    creating.value = false
  }
}

// ---- 卡片快捷编辑 ----
const editVisible = ref(false)
const editLoading = ref(false)
const saving = ref(false)
const editForm = reactive({
  id: null, projectName: '', categoryId: null, contactCustomerIds: [], projectDesc: '', expectTime: null,
  designerRelUserIdList: [], designerList: [], coverImage: null, projectStatus: ''
})

function onEditCategoryChange() {
  editForm.contactCustomerIds = []
}

async function openQuickEdit(row) {
  if (row.projectStatus === '已归档') {
    ElMessage.warning('已归档项目只读，请先取消归档')
    return
  }
  // 先取详情（含对接人/设计师ID列表）再开弹窗，避免用户快速点保存时数据未就绪（修复竞态）
  editLoading.value = true
  try {
    const detail = await projectDetail(row.id)
    Object.assign(editForm, {
      id: row.id,
      projectName: row.projectName || detail.projectName || '',
      categoryId: detail.categoryId ?? row.categoryId ?? null,
      contactCustomerIds: (detail.contactList || []).map((c) => c.customerId),
      projectDesc: row.projectDesc || detail.projectDesc || '',
      expectTime: row.expectTime || detail.expectTime || null,
      designerRelUserIdList: (detail.designerList || []).map((d) => d.userId),
      designerList: detail.designerList || [],
      coverImage: row.coverImage || detail.coverImage || null,
      projectStatus: row.projectStatus
    })
    editVisible.value = true
  } catch {
    /* 拦截器已弹错误提示 */
  } finally {
    editLoading.value = false
  }
}

function beforeCoverUpload(file) {
  const okTypes = ['image/jpeg', 'image/png', 'image/webp']
  if (!okTypes.includes(file.type)) {
    ElMessage.error('封面图仅支持 jpg / png / webp 格式')
    return false
  }
  if (file.size > 5 * 1024 * 1024) {
    ElMessage.error('封面图大小不能超过 5MB')
    return false
  }
  return true
}

async function doCoverUpload(file) {
  try {
    const data = await uploadProjectCover(editForm.id, file)
    editForm.coverImage = data.coverImage
    // 同步列表行数据，关弹窗后卡片立即显示
    const row = tableData.value.find((r) => r.id === editForm.id)
    if (row) row.coverImage = data.coverImage
    ElMessage.success('封面已更新')
  } catch {
    // 拦截器已弹错误提示
  }
}

async function doCoverRemove() {
  await ElMessageBox.confirm('确定移除该项目封面图吗？', '移除确认', { type: 'warning' })
  await removeProjectCover({ projectId: editForm.id })
  editForm.coverImage = null
  const row = tableData.value.find((r) => r.id === editForm.id)
  if (row) row.coverImage = null
  ElMessage.success('封面已移除')
}

async function submitEdit() {
  if (!editForm.projectName || !editForm.categoryId) {
    ElMessage.warning('请填写项目名称并选择客户单位')
    return
  }
  if (!editForm.contactCustomerIds.length) {
    ElMessage.warning('请至少选择一位客户对接人')
    return
  }
  saving.value = true
  try {
    await updateProjectBase({
      id: editForm.id,
      projectName: editForm.projectName,
      categoryId: editForm.categoryId,
      contactCustomerIds: editForm.contactCustomerIds,
      projectDesc: editForm.projectDesc,
      expectTime: editForm.expectTime,
      designerRelUserIdList: editForm.designerRelUserIdList
    })
    ElMessage.success('已保存')
    editVisible.value = false
    loadData()
  } finally {
    saving.value = false
  }
}

// ---- 归档 / 删除 ----
async function onArchive(row) {
  await ElMessageBox.confirm(`确定归档项目「${row.projectName}」吗？归档后内容只读。`, '归档确认', { type: 'warning' })
  await archiveProject({ projectId: row.id })
  ElMessage.success('已归档')
  loadData()
}

async function onUnArchive(row) {
  await unArchiveProject({ projectId: row.id })
  ElMessage.success('已取消归档')
  loadData()
}

async function onDelete(row) {
  await ElMessageBox.confirm(
    `确定删除项目「${row.projectName}」吗？全部业务数据与附件文件将物理销毁，不可恢复！`,
    '删除确认',
    { type: 'error', confirmButtonText: '确认删除' }
  )
  await deleteProject({ projectId: row.id })
  ElMessage.success('已删除')
  loadData()
}

onMounted(async () => {
  loadData()
  // 筛选项数据：客户单位、对接人（复用列表第一页大容量）、模板、设计师
  const [, cats, custs, tpls] = await Promise.all([
    Promise.resolve(),
    listCategories().catch(() => []),
    listCustomers({ pageNum: 1, pageSize: 200 }).catch(() => ({ items: [] })),
    listTemplates().catch(() => [])
  ])
  categoryOptions.value = cats || []
  customerOptions.value = custs.items || []
  templateOptions.value = tpls || []
  // 设计师选项：仅管理员能取用户列表，其他角色退化为空（编辑弹窗内只读展示）
  if (userStore.role === '管理员') {
    const users = await listUsers().catch(() => [])
    designerOptions.value = (users || []).filter((u) => u.isEnable === 1 && u.role !== '客户')
  }
  // 从首页「创建项目」卡片跳转：自动打开新建弹窗（create=blank 空白 / create=template 预选第一个模板）
  if (route.query.create) {
    openCreate()
    if (route.query.create === 'template' && tpls && tpls.length) {
      createForm.templateId = tpls[0].id
    }
  }
})
</script>

<style scoped>
.filter-card { margin-bottom: 12px; }
.pagination { margin-top: 12px; justify-content: flex-end; }
.empty-hint { color: var(--lk-text-3); font-size: 13px; }
.empty-text { color: var(--lk-text-3); font-size: 13px; }
.sort-dir { margin-left: 8px; }
.designer-tag { margin-right: 6px; }

/* ---- 卡片网格：一行约 3 个，间隔 16px ---- */
.card-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}
@media (max-width: 1200px) {
  .card-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 768px) {
  .card-grid { grid-template-columns: 1fr; gap: 12px; }
}

.proj-card {
  border: 1px solid var(--lk-border, #ebeef5);
  border-radius: 10px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  transition: box-shadow 0.2s, border-color 0.2s, transform 0.2s;
  background: var(--el-bg-color, #fff);
}
.proj-card:hover {
  border-color: var(--lk-primary, #409eff);
  box-shadow: var(--lk-shadow-md, 0 6px 18px rgba(64, 158, 255, 0.12));
  transform: translateY(-2px);
}
.skeleton-card { padding: 20px 16px; }

/* ---- 醒目倒计时条（卡片顶部色带） ---- */
.cd-strip {
  display: flex;
  align-items: baseline;
  gap: 8px;
  padding: 8px 14px;
  color: #fff;
  flex-wrap: wrap;
}
.cd-label { font-size: 12px; opacity: 0.9; }
.cd-value { font-size: 19px; font-weight: 700; letter-spacing: 0.5px; }
.cd-date { font-size: 12px; opacity: 0.85; margin-left: auto; }
/* 分档配色：>30天绿 / 16-30天蓝 / 6-15天橙 / <=5天红闪 / 逾期红闪 */
.cd-success { background: var(--lk-success, #67c23a); }
.cd-primary { background: var(--lk-primary, #409eff); }
.cd-warning { background: var(--lk-warning, #e6a23c); }
.cd-danger { background: var(--lk-danger, #f56c6c); animation: cd-pulse 1.6s ease-in-out infinite; }
@keyframes cd-pulse {
  0%, 100% { filter: brightness(1); }
  50% { filter: brightness(1.18); }
}
@media (prefers-reduced-motion: reduce) {
  .cd-danger { animation: none; }
}

.proj-body {
  display: flex;
  gap: 12px;
  padding: 14px 16px 8px;
  flex: 1;
  min-height: 0;
}
.proj-info { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 10px; }
.proj-title-row { display: flex; align-items: flex-start; justify-content: space-between; gap: 8px; }
.proj-name { font-size: 15px; font-weight: bold; line-height: 1.4; word-break: break-all; text-align: left; }

/* ---- 右侧封面图（加大到 140px，点击可全屏查看） ---- */
.proj-cover {
  width: 140px;
  min-height: 140px;
  align-self: stretch;
  border-radius: 10px;
  overflow: hidden;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: zoom-in;
  position: relative;
  border: 1px solid var(--lk-border, #ebeef5);
  background: var(--lk-fill-1, #f5f7fa);
  color: var(--lk-text-4, #a8abb2);
  transition: box-shadow 0.2s;
}
.proj-cover:hover { box-shadow: 0 4px 14px rgba(0, 0, 0, 0.14); }
.proj-cover.placeholder { cursor: pointer; border-style: dashed; }
.cover-img { width: 100%; height: 100%; display: block; }
.cover-ph {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  font-size: 12px;
}
@media (max-width: 768px) {
  .proj-cover { width: 108px; min-height: 108px; }
}

.proj-meta { display: flex; flex-direction: column; gap: 4px; flex: 1; }
.meta-row { display: flex; gap: 8px; font-size: 13px; line-height: 1.5; }
.meta-label { color: var(--lk-text-3); flex-shrink: 0; }
.meta-value { color: var(--lk-text-1, #303133); min-width: 0; word-break: break-all; }

.proj-foot {
  display: flex;
  align-items: center;
  gap: 8px;
  border-top: 1px solid var(--lk-border, #ebeef5);
  padding: 10px 16px;
}
.foot-spacer { flex: 1; }
.no-eval-tag { font-size: 12px; color: var(--lk-text-3); }

/* ---- 编辑弹窗封面 ---- */
.cover-editor { display: flex; gap: 14px; align-items: flex-start; }
.cover-preview {
  width: 140px;
  height: 140px;
  border-radius: 8px;
  border: 1px dashed var(--lk-border, #dcdfe6);
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--lk-fill-1, #f5f7fa);
  color: var(--lk-text-4, #a8abb2);
  flex-shrink: 0;
}
.cover-preview-img { width: 100%; height: 100%; display: block; }
.cover-actions { display: flex; flex-direction: column; gap: 8px; align-items: flex-start; }
.cover-tip { font-size: 12px; color: var(--lk-text-3); margin: 0; line-height: 1.5; }
</style>
