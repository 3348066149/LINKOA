<template>
  <div class="dynamic-form">
    <el-empty v-if="fields.length === 0" description="该节点无自定义表单" :image-size="60" />
    <el-form v-else label-position="top" :disabled="disabled">
      <el-form-item v-for="field in fields" :key="field.id" :label="field.fieldLabel">
        <el-input
          v-if="field.fieldType === 'text_single'"
          v-model="values[field.id]"
          placeholder="请输入"
          clearable
        />
        <el-input
          v-else-if="field.fieldType === 'text_multi'"
          v-model="values[field.id]"
          type="textarea"
          :rows="3"
          placeholder="请输入"
        />
        <el-select
          v-else-if="field.fieldType === 'select'"
          v-model="values[field.id]"
          placeholder="请选择"
          clearable
          style="width: 100%"
        >
          <el-option
            v-for="opt in field.selectOptions || []"
            :key="opt"
            :label="opt"
            :value="opt"
          />
        </el-select>

        <!-- 多文件上传 -->
        <div v-else-if="field.fieldType === 'image'" class="image-field">
          <!-- 图片：网格卡片 -->
          <div v-if="getFiles(field.id).some(isImage)" class="file-grid">
            <div v-for="file in getFiles(field.id).filter(isImage)" :key="'c'+file" class="file-card">
              <el-image
                :src="imgSrc(file)"
                :preview-src-list="getFiles(field.id).filter(isImage).map(imgSrc)"
                :preview-teleported="true"
                fit="cover"
                class="file-thumb"
              />
              <div class="file-card-name" :title="fileName(file)">{{ fileName(file) }}</div>
              <div class="file-mask">
                <el-icon :title="'预览'" @click.stop="onPreview(file)"><ZoomIn /></el-icon>
                <el-icon :title="'删除'" @click.stop="removeFileByPath(field.id, file)"><Delete /></el-icon>
              </div>
            </div>
          </div>
          <!-- 其他文件：列表条目 -->
          <div v-if="getFiles(field.id).some(f => !isImage(f))" class="file-list">
            <div v-for="file in getFiles(field.id).filter(f => !isImage(f))" :key="'l'+file" class="file-item">
              <span class="file-type-badge" :class="extOf(file)">{{ fileTag(file) }}</span>
              <span class="file-item-name" :title="fileName(file)">{{ fileName(file) }}</span>
              <el-icon :title="isPdf(file)||isVideo(file) ? '在线查看' : '下载'" class="file-item-icon" @click="onPreview(file)"><Download /></el-icon>
              <el-icon :title="'删除'" class="file-item-icon danger" @click="removeFileByPath(field.id, file)"><Delete /></el-icon>
            </div>
          </div>
          <el-upload
            :show-file-list="false"
            :before-upload="(f) => onUploadFile(f, field)"
            accept="*/*"
            :disabled="disabled"
            multiple
            class="file-upload-add"
          >
            <div class="file-add-box">
              <el-icon :size="18"><Plus /></el-icon>
              <span>上传文件</span>
            </div>
          </el-upload>
          <div class="image-tip">支持图片/PDF/视频/Word/Excel等，可上传多个</div>
          <div v-if="field.updateTime" class="image-time">🕐 上传时间：{{ formatTime(field.updateTime) }}</div>
        </div>

        <div v-else-if="field.fieldType === 'link'" class="link-field">
          <el-input
            v-model="values[field.id]"
            placeholder="https:// 或 http:// 开头的链接地址"
            clearable
          />
          <div v-if="values[field.id]" class="link-hint">
            链接：<a :href="normalizeLink(values[field.id])" target="_blank" rel="noopener" @click.stop>
              {{ values[field.id] }}
            </a>
          </div>
        </div>
      </el-form-item>
    </el-form>
    <el-button
      v-if="fields.length > 0 && !disabled"
      type="primary"
      class="save-btn"
      :loading="saving"
      @click="onSave"
    >
      保存表单
    </el-button>
  </div>
