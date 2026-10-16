<template>
  <div class="dashboard">
    <!-- 欢迎区 -->
    <div class="welcome">
      <h1>你好，{{ userStore.realName }}</h1>
      <p>开始管理你的项目</p>
    </div>

    <!-- 创建项目卡片（仅管理员；流程模板功能已下线，直接打开新建弹窗） -->
    <el-card v-if="canWrite" class="create-card" shadow="never">
      <h2 class="create-title">创建项目</h2>
      <div class="create-options">
        <div class="option" @click="onCreate('blank')">
          <div class="option-icon">📄</div>
          <div class="option-title">创建项目</div>
          <div class="option-desc">填写封面、名称、对接人、环节等信息</div>
        </div>
      </div>
    </el-card>

    <!-- 最近项目 -->
    <el-card class="recent-card" shadow="never">
      <div class="recent-head">
        <h2>最近项目</h2>
        <el-button link type="primary" @click="$router.push('/projects')">查看全部 →</el-button>
      </div>
      <ResponsiveTable
        :columns="columns"
        :data="recentProjects"
        :loading="loading"
        card-title-key="projectName"
      >
        <template #projectName="{ row }">
          <el-link type="primary" @click="$router.push(`/projects/${row.id}`)">{{ row.projectName }}</el-link>
        </template>
        <template #designerNames="{ row }">{{ row.designerNames || '—' }}</template>
        <template #createTime="{ row }">{{ formatTime(row.createTime) }}</template>
        <template #projectStatus="{ row }">
          <el-tag :type="row.projectStatus === '进行中' ? 'success' : 'info'">{{ row.projectStatus }}</el-tag>
        </template>
      </ResponsiveTable>
      <el-empty v-if="!loading && recentProjects.length === 0" description="暂无项目" />
    </el-card>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { listProjects } from '@/api/project'
import { useUserStore } from '@/stores/user'
import ResponsiveTable from '@/components/ResponsiveTable.vue'

const router = useRouter()
const userStore = useUserStore()
const canWrite = computed(() => ['管理员'].includes(userStore.role))

// 最近项目表格列配置
const columns = [
  { prop: 'projectName', label: '项目名称', minWidth: 220 },
  { prop: 'customerName', label: '关联客户', minWidth: 140 },
  { prop: 'designerNames', label: '项目参与人', minWidth: 160 },
  { prop: 'createTime', label: '创建时间', width: 160 },
  { prop: 'projectStatus', label: '状态', width: 100 }
]

const loading = ref(false)
const recentProjects = ref([])

function formatTime(t) {
  return t ? t.slice(0, 16) : ''
}

async function loadRecent() {
  loading.value = true
  try {
    const data = await listProjects({ pageNum: 1, pageSize: 5 })
    recentProjects.value = data.items || []
  } finally {
    loading.value = false
  }
}

function onCreate(mode) {
  if (mode === 'json') {
    ElMessage.info('JSON 导入功能即将上线')
    return
  }
  router.push({ path: '/projects', query: { create: mode } })
}

onMounted(loadRecent)
</script>

<style scoped>
.dashboard { max-width: 960px; margin: 0 auto; }
.welcome { margin-bottom: 20px; }
.welcome h1 { font-size: 24px; color: #1f2937; margin-bottom: 4px; }
.welcome p { color: var(--lk-text-3); font-size: 14px; }

.create-card { margin-bottom: 20px; }
.create-title { font-size: 16px; color: #303133; margin-bottom: 16px; }
.create-options { display: flex; gap: 16px; }
.option {
  flex: 1;
  padding: 24px 16px;
  border: 1px solid #ebeef5;
  border-radius: 10px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
}
.option:hover {
  border-color: #409eff;
  box-shadow: 0 6px 18px rgba(64, 158, 255, 0.12);
  transform: translateY(-2px);
}
.option-icon { font-size: 32px; margin-bottom: 10px; }
.option-title { font-size: 15px; font-weight: bold; color: #303133; margin-bottom: 4px; }
.option-desc { font-size: 12px; color: var(--lk-text-3); }

.recent-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.recent-head h2 { font-size: 16px; color: #303133; }
</style>
