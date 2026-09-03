<template>
  <el-card>
    <div class="header">
      <span class="title">报表导出</span>
    </div>
    <el-form label-width="90px" class="filter-form">
      <el-form-item label="项目状态">
        <el-select v-model="query.projectStatus" placeholder="全部状态" clearable style="width: 200px">
          <el-option label="进行中" value="进行中" />
          <el-option label="已归档" value="已归档" />
        </el-select>
      </el-form-item>
      <el-form-item label="客户单位">
        <el-select v-model="query.categoryId" placeholder="全部单位" clearable style="width: 240px">
          <el-option v-for="c in categoryOptions" :key="c.id" :label="c.categoryName" :value="c.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="立项时间">
        <el-date-picker
          v-model="timeRange"
          type="datetimerange"
          value-format="YYYY-MM-DD HH:mm:ss"
          start-placeholder="开始时间"
          end-placeholder="结束时间"
          style="width: 360px"
        />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :icon="Download" :loading="exporting" @click="onExport">
          导出项目列表 Excel
        </el-button>
      </el-form-item>
    </el-form>
    <el-alert
      title="导出字段：项目名称、客户单位、客户对接人、项目参与人、立项时间、预计结束时间、项目状态；文件名：项目列表_YYYYMMDD.xlsx"
      type="info"
      :closable="false"
    />
  </el-card>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Download } from '@element-plus/icons-vue'
import { listCategories } from '@/api/customer'
import { exportProjects } from '@/api/report'

const categoryOptions = ref([])
const timeRange = ref(null)
const exporting = ref(false)
const query = reactive({ projectStatus: null, categoryId: null })

async function onExport() {
  exporting.value = true
  try {
    const params = { ...query }
    if (timeRange.value?.[0]) params.startTime = timeRange.value[0]
    if (timeRange.value?.[1]) params.endTime = timeRange.value[1]
    const resp = await exportProjects(params)
    // 响应拦截器对 blob 直接放行 response 对象
    const disposition = resp.headers['content-disposition'] || ''
    const match = disposition.match(/filename\*=UTF-8''([^;]+)/)
    const filename = match ? decodeURIComponent(match[1]) : `项目列表_${new Date().toISOString().slice(0, 10).replaceAll('-', '')}.xlsx`
    const url = URL.createObjectURL(new Blob([resp.data]))
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } finally {
    exporting.value = false
  }
}

onMounted(async () => {
  const cats = await listCategories().catch(() => [])
  categoryOptions.value = cats || []
})
</script>

<style scoped>
.header { margin-bottom: 16px; }
.title { font-size: 16px; font-weight: bold; }
.filter-form { max-width: 560px; }
</style>
