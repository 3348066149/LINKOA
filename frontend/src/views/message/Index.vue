<template>
  <el-card>
    <div class="header">
      <span class="title">消息中心</span>
      <div class="header-right">
        <el-radio-group v-model="isRead" @change="onSearch">
          <el-radio-button :value="null">全部</el-radio-button>
          <el-radio-button :value="0">未读</el-radio-button>
          <el-radio-button :value="1">已读</el-radio-button>
        </el-radio-group>
        <el-button type="primary" size="small" :icon="Check" :loading="markingAll" @click="onMarkAllRead">全部已读</el-button>
      </div>
    </div>

    <div v-loading="loading">
      <div v-if="tableData.length === 0" class="empty-text">暂无消息</div>
      <!-- 点击整行：标记已读 + 跳转项目详情 -->
      <div
        v-for="m in tableData"
        :key="m.id"
        class="msg-item"
        :class="{ unread: m.isRead === 0 }"
        @click="onClickMessage(m)"
      >
        <el-badge is-dot :hidden="m.isRead === 1" class="msg-dot" />
        <div class="msg-body">
          <div class="msg-content">{{ m.msgContent }}</div>
          <div class="msg-time">{{ (m.createTime || '').slice(0, 16) }}</div>
        </div>
        <el-tag size="small" effect="plain">{{ typeLabel(m.msgType) }}</el-tag>
      </div>
    </div>

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
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Check } from '@element-plus/icons-vue'
import { markRead, markReadAll, myMessages } from '@/api/message'
import { useMessageStore } from '@/stores/message'

const router = useRouter()
const messageStore = useMessageStore()

const TYPE_LABELS = {
  node_create: '节点新增',
  node_update: '节点修改',
  node_delete: '节点删除',
  form_update: '表单填写',
  comment_create: '新评论',
  evaluation_create: '客户评价'
}
function typeLabel(t) { return TYPE_LABELS[t] || t }

const loading = ref(false)
const tableData = ref([])
const total = ref(0)
const isRead = ref(null)
const query = reactive({ pageNum: 1, pageSize: 10 })

async function loadData() {
  loading.value = true
  try {
    const params = { ...query }
    if (isRead.value !== null) params.isRead = isRead.value
    const data = await myMessages(params)
    tableData.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function onSearch() { query.pageNum = 1; loadData() }

async function onClickMessage(m) {
  if (m.isRead === 0) {
    await markRead({ messageId: m.id })
    m.isRead = 1
    messageStore.fetchUnread()
  }
  if (m.projectId) {
    router.push(`/projects/${m.projectId}`)
  }
}

const markingAll = ref(false)
async function onMarkAllRead() {
  markingAll.value = true
  try {
    const data = await markReadAll()
    ElMessage.success(`已标记 ${data.count} 条为已读`)
    messageStore.fetchUnread()
    loadData()
  } finally {
    markingAll.value = false
  }
}

onMounted(loadData)
</script>

<style scoped>
.header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.header-right { display: flex; align-items: center; gap: 12px; }
.title { font-size: 16px; font-weight: bold; }
.empty-text { color: var(--lk-text-3); text-align: center; padding: 40px 0; }
.msg-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 8px;
  border-bottom: 1px solid #ebeef5;
  cursor: pointer;
  border-radius: 4px;
}
.msg-item:hover { background: #f5f7fa; }
.msg-item.unread .msg-content { font-weight: bold; color: #303133; }
.msg-body { flex: 1; min-width: 0; }
.msg-content { font-size: 14px; color: #606266; }
.msg-time { font-size: 12px; color: var(--lk-text-3); margin-top: 4px; }
.pagination { margin-top: 12px; justify-content: flex-end; }
</style>
