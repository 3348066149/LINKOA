<template>
  <div>
    <el-card class="filter-card">
      <el-form inline @submit.prevent>
        <el-form-item label="客户单位">
          <el-select v-model="query.categoryId" placeholder="全部单位" clearable style="width: 160px" @change="onSearch">
            <el-option v-for="c in categories" :key="c.id" :label="c.categoryName" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="对接人名称">
          <el-input v-model="query.customerName" placeholder="模糊搜索" clearable style="width: 180px" @keyup.enter="onSearch" />
        </el-form-item>
        <el-form-item label="排序">
          <el-select v-model="query.sortField" style="width: 130px" @change="onSearch">
            <el-option label="创建时间" value="createTime" />
            <el-option label="名称" value="customerName" />
            <el-option label="分类" value="categoryName" />
          </el-select>
          <el-button class="sort-dir" :icon="query.sortOrder === 'asc' ? SortUp : SortDown" :title="query.sortOrder === 'asc' ? '升序' : '降序'" @click="toggleSortOrder" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="onSearch">搜索</el-button>
          <el-button :icon="Refresh" @click="onReset">重置</el-button>
          <template v-if="canWrite">
            <el-button type="primary" :icon="Plus" @click="openEdit(null)">新增对接人</el-button>
            <el-button :icon="FolderOpened" @click="catDialogVisible = true">单位管理</el-button>
          </template>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 客户卡片网格（一行 3 个，间隔 16px） -->
    <el-card>
      <div v-if="loading" class="card-grid">
        <div v-for="i in 6" :key="i" class="cust-card skeleton-card">
          <div class="sk-body">
            <el-skeleton :rows="3" animated />
          </div>
          <div class="sk-cover" />
        </div>
      </div>

      <template v-else>
        <div v-if="tableData.length" class="card-grid">
          <div v-for="row in tableData" :key="row.id" class="cust-card">
            <!-- 左侧信息区 -->
            <div class="cust-main">
              <div class="cust-title">
                <span class="cust-name" :title="row.customerName">{{ row.customerName }}</span>
                <el-tag size="small" :type="row.categoryName ? 'primary' : 'info'" effect="plain">
                  {{ row.categoryName || '未归属单位' }}
                </el-tag>
              </div>

              <div class="cust-meta">
                <div v-if="row.contact" class="meta-row">
                  <el-icon class="meta-icon"><Phone /></el-icon>
                  <span class="meta-text" :title="row.contact">{{ row.contact }}</span>
                </div>
                <div v-else class="meta-row muted">
                  <el-icon class="meta-icon"><Phone /></el-icon>
                  <span class="meta-text">未填写联系方式</span>
                </div>
                <div class="meta-row">
                  <el-icon class="meta-icon"><Clock /></el-icon>
                  <span class="meta-text">创建于 {{ (row.createTime || '').slice(0, 10) }}</span>
                </div>
              </div>

              <div class="cust-remark" :title="row.remark || ''">{{ row.remark || '暂无备注' }}</div>

              <div class="cust-foot">
                <span class="cust-id">#{{ row.id }}</span>
                <div v-if="canWrite" class="act-group">
                  <el-button size="small" type="primary" :icon="Edit" @click="openEdit(row)">编辑</el-button>
                  <el-button size="small" type="danger" :icon="Delete" @click="onDelete(row)">删除</el-button>
                </div>
              </div>
            </div>

            <!-- 右侧封面图：点击放大查看 -->
            <div class="cust-cover" :class="{ 'is-empty': !row.coverImage }" @click="onPreviewCover(row)" :title="row.coverImage ? '点击查看大图' : '点击上传封面图'">
              <el-image
                v-if="row.coverImage"
                :src="coverUrl(row.coverImage)"
                :preview-src-list="[coverUrl(row.coverImage)]"
                :preview-teleported="true"
                fit="cover"
                class="cover-img"
                :alt="row.customerName"
                @click.stop
              />
              <div v-else class="cover-ph">
                <el-icon><Picture /></el-icon>
                <span>{{ canWrite ? '上传图片' : '暂无图片' }}</span>
              </div>
            </div>
          </div>
        </div>

        <el-empty v-else description="暂无对接人">
          <el-button v-if="canWrite" type="primary" :icon="Plus" @click="openEdit(null)">新增对接人</el-button>
        </el-empty>
      </template>

      <el-pagination
        v-model:current-page="query.pageNum"
        v-model:page-size="query.pageSize"
        :total="total"
        :page-sizes="[9, 18, 36]"
        layout="total, sizes, prev, pager, next"
        class="pagination"
        @change="loadData"
      />
    </el-card>

    <!-- 客户编辑弹窗 -->
    <el-dialog v-model="editVisible" :title="editForm.id ? '编辑对接人' : '新增对接人'" width="min(520px, 92vw)">
      <el-form :model="editForm" label-width="90px">
        <el-form-item label="封面图">
          <div class="cover-upload">
            <el-upload
              v-if="canWrite"
              :show-file-list="false"
              :before-upload="beforeCoverUpload"
              :http-request="doUploadCover"
              accept="image/jpeg,image/png,image/webp"
            >
              <div class="cover-box">
                <el-image
                  v-if="editForm.coverImage"
                  :src="coverUrl(editForm.coverImage)"
                  :preview-src-list="[coverUrl(editForm.coverImage)]"
                  :preview-teleported="true"
                  fit="cover"
                  class="cover-box-img"
                  @click.stop
                />
                <div v-else class="cover-box-ph">
                  <el-icon><Plus /></el-icon>
                  <span>上传图片</span>
                </div>
              </div>
            </el-upload>
            <div v-else class="cover-box">
              <el-image
                v-if="editForm.coverImage"
                :src="coverUrl(editForm.coverImage)"
                :preview-src-list="[coverUrl(editForm.coverImage)]"
                :preview-teleported="true"
                fit="cover"
                class="cover-box-img"
                @click.stop
              />
              <div v-else class="cover-box-ph"><el-icon><Picture /></el-icon><span>暂无图片</span></div>
            </div>
            <div class="cover-tip">
              <div class="tip-line">建议 1:1 方形图，jpg / png / webp，≤5MB</div>
              <el-button v-if="canWrite && editForm.coverImage" link type="danger" size="small" @click="onRemoveCover">移除封面</el-button>
            </div>
          </div>
        </el-form-item>
        <el-form-item label="对接人姓名" required>
          <el-input v-model="editForm.customerName" maxlength="128" placeholder="请输入对接人姓名" />
        </el-form-item>
        <el-form-item label="所属单位" required>
          <el-select v-model="editForm.categoryId" placeholder="请选择客户单位" style="width: 100%">
            <el-option v-for="c in categories" :key="c.id" :label="c.categoryName" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="联系方式">
          <el-input v-model="editForm.contact" maxlength="128" placeholder="电话 / 微信 / 邮箱" />
        </el-form-item>
        <el-form-item label="客户备注">
          <el-input v-model="editForm.remark" type="textarea" :rows="3" placeholder="对接人、合作信息等" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitEdit">保存</el-button>
      </template>
    </el-dialog>

    <!-- 客户单位管理弹窗 -->
    <el-dialog v-model="catDialogVisible" title="客户单位管理" width="min(480px, 92vw)">
      <div class="cat-add">
        <el-input v-model="newCatName" placeholder="新单位名称" size="small" style="flex: 1" />
        <el-button type="primary" size="small" @click="onAddCategory">添加</el-button>
      </div>
      <el-table :data="categories" size="small">
        <el-table-column label="单位名称">
          <template #default="{ row }">
            <el-input v-if="editingCatId === row.id" v-model="editingCatName" size="small" />
            <span v-else>{{ row.categoryName }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150">
          <template #default="{ row }">
            <template v-if="editingCatId === row.id">
              <el-button link type="primary" size="small" @click="onSaveCategory(row)">保存</el-button>
              <el-button link size="small" @click="editingCatId = null">取消</el-button>
            </template>
            <template v-else>
              <el-button link type="primary" size="small" @click="startEditCat(row)">改名</el-button>
              <el-button link type="danger" size="small" @click="onDeleteCategory(row)">删除</el-button>
            </template>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Clock, Delete, Edit, FolderOpened, Phone, Picture, Plus, Refresh, Search, SortDown, SortUp
} from '@element-plus/icons-vue'
import {
  addCategory, addCustomer, deleteCategory, deleteCustomer,
  listCategories, listCustomers, removeCustomerCover, updateCategory,
  updateCustomer, uploadCustomerCover
} from '@/api/customer'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const canWrite = computed(() => ['管理员'].includes(userStore.role))

