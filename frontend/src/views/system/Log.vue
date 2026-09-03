<template>
  <div>
    <el-card class="filter-card">
      <el-form inline @submit.prevent>
        <el-form-item label="操作类型">
          <el-select v-model="query.operType" placeholder="全部类型" clearable filterable style="width: 200px">
            <el-option v-for="t in OPER_TYPES" :key="t.value" :label="t.label" :value="t.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="操作人ID">
          <el-input-number v-model="query.operUserId" :min="1" placeholder="可空" style="width: 130px" />
        </el-form-item>
        <el-form-item label="时间范围">
          <el-date-picker
            v-model="timeRange"
            type="datetimerange"
            value-format="YYYY-MM-DD HH:mm:ss"
            start-placeholder="开始时间"
            end-placeholder="结束时间"
            style="width: 340px"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="onSearch">搜索</el-button>
          <el-button :icon="Refresh" @click="onReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card>
      <ResponsiveTable
        :columns="columns"
        :data="tableData"
        :loading="loading"
        card-title-key="operDesc"
        row-key="logId"
      >
        <template #operTime="{ row }">{{ (row.operTime || '').slice(0, 19) }}</template>
        <template #operType="{ row }">
          <el-tag size="small" effect="plain">{{ typeLabel(row.operType) }}</el-tag>
        </template>
        <template #relatedProjectId="{ row }">
          <el-link v-if="row.relatedProjectId" type="primary" @click="$router.push(`/projects/${row.relatedProjectId}`)">
            #{{ row.relatedProjectId }}
          </el-link>
          <span v-else>—</span>
        </template>
      </ResponsiveTable>
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
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { Refresh, Search } from '@element-plus/icons-vue'
import { globalLogs } from '@/api/log'
import ResponsiveTable from '@/components/ResponsiveTable.vue'

// 表格列配置
const columns = [
  { prop: 'operUserName', label: '操作人', width: 110 },
  { prop: 'operTime', label: '操作时间', width: 160 },
  { prop: 'operType', label: '操作类型', width: 170 },
  { prop: 'operDesc', label: '变更描述', minWidth: 260, ellipsis: true },
  { prop: 'relatedProjectId', label: '关联项目', width: 100 }
]

// oper_type 枚举（Database.md 附录）
const OPER_TYPES = [
  { value: 'user_login', label: '用户登录' },
  { value: 'user_enable', label: '启用账号' },
  { value: 'user_disable', label: '停用账号' },
  { value: 'user_delete', label: '删除用户' },
  { value: 'project_create', label: '项目新建' },
  { value: 'project_delete', label: '项目删除' },
  { value: 'project_archive', label: '项目归档' },
  { value: 'project_unarchive', label: '取消归档' },
  { value: 'project_update', label: '项目修改' },
  { value: 'node_create', label: '节点新增' },
  { value: 'node_update', label: '节点修改' },
  { value: 'node_delete', label: '节点删除' },
  { value: 'template_form_create', label: '模板字段新增' },
  { value: 'template_form_update', label: '模板字段修改' },
  { value: 'template_form_delete', label: '模板字段删除' },
  { value: 'node_form_value_update', label: '表单填写修改' },
  { value: 'comment_create', label: '评论新增' },
  { value: 'comment_delete', label: '评论删除' },
  { value: 'attachment_upload', label: '附件上传' },
  { value: 'attachment_delete', label: '附件删除' },
  { value: 'customer_create', label: '客户新增' },
  { value: 'customer_update', label: '客户修改' },
  { value: 'customer_delete', label: '客户删除' },
  { value: 'category_create', label: '分类新增' },
  { value: 'category_update', label: '分类修改' },
  { value: 'category_delete', label: '分类删除' },
  { value: 'template_create', label: '模板新增' },
  { value: 'template_update', label: '模板修改' },
  { value: 'template_delete', label: '模板删除' },
  { value: 'node_template_create', label: '节点模板新增' },
  { value: 'node_template_update', label: '节点模板修改' },
  { value: 'node_template_delete', label: '节点模板删除' }
]

function typeLabel(v) {
  return OPER_TYPES.find((t) => t.value === v)?.label || v
}

const loading = ref(false)
const tableData = ref([])
const total = ref(0)
const timeRange = ref(null)
const query = reactive({ pageNum: 1, pageSize: 10, operType: null, operUserId: null })

async function loadData() {
  loading.value = true
  try {
    const params = { ...query }
    if (timeRange.value?.[0]) params.startTime = timeRange.value[0]
    if (timeRange.value?.[1]) params.endTime = timeRange.value[1]
    const data = await globalLogs(params)
    tableData.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function onSearch() { query.pageNum = 1; loadData() }
function onReset() {
  Object.assign(query, { pageNum: 1, pageSize: 10, operType: null, operUserId: null })
  timeRange.value = null
  loadData()
}

onMounted(loadData)
</script>

<style scoped>
.filter-card { margin-bottom: 12px; }
.pagination { margin-top: 12px; justify-content: flex-end; }
</style>
