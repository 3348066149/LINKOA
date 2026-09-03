<template>
  <el-card>
    <div class="header">
      <span class="title">流程模板</span>
      <el-button v-if="canWrite" type="primary" :icon="Plus" @click="openCreate">新建模板</el-button>
    </div>

    <!-- 卡片网格（一行 3 个，间隔 16px） -->
    <div v-if="loading" class="card-grid">
      <div v-for="i in 6" :key="i" class="tpl-card skeleton-card">
        <el-skeleton :rows="3" animated />
      </div>
    </div>

    <div v-else-if="tableData.length" class="card-grid">
      <div v-for="row in tableData" :key="row.id" class="tpl-card">
        <div class="tpl-head">
          <div class="tpl-avatar"><el-icon><Connection /></el-icon></div>
          <div class="tpl-title">
            <span class="tpl-name" :title="row.templateName">{{ row.templateName }}</span>
            <span class="tpl-id">#{{ row.id }}</span>
          </div>
        </div>

        <div class="tpl-meta">
          <div class="meta-row">
            <el-icon class="meta-icon"><User /></el-icon>
            <span class="meta-label">创建人</span>
            <span class="meta-value">{{ row.createUserName || '—' }}</span>
          </div>
          <div class="meta-row">
            <el-icon class="meta-icon"><Clock /></el-icon>
            <span class="meta-label">创建时间</span>
            <span class="meta-value">{{ (row.createTime || '').slice(0, 16) }}</span>
          </div>
        </div>

        <div class="tpl-foot">
          <el-button size="small" type="primary" :icon="Edit" @click="$router.push(`/templates/${row.id}/edit`)">编辑流程</el-button>
          <span class="foot-spacer" />
          <el-button v-if="canWrite" size="small" type="danger" :icon="Delete" @click="onDelete(row)">删除</el-button>
        </div>
      </div>
    </div>

    <el-empty v-else description="暂无流程模板">
      <el-button v-if="canWrite" type="primary" :icon="Plus" @click="openCreate">新建模板</el-button>
      <p v-else class="empty-hint">暂无流程模板，请联系管理员创建</p>
    </el-empty>

    <!-- 新建模板弹窗：先建空模板，再进入画布编辑 -->
    <el-dialog v-model="createVisible" title="新建流程模板" width="min(420px, 92vw)">
      <el-input v-model="newName" placeholder="模板名称" maxlength="128" />
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="submitCreate">创建并编辑</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Clock, Connection, Delete, Edit, Plus, User } from '@element-plus/icons-vue'
import { addTemplate, deleteTemplate, listTemplates } from '@/api/template'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()
const canWrite = computed(() => ['管理员'].includes(userStore.role))

const loading = ref(false)
const tableData = ref([])
const createVisible = ref(false)
const creating = ref(false)
const newName = ref('')

async function loadData() {
  loading.value = true
  try {
    tableData.value = await listTemplates()
  } finally {
    loading.value = false
  }
}

function openCreate() {
  newName.value = ''
  createVisible.value = true
}

async function submitCreate() {
  if (!newName.value.trim()) {
    ElMessage.warning('请输入模板名称')
    return
  }
  creating.value = true
  try {
    const data = await addTemplate({ templateName: newName.value.trim(), nodes: [], edges: [] })
    createVisible.value = false
    router.push(`/templates/${data.id}/edit`)
  } finally {
    creating.value = false
  }
}

async function onDelete(row) {
  await ElMessageBox.confirm(
    `确定删除模板「${row.templateName}」吗？已创建的历史项目不受影响。`,
    '删除确认',
    { type: 'error', confirmButtonText: '确认删除' }
  )
  await deleteTemplate({ id: row.id })
  ElMessage.success('已删除')
  loadData()
}

onMounted(loadData)
</script>

<style scoped>
.header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.title { font-size: 16px; font-weight: bold; }
.empty-hint { color: var(--lk-text-3, #6f737a); font-size: 13px; }

/* ---- 卡片网格：一行 3 个，间隔 16px ---- */
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

.tpl-card {
  border: 1px solid var(--lk-border, #ebeef5);
  border-radius: 12px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 186px;
  transition: box-shadow 0.2s, border-color 0.2s, transform 0.2s;
}
.tpl-card:hover {
  border-color: var(--lk-primary, #409eff);
  box-shadow: var(--lk-shadow-md, 0 6px 18px rgba(64, 158, 255, 0.14));
  transform: translateY(-2px);
}
.skeleton-card { padding: 20px 16px; min-height: 0; }

.tpl-head { display: flex; align-items: center; gap: 12px; }
.tpl-avatar {
  width: 44px;
  height: 44px;
  flex: none;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  color: #fff;
  background: linear-gradient(135deg, var(--lk-primary, #409eff), #66b1ff);
}
.tpl-title { display: flex; flex-direction: column; gap: 2px; min-width: 0; flex: 1; }
.tpl-name {
  font-size: 16px;
  font-weight: 700;
  color: var(--lk-text-1, #303133);
  line-height: 1.35;
  word-break: break-all;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.tpl-id { font-size: 12px; color: var(--lk-text-3, #6f737a); }

.tpl-meta { display: flex; flex-direction: column; gap: 6px; flex: 1; }
.meta-row { display: flex; align-items: center; gap: 6px; font-size: 13px; }
.meta-icon { font-size: 14px; color: var(--lk-text-3, #6f737a); flex: none; }
.meta-label { color: var(--lk-text-3, #6f737a); flex: none; }
.meta-value {
  color: var(--lk-text-1, #303133);
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tpl-foot {
  display: flex;
  align-items: center;
  gap: 8px;
  border-top: 1px solid var(--lk-border, #ebeef5);
  padding-top: 10px;
  margin-top: auto;
}
.foot-spacer { flex: 1; }
</style>
