<template>
  <el-card>
    <div class="header">
      <span class="title">节点模板管理</span>
      <el-button type="primary" :icon="Plus" @click="openEdit(null)">新建节点模板</el-button>
    </div>
    <el-alert
      title="节点模板是画布节点库的来源：流程模板编辑页与项目画布只能从这里的预设类型添加节点。可为每个节点配置图标与表单字段（含上传图像、链接）。"
      type="info"
      :closable="false"
      class="tip"
    />

    <!-- 节点模板卡片网格（一行约 3 个，间隔 16px） -->
    <div v-if="loading" class="card-grid">
      <div v-for="i in 6" :key="i" class="node-card skeleton-card">
        <el-skeleton :rows="3" animated />
      </div>
    </div>
    <template v-else>
      <div v-if="tableData.length" class="card-grid">
        <div v-for="row in tableData" :key="row.id" class="node-card">
          <div class="node-head">
            <div class="node-icon">
              <el-image v-if="isImageIcon(row.icon)" :src="iconUrl(row.icon)" fit="cover" class="icon-img" :alt="row.nodeTitle" />
              <el-icon v-else :size="18"><component :is="ICON_MAP[row.icon] || MessageBox" /></el-icon>
            </div>
            <el-tooltip :content="row.nodeRemark || '暂无说明'" placement="top" :disabled="!row.nodeRemark">
              <span class="node-title">{{ row.nodeTitle }}</span>
            </el-tooltip>
            <el-tag size="small" effect="plain" class="node-sort">排序 {{ row.sort }}</el-tag>
          </div>
          <div class="node-remark">{{ row.nodeRemark || '暂无说明' }}</div>
          <div class="node-fields">
            <span class="fields-label">表单字段</span>
            <template v-if="row.formFields?.length">
              <el-tag v-for="f in row.formFields" :key="f.fieldLabel" size="small" class="field-tag" effect="plain">
                {{ f.fieldLabel }}（{{ TYPE_LABELS[f.fieldType] }}）
              </el-tag>
            </template>
            <span v-else class="empty-text">无</span>
          </div>
          <div class="node-foot">
            <el-button size="small" type="primary" :icon="Edit" @click="openEdit(row)">编辑</el-button>
            <span class="foot-spacer" />
            <el-button size="small" type="danger" link :icon="Delete" @click="onDelete(row)">删除</el-button>
          </div>
        </div>
      </div>
      <el-empty v-else description="暂无节点模板">
        <el-button type="primary" :icon="Plus" @click="openEdit(null)">新建节点模板</el-button>
      </el-empty>
    </template>

    <!-- 编辑弹窗 -->
    <el-dialog v-model="editVisible" :title="editForm.id ? '编辑节点模板' : '新建节点模板'" width="min(680px, 94vw)">
      <el-form label-position="top">
        <el-form-item label="节点图标" class="icon-form-item">
          <div class="icon-picker">
            <div
              v-for="ic in PRESET_ICONS"
              :key="ic.name"
              class="icon-opt"
              :class="{ active: editForm.icon === ic.name }"
              :title="ic.label"
              @click="editForm.icon = ic.name"
            >
              <el-icon :size="18"><component :is="ICON_MAP[ic.name]" /></el-icon>
            </div>
            <el-upload
              :show-file-list="false"
              :before-upload="onUploadIcon"
              accept=".jpg,.jpeg,.png,.svg"
              class="icon-opt upload-opt"
            >
              <el-icon v-if="!uploading" :size="18"><Upload /></el-icon>
              <el-icon v-else class="is-loading" :size="18"><Loading /></el-icon>
            </el-upload>
            <el-tooltip content="点击上传自定义图标（jpg/png/svg ≤1MB）" placement="top">
              <span class="upload-hint">上传</span>
            </el-tooltip>
          </div>
          <div v-if="isImageIcon(editForm.icon)" class="icon-preview">
            <el-image :src="iconUrl(editForm.icon)" fit="cover" class="preview-img" />
            <span class="preview-name">{{ editForm.icon.split('/').pop() }}</span>
            <el-button link type="danger" size="small" @click="editForm.icon = ''">移除</el-button>
          </div>
        </el-form-item>
        <el-form-item label="节点类型名称" required>
          <el-input v-model="editForm.nodeTitle" maxlength="128" placeholder="如：需求对齐" />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="editForm.nodeRemark" type="textarea" :rows="2" placeholder="该节点在流程中的作用" />
        </el-form-item>
        <el-form-item label="面板排序">
          <el-input-number v-model="editForm.sort" :min="0" />
        </el-form-item>
      </el-form>

      <el-divider content-position="left">建议表单字段（实例化到流程模板时带出）</el-divider>
      <div v-for="(f, idx) in editForm.formFields" :key="f._key" class="field-item">
        <div class="field-head">
          <el-input v-model="f.fieldLabel" placeholder="字段名称" size="small" class="field-label-input" />
          <el-select v-model="f.fieldType" size="small" style="width: 130px">
            <el-option label="单行文本" value="text_single" />
            <el-option label="多行文本" value="text_multi" />
            <el-option label="下拉单选" value="select" />
            <el-option label="上传图像" value="image" />
            <el-option label="链接" value="link" />
          </el-select>
          <el-input-number v-model="f.sort" :min="0" size="small" style="width: 90px" />
          <el-button link type="danger" size="small" :icon="Delete" @click="editForm.formFields.splice(idx, 1)" />
        </div>
        <el-select
          v-if="f.fieldType === 'select'"
          v-model="f.selectOptions"
          multiple filterable allow-create default-first-option
          placeholder="输入选项后回车添加"
          size="small"
          class="options-editor"
        />
        <div v-else-if="f.fieldType === 'image'" class="field-tip">用户可在项目节点中上传 1 张图片（jpg/png/webp ≤5MB），可点击放大查看</div>
        <div v-else-if="f.fieldType === 'link'" class="field-tip">用户填写链接地址，点击可跳转</div>
      </div>
      <el-button size="small" :icon="Plus" plain @click="addField">添加字段</el-button>

      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitEdit">保存</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Edit, Loading, MessageBox, Plus, Upload } from '@element-plus/icons-vue'