</template>

<script setup>
import { reactive, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Delete, Download, Plus, ZoomIn } from '@element-plus/icons-vue'
import { uploadFormImage } from '@/api/projectNode'

const props = defineProps({
  fields: { type: Array, default: () => [] },
  disabled: { type: Boolean, default: false },
  saving: { type: Boolean, default: false }
})

const emit = defineEmits(['save'])
const values = reactive({})

const IMAGE_EXTS = ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp']

function extOf(path) {
  const name = path.split('/').pop() || path
  return (name.split('.').pop() || '').toLowerCase()
}
function fileName(path) {
  const name = path.split('/').pop() || path
  const idx = name.indexOf('_')
  // 新格式：{uuid}_{原文件名}，去掉 uuid_ 前缀
  if (idx > 0 && /^[0-9a-f]{20,}$/.test(name.slice(0, idx))) return name.slice(idx + 1)
  // 旧数据：没有 uuid 前缀
  return name
}
function isImage(path) { return IMAGE_EXTS.includes(extOf(path)) }
function isPdf(path) { return extOf(path) === 'pdf' }
function isVideo(path) { return ['mp4', 'webm', 'ogg'].includes(extOf(path)) }
function fileTag(path) {
  const ext = extOf(path)
  const map = { psd: 'PSD', ai: 'AI', zip: 'ZIP', rar: 'RAR', pdf: 'PDF', doc: 'DOC', docx: 'DOC', xls: 'XLS', xlsx: 'XLS', mp4: 'MP4', ppt: 'PPT', pptx: 'PPT', mp3: 'MP3' }
  return map[ext] || 'FILE'
}

watch(
  () => props.fields,
  (val) => {
    Object.keys(values).forEach((k) => delete values[k])
    val.forEach((f) => {
      if (f.fieldType === 'image') {
        // image 字段：兼容旧单值，统一成 JSON 数组
        if (f.fieldValue) {
          try {
            const parsed = JSON.parse(f.fieldValue)
            values[f.id] = Array.isArray(parsed) ? f.fieldValue : JSON.stringify([f.fieldValue])
          } catch {
            values[f.id] = JSON.stringify([f.fieldValue])
          }
        } else {
          values[f.id] = '[]'
        }
      } else {
        // 其他字段：保持原始值
        values[f.id] = f.fieldValue ?? ''
      }
    })
  },
  { immediate: true, deep: true }
)

// 解析文件数组：兼容 JSON 数组（多文件）与旧单值字符串。
// 必须过滤 null/空串/非字符串项，避免下游 .split('.') 抛异常导致表单区白屏。
function getFiles(fieldId) {
  const raw = values[fieldId]
  if (!raw) return []
  let arr
  try {
    const parsed = JSON.parse(raw)
    arr = Array.isArray(parsed) ? parsed : [parsed]
  } catch {
    arr = [raw]
  }
  return arr.filter((p) => typeof p === 'string' && p.trim() !== '')
}

function addFile(fieldId, path) {
  const arr = getFiles(fieldId)
  arr.push(path)
  values[fieldId] = JSON.stringify(arr)
}

function removeFile(fieldId, idx) {
  const arr = getFiles(fieldId)
  arr.splice(idx, 1)
  values[fieldId] = JSON.stringify(arr)
}

function removeFileByPath(fieldId, path) {
  const arr = getFiles(fieldId).filter(f => f !== path)
  values[fieldId] = JSON.stringify(arr)
}

function imgSrc(path) {
  if (!path) return ''
  if (path.startsWith('http')) return path
  return `/uploads/${path.replace(/^uploads\//, '')}`
}

function onPreview(file) {
  window.open(imgSrc(file), '_blank')
}

async function onUploadFile(file, field) {
  try {
    const data = await uploadFormImage(file)
    addFile(field.id, data.imagePath)
    ElMessage.success('文件已上传')
  } catch {
    /* 拦截器已提示 */
  }
  return false
}

function normalizeLink(v) {
  return /^https?:\/\//i.test(v) ? v : `https://${v}`
}

