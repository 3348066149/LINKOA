<template>
  <!-- 动态表单渲染器：单行/多行/下拉/上传图像/链接（V1.4.3） -->
  <div class="dynamic-form">
    <el-empty v-if="fields.length === 0" description="该节点无自定义表单" :image-size="60" />
    <el-form v-else label-position="top" :disabled="disabled">
      <el-form-item v-for="field in fields" :key="field.id" :label="field.fieldLabel">
        <!-- 单行文本 -->
        <el-input
          v-if="field.fieldType === 'text_single'"
          v-model="values[field.id]"
          placeholder="请输入"
          clearable
        />
        <!-- 多行文本 -->
        <el-input
          v-else-if="field.fieldType === 'text_multi'"
          v-model="values[field.id]"
          type="textarea"
          :rows="3"
          placeholder="请输入"
        />
        <!-- 下拉单选 -->
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
        <!-- 上传图像（单张可替换，点击放大预览） -->
        <div v-else-if="field.fieldType === 'image'" class="image-field">
          <el-upload
            :show-file-list="false"
            :before-upload="(f) => onUploadImage(f, field)"
            accept=".jpg,.jpeg,.png,.webp"
            :disabled="disabled"
            class="image-upload"
          >
            <div class="image-box">
              <el-image
                v-if="values[field.id]"
                :ref="(el) => setImageRef(el, field.id)"
                :src="imgSrc(values[field.id])"
                :preview-src-list="[imgSrc(values[field.id])]"
                :preview-teleported="true"
                fit="cover"
                class="image-preview"
              />
              <div v-else class="image-empty">
                <el-icon :size="22"><Picture /></el-icon>
                <span>点击上传图片</span>
              </div>
              <div v-if="values[field.id]" class="image-mask">
                <el-icon v-if="uploading[field.id]" class="is-loading"><Loading /></el-icon>
                <template v-else>
                  <el-icon :title="'放大查看'" @click.stop="showImagePreview(field.id)"><ZoomIn /></el-icon>
                  <el-icon :title="'替换图片'" @click.stop="replaceImage(field)"><RefreshLeft /></el-icon>
                  <el-icon :title="'删除图片'" @click.stop="values[field.id] = ''"><Delete /></el-icon>
                </template>
              </div>
            </div>
          </el-upload>
          <div class="image-tip">jpg/png/webp ≤5MB，可点击放大查看，可替换或删除</div>
          <div v-if="field.updateTime" class="image-time">🕐 上传时间：{{ formatTime(field.updateTime) }}</div>
        </div>
        <!-- 链接 -->
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
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Delete, Loading, Picture, RefreshLeft, ZoomIn } from '@element-plus/icons-vue'
import { uploadFormImage } from '@/api/projectNode'

const props = defineProps({
  // 表单字段定义 + 已填值：[{id, fieldLabel, fieldType, selectOptions, fieldValue}]
  fields: { type: Array, default: () => [] },
  // 归档状态禁用
  disabled: { type: Boolean, default: false },
  saving: { type: Boolean, default: false }
})

const emit = defineEmits(['save'])

// 本地值副本：{[fieldId]: value}
const values = reactive({})
const uploading = reactive({})
// el-image 实例集合：{[fieldId]: el-image 组件实例}，用于放大镜按钮手动触发预览
const imageRefs = reactive({})
function setImageRef(el, fieldId) {
  // 函数 ref 回调，每次渲染/卸载都调；保证引用与元素一致
  if (el) imageRefs[fieldId] = el
  else delete imageRefs[fieldId]
}
function showImagePreview(fieldId) {
  // el-image 暴露 showPreview()：点击放大镜时主动打开预览（@click.stop 同时阻止穿透到 el-upload 触发选文件）
  imageRefs[fieldId]?.showPreview?.()
}

const initialSnapshot = ref('')
watch(
  () => props.fields,
  (val) => {
    Object.keys(values).forEach((k) => delete values[k])
    val.forEach((f) => { values[f.id] = f.fieldValue ?? '' })
    // 记录初始快照：切换节点/重置后同步更新，故 isDirty 仅反映"本次编辑未保存"
    initialSnapshot.value = JSON.stringify(values)
  },
  { immediate: true, deep: true }
)
// 脏检测：当前输入值是否与初始快照不同（未保存修改）
const isDirty = computed(() => JSON.stringify(values) !== initialSnapshot.value)

function imgSrc(path) {
  if (!path) return ''
  if (path.startsWith('http')) return path
  return `/uploads/${path.replace(/^uploads\//, '')}`
}

async function onUploadImage(file, field) {
  if (!/\.(jpg|jpeg|png|webp)$/i.test(file.name)) {
    ElMessage.warning('仅支持 jpg/png/webp 格式的图片')
    return false
  }
  if (file.size > 5 * 1024 * 1024) {
    ElMessage.warning('图片大小不能超过 5MB')
    return false
  }
  uploading[field.id] = true
  try {
    const data = await uploadFormImage(file)
    values[field.id] = data.imagePath
    ElMessage.success('图片已上传')
  } catch {
    /* 拦截器已提示 */
  } finally {
    uploading[field.id] = false
  }
  return false
}

function replaceImage(field) {
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = '.jpg,.jpeg,.png,.webp'
  input.onchange = () => {
    if (input.files?.[0]) onUploadImage(input.files[0], field)
  }
  input.click()
}

function normalizeLink(v) {
  return /^https?:\/\//i.test(v) ? v : `https://${v}`
}

function formatTime(t) { return t ? t.slice(0, 16) : '' }

function collect() {
  // 全量覆盖提交：[{id, fieldValue}]
  return props.fields.map((f) => ({
    id: f.id,
    fieldValue: values[f.id] === '' ? null : values[f.id]
  }))
}

function onSave() {
  emit('save', collect())
}

// 保存成功后由父组件调用，将当前输入标记为「已保存」基准，避免重复弹未保存提示
function markClean() {
  initialSnapshot.value = JSON.stringify(values)
}

// 暴露给父组件：顶部栏「保存」按钮可主动收集表单值；isDirty 供切换节点/离开页前拦截未保存修改；markClean 用于保存后清脏
defineExpose({ collect, isDirty, markClean })
</script>

<style scoped>
.dynamic-form { width: 100%; }
.save-btn { width: 100%; margin-top: 8px; }

/* 图像字段 */
.image-field { width: 100%; }
.image-box {
  position: relative;
  width: 140px;
  height: 140px;
  border: 1px dashed var(--lk-border, #dcdfe6);
  border-radius: 10px;
  overflow: hidden;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--lk-fill, #f5f7fa);
}
.image-box:hover .image-mask { opacity: 1; }
.image-preview { width: 100%; height: 100%; display: block; }
.image-empty { display: flex; flex-direction: column; align-items: center; gap: 6px; color: var(--lk-text-3, #6f737a); font-size: 12px; }
.image-mask {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 14px;
  color: #fff;
  font-size: 18px;
  opacity: 0;
  transition: opacity 0.15s;
}
.image-mask .el-icon { cursor: pointer; }
.image-mask .el-icon:hover { color: #66b1ff; }
.image-tip { font-size: 12px; color: var(--lk-text-3, #6f737a); margin-top: 6px; }
.image-time { font-size: 12px; color: var(--lk-text-3, #6f737a); margin-top: 4px; }

/* 链接字段 */
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