import { addNodeTemplate, deleteNodeTemplate, listNodeTemplates, updateNodeTemplate, uploadNodeIcon } from '@/api/nodeTemplate'
import { ICON_MAP, PRESET_ICONS, iconUrl, isImageIcon } from '@/utils/nodeIcon'

const TYPE_LABELS = { text_single: '单行', text_multi: '多行', select: '下拉', image: '图像', link: '链接' }

const loading = ref(false)
const tableData = ref([])
const editVisible = ref(false)
const saving = ref(false)
const uploading = ref(false)
let fieldSeq = 0
const editForm = reactive({ id: null, icon: '', nodeTitle: '', nodeRemark: '', sort: 0, formFields: [] })

async function loadData() {
  loading.value = true
  try {
    tableData.value = await listNodeTemplates()
  } finally {
    loading.value = false
  }
}

function openEdit(row) {
  Object.assign(editForm, {
    id: row?.id ?? null,
    icon: row?.icon ?? '',
    nodeTitle: row?.nodeTitle ?? '',
    nodeRemark: row?.nodeRemark ?? '',
    sort: row?.sort ?? (tableData.value.length + 1),
    formFields: (row?.formFields || []).map((f) => ({ _key: ++fieldSeq, ...f, selectOptions: f.selectOptions || [] }))
  })
  editVisible.value = true
}

function addField() {
  editForm.formFields.push({
    _key: ++fieldSeq, fieldLabel: '', fieldType: 'text_single',
    selectOptions: [], sort: editForm.formFields.length + 1
  })
}

async function onUploadIcon(file) {
  if (!/\.(jpg|jpeg|png|svg)$/i.test(file.name)) {
    ElMessage.warning('仅支持 jpg/png/svg 格式的图标')
    return false
  }
  if (file.size > 1024 * 1024) {
    ElMessage.warning('图标大小不能超过 1MB')
    return false
  }
  uploading.value = true
  try {
    const data = await uploadNodeIcon(file)
    editForm.icon = data.iconPath
    ElMessage.success('图标已上传')
  } catch {
    /* 拦截器已提示 */
  } finally {
    uploading.value = false
  }
  return false
}