function formatTime(t) { return t ? t.slice(0, 16) : '' }

function collect() {
  return props.fields.map((f) => {
    if (f.fieldType === 'image') {
      const arr = getFiles(f.id)
      return { id: f.id, fieldValue: arr.length === 0 ? null : JSON.stringify(arr) }
    }
    return { id: f.id, fieldValue: values[f.id] === '' ? null : values[f.id] }
  })
}

function onSave() {
  emit('save', collect())
}

function markClean() {}

defineExpose({ collect, markClean })
</script>

<style scoped>
.dynamic-form { width: 100%; }
.save-btn { width: 100%; margin-top: 8px; }

.image-field { width: 100%; }

/* 图片：网格卡片 */
.file-grid { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 8px; }
.file-card {
  position: relative;
  width: 100px;
  height: 100px;
  border-radius: 8px;
  overflow: visible;
  border: 1px solid var(--lk-border, #dcdfe6);
  background: #fff;
}
.file-thumb { width: 100%; height: 100%; object-fit: cover; display: block; border-radius: 8px; }
.file-card-name {
  position: absolute; bottom: -20px; left: 0; right: 0;
  font-size: 11px; color: var(--lk-text-2, #606266);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  text-align: center;
}
.file-mask {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: #fff;
  font-size: 16px;
  opacity: 0;
  transition: opacity 0.15s;
  border-radius: 8px;
}
.file-card:hover .file-mask { opacity: 1; }
.file-mask .el-icon { cursor: pointer; }
.file-mask .el-icon:hover { color: #66b1ff; }

/* 其他文件：列表条目 */
.file-list { margin-bottom: 8px; }
.file-item {
  display: flex; align-items: center; gap: 8px;
  padding: 6px 10px;
  border: 1px solid var(--lk-border, #e4e7ed);
  border-radius: 6px;
  margin-bottom: 4px;
  background: #fafafa;
}
.file-type-badge {
  font-size: 10px; font-weight: 700; color: #fff;
  padding: 3px 6px; border-radius: 4px; min-width: 36px; text-align: center;
}
.file-type-badge.pdf { background: #e74c3c; }
.file-type-badge.mp4, .file-type-badge.video { background: #3498db; }
.file-type-badge.doc, .file-type-badge.docx { background: #2b579a; }
.file-type-badge.xls, .file-type-badge.xlsx { background: #217346; }
.file-type-badge.ppt, .file-type-badge.pptx { background: #d24726; }
.file-type-badge.psd { background: #001d34; }
.file-type-badge.ai { background: #ff61f6; }
.file-type-badge.zip, .file-type-badge.rar { background: #95a5a6; }
.file-type-badge.mp3 { background: #9b59b6; }
.file-item-name {
  flex: 1; font-size: 13px; color: var(--lk-text-1, #303133);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.file-item-icon { cursor: pointer; color: var(--lk-text-3, #909399); font-size: 14px; }
.file-item-icon:hover { color: var(--lk-primary, #409eff); }
.file-item-icon.danger:hover { color: #f56c6c; }

.file-upload-add { margin-top: 4px; }
.file-add-box {
  width: 100%;
  min-height: 36px;
  border: 1px dashed var(--lk-border, #dcdfe6);
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  color: var(--lk-text-3, #6f737a);
  font-size: 13px;
  cursor: pointer;
  background: var(--lk-fill, #f9fafc);
  padding: 8px;
}
.file-add-box:hover { border-color: var(--lk-primary, #409eff); color: var(--lk-primary, #409eff); }

.image-tip { font-size: 12px; color: var(--lk-text-3, #6f737a); margin-top: 6px; }
.image-time { font-size: 12px; color: var(--lk-text-3, #6f737a); margin-top: 4px; }

.link-hint {
  margin-top: 6px;
  font-size: 12px;
  color: var(--lk-text-3, #6f737a);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.link-hint a { color: var(--lk-primary, #409eff); }
</style>