const loading = ref(false)
const tableData = ref([])
const total = ref(0)
const categories = ref([])
const query = reactive({
  pageNum: 1, pageSize: 9, categoryId: null, customerName: '',
  sortField: 'createTime', sortOrder: 'desc'
})

async function loadData() {
  loading.value = true
  try {
    const data = await listCustomers({ ...query })
    tableData.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

async function loadCategories() { categories.value = await listCategories() }

function onSearch() { query.pageNum = 1; loadData() }

function toggleSortOrder() {
  query.sortOrder = query.sortOrder === 'asc' ? 'desc' : 'asc'
  loadData()
}

function onReset() {
  Object.assign(query, {
    pageNum: 1, pageSize: 9, categoryId: null, customerName: '',
    sortField: 'createTime', sortOrder: 'desc'
  })
  loadData()
}

function coverUrl(path) { return `/uploads/${path}` }

// ---- 客户编辑 ----
const editVisible = ref(false)
const saving = ref(false)
const editForm = reactive({ id: null, categoryId: null, customerName: '', contact: '', remark: '', coverImage: null })

function openEdit(row) {
  Object.assign(editForm, row
    ? {
        id: row.id, categoryId: row.categoryId, customerName: row.customerName,
        contact: row.contact || '', remark: row.remark || '', coverImage: row.coverImage || null
      }
    : { id: null, categoryId: null, customerName: '', contact: '', remark: '', coverImage: null })
  editVisible.value = true
}

async function submitEdit() {
  if (!editForm.customerName || !editForm.categoryId) {
    ElMessage.warning('请填写对接人姓名并选择所属单位')
    return
  }
  saving.value = true
  try {
    const payload = {
      categoryId: editForm.categoryId,
      customerName: editForm.customerName,
      contact: editForm.contact || null,
      remark: editForm.remark || null
    }
    if (editForm.id) {
      await updateCustomer({ id: editForm.id, ...payload })
    } else {
      await addCustomer(payload)
    }
    ElMessage.success('已保存')
    editVisible.value = false
    loadData()
  } finally {
    saving.value = false
  }
}

// ---- 封面图 ----
function beforeCoverUpload(file) {
  const okType = ['image/jpeg', 'image/png', 'image/webp'].includes(file.type)
  if (!okType) { ElMessage.error('封面图仅支持 jpg / png / webp 格式'); return false }
  if (file.size > 5 * 1024 * 1024) { ElMessage.error('封面图大小不能超过 5MB'); return false }
  if (!editForm.id) { ElMessage.warning('请先保存客户信息，再上传封面图'); return false }
  return true
}

async function doUploadCover({ file }) {
  try {
    const res = await uploadCustomerCover(editForm.id, file)
    editForm.coverImage = res.coverImage
    ElMessage.success('封面图已上传')
    loadData()
  } catch {
    ElMessage.error('封面图上传失败')
  }
}

async function onRemoveCover() {
  if (!editForm.id) { editForm.coverImage = null; return }
  await removeCustomerCover(editForm.id)
  editForm.coverImage = null
  ElMessage.success('已移除封面图')
  loadData()
}

// 卡片上点击封面：无图时直接进入编辑弹窗上传
function onPreviewCover(row) {
  if (!row.coverImage && canWrite.value) openEdit(row)
}

async function onDelete(row) {
  await ElMessageBox.confirm(`确定删除对接人「${row.customerName}」吗？其下项目与关联数据将一并受影响，删除后不可恢复！`, '删除确认', { type: 'error', confirmButtonText: '确认删除' })
  await deleteCustomer({ id: row.id })
  ElMessage.success('已删除')
  loadData()
}

// ---- 客户单位管理 ----
const catDialogVisible = ref(false)
const newCatName = ref('')
const editingCatId = ref(null)
const editingCatName = ref('')

async function onAddCategory() {
  if (!newCatName.value.trim()) return
  await addCategory({ categoryName: newCatName.value.trim() })
  newCatName.value = ''
  ElMessage.success('已添加')
  loadCategories()
}

function startEditCat(row) {
  editingCatId.value = row.id
  editingCatName.value = row.categoryName
}

async function onSaveCategory(row) {
  await updateCategory({ id: row.id, categoryName: editingCatName.value.trim() })
  editingCatId.value = null
  ElMessage.success('已保存')
  loadCategories()
}

async function onDeleteCategory(row) {
  await ElMessageBox.confirm(`确定删除客户单位「${row.categoryName}」吗？删除后不可恢复。`, '删除确认', { type: 'error', confirmButtonText: '确认删除' })
  await deleteCategory({ id: row.id })
  ElMessage.success('已删除')
  loadCategories()
}

onMounted(() => { loadData(); loadCategories() })
</script>

<style scoped>
.filter-card { margin-bottom: 12px; }
.pagination { margin-top: 12px; justify-content: flex-end; }
.cat-add { display: flex; gap: 8px; margin-bottom: 12px; }
.sort-dir { margin-left: 8px; }

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

.cust-card {
  border: 1px solid var(--lk-border, #ebeef5);
  border-radius: 12px;
  padding: 16px;
  display: flex;
  gap: 14px;
  min-height: 190px;
  transition: box-shadow 0.2s, border-color 0.2s, transform 0.2s;
}
.cust-card:hover {
  border-color: var(--lk-primary, #409eff);
  box-shadow: var(--lk-shadow-md, 0 6px 18px rgba(64, 158, 255, 0.14));
  transform: translateY(-2px);
}
.skeleton-card { align-items: stretch; }
.sk-body { flex: 1; }
.sk-cover {
  width: 112px;
  flex: none;
  border-radius: 10px;
  background: var(--lk-fill, #f5f7fa);
}

.cust-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 8px; }

.cust-title { display: flex; align-items: flex-start; justify-content: space-between; gap: 8px; }
.cust-name {
  font-size: 17px;
  font-weight: 700;
  color: var(--lk-text-1, #303133);
  line-height: 1.35;
  word-break: break-all;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.cust-meta { display: flex; flex-direction: column; gap: 4px; }
.meta-row { display: flex; align-items: center; gap: 6px; font-size: 13px; color: var(--lk-text-2, #606266); }
.meta-row.muted .meta-text { color: var(--lk-text-3, #6f737a); }
.meta-icon { font-size: 14px; color: var(--lk-text-3, #6f737a); flex: none; }
.meta-text { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.cust-remark {
  flex: 1;
  font-size: 13px;
  color: var(--lk-text-2, #606266);
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  min-height: 40px;
}

.cust-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  border-top: 1px solid var(--lk-border, #ebeef5);
  padding-top: 10px;
  margin-top: auto;
}
.cust-id { font-size: 12px; color: var(--lk-text-3, #6f737a); }

/* 编辑 + 删除 紧挨成组 */
.act-group { display: flex; gap: 6px; flex: none; }

/* 右侧封面图 */
.cust-cover {
  width: 112px;
  height: 112px;
  flex: none;
  border-radius: 10px;
  overflow: hidden;
  background: var(--lk-fill, #f5f7fa);
  border: 1px solid var(--lk-border, #ebeef5);
  cursor: zoom-in;
  position: relative;
}
.cust-cover.is-empty { cursor: pointer; border-style: dashed; }
.cover-img { width: 100%; height: 100%; display: block; }
.cover-ph {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  color: var(--lk-text-3, #6f737a);
  font-size: 12px;
}
.cover-ph .el-icon { font-size: 26px; }

/* 编辑弹窗封面上传 */
.cover-upload { display: flex; align-items: center; gap: 14px; }
.cover-box {
  width: 120px;
  height: 120px;
  border-radius: 10px;
  overflow: hidden;
  border: 1px dashed var(--lk-border, #dcdfe6);
  background: var(--lk-fill, #f5f7fa);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}
.cover-box:hover { border-color: var(--lk-primary, #409eff); }
.cover-box-img { width: 100%; height: 100%; display: block; }
.cover-box-ph {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  color: var(--lk-text-3, #6f737a);
  font-size: 12px;
}
.cover-box-ph .el-icon { font-size: 24px; }
.cover-tip { font-size: 12px; color: var(--lk-text-3, #6f737a); line-height: 1.6; }
</style>