async function submitEdit() {
  if (!editForm.nodeTitle.trim()) {
    ElMessage.warning('请填写节点类型名称')
    return
  }
  for (const f of editForm.formFields) {
    if (!f.fieldLabel.trim()) {
      ElMessage.warning('存在未命名的表单字段')
      return
    }
    if (f.fieldType === 'select' && f.selectOptions.length === 0) {
      ElMessage.warning(`字段「${f.fieldLabel}」是下拉单选，请添加选项`)
      return
    }
  }
  saving.value = true
  try {
    const payload = {
      nodeTitle: editForm.nodeTitle.trim(),
      nodeRemark: editForm.nodeRemark,
      icon: editForm.icon || null,
      sort: editForm.sort,
      formFields: editForm.formFields.map((f) => ({
        fieldLabel: f.fieldLabel,
        fieldType: f.fieldType,
        selectOptions: f.fieldType === 'select' ? f.selectOptions : null,
        sort: f.sort
      }))
    }
    if (editForm.id) {
      await updateNodeTemplate({ id: editForm.id, ...payload })
    } else {
      await addNodeTemplate(payload)
    }
    ElMessage.success('已保存')
    editVisible.value = false
    loadData()
  } finally {
    saving.value = false
  }
}

async function onDelete(row) {
  await ElMessageBox.confirm(
    `确定删除节点模板「${row.nodeTitle}」吗？已生成的流程模板与项目节点不受影响。`,
    '删除确认',
    { type: 'error', confirmButtonText: '确认删除' }
  )
  await deleteNodeTemplate({ id: row.id })
  ElMessage.success('已删除')
  loadData()
}

onMounted(loadData)
</script>

<style scoped>
.header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.title { font-size: 16px; font-weight: bold; }
.tip { margin-bottom: 12px; }
.empty-text { color: var(--lk-text-3); font-size: 13px; }
.field-tag { margin: 2px 4px 2px 0; }
.field-item { border: 1px solid #ebeef5; border-radius: 6px; padding: 8px; margin-bottom: 8px; }
.field-head { display: flex; gap: 6px; align-items: center; }
.field-label-input { flex: 1; }
.options-editor { width: 100%; margin-top: 6px; }
.field-tip { font-size: 12px; color: var(--lk-text-3); margin-top: 6px; }

/* 图标选择器 */
.icon-picker { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
.icon-opt {
  width: 40px; height: 40px;
  border: 1px solid var(--lk-border, #ebeef5);
  border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  color: var(--lk-text-2, #606266);
  cursor: pointer;
  transition: all 0.15s;
}
.icon-opt:hover { border-color: var(--lk-primary, #409eff); color: var(--lk-primary, #409eff); }
.icon-opt.active { border-color: var(--lk-primary, #409eff); background: rgba(64, 158, 255, 0.1); color: var(--lk-primary, #409eff); }
.upload-opt { background: var(--lk-fill, #f5f7fa); }
.upload-hint { font-size: 12px; color: var(--lk-text-3); }
.icon-preview { display: flex; align-items: center; gap: 8px; margin-top: 8px; }
.preview-img { width: 44px; height: 44px; border-radius: 8px; border: 1px solid var(--lk-border); }
.preview-name { font-size: 12px; color: var(--lk-text-3); word-break: break-all; }

/* ---- 卡片网格 ---- */
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

.node-card {
  border: 1px solid var(--lk-border, #ebeef5);
  border-radius: 10px;
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  transition: box-shadow 0.2s, border-color 0.2s, transform 0.2s;
  background: var(--el-bg-color, #fff);
}
.node-card:hover {
  border-color: var(--lk-primary, #409eff);
  box-shadow: var(--lk-shadow-md, 0 6px 18px rgba(64, 158, 255, 0.12));
  transform: translateY(-2px);
}
.skeleton-card { padding: 20px 16px; }

.node-head { display: flex; align-items: center; gap: 8px; }
.node-icon {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: rgba(64, 158, 255, 0.1);
  color: var(--lk-primary, #409eff);
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}
.icon-img { width: 100%; height: 100%; }
.node-title { font-size: 15px; font-weight: bold; flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.node-sort { flex-shrink: 0; }

.node-remark {
  font-size: 13px;
  color: var(--lk-text-3);
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  min-height: 40px;
}

.node-fields { flex: 1; }
.fields-label { display: block; font-size: 12px; color: var(--lk-text-3); margin-bottom: 4px; }

.node-foot {
  display: flex;
  align-items: center;
  gap: 8px;
  border-top: 1px solid var(--lk-border, #ebeef5);
  padding-top: 10px;
}
.foot-spacer { flex: 1; }
</style>
