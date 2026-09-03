<template>
  <el-card>
    <div class="header">
      <span class="title">用户管理</span>
      <div class="header-actions">
        <!-- 部门筛选：全部 / 内置部门 / 客户部门 -->
        <el-select v-model="filterType" class="dept-filter" @change="onFilterChange">
          <el-option label="全部部门" value="all" />
          <el-option-group label="内置部门">
            <el-option v-for="d in internalDepts" :key="`d${d.id}`" :label="d.deptName" :value="`d${d.id}`" />
          </el-option-group>
          <el-option-group label="客户单位（公司）">
            <el-option v-for="c in categories" :key="`c${c.id}`" :label="c.categoryName" :value="`c${c.id}`" />
          </el-option-group>
        </el-select>
        <el-button :icon="OfficeBuilding" @click="deptDialogVisible = true">部门管理</el-button>
        <el-button type="primary" :icon="Plus" @click="openCreate">新建用户</el-button>
      </div>
    </div>

    <!-- 卡片网格（一行 3 个，间隔 16px） -->
    <div v-if="loading" class="card-grid">
      <div v-for="i in 6" :key="i" class="user-card skeleton-card">
        <el-skeleton :rows="3" animated />
      </div>
    </div>

    <div v-else-if="filteredUsers.length" class="card-grid">
      <div v-for="row in filteredUsers" :key="row.id" class="user-card">
        <div class="user-head">
          <div class="user-avatar" :class="`role-${roleKey(row.role)}`">{{ (row.realName || row.username || '?').slice(0, 1) }}</div>
          <div class="user-title">
            <div class="user-name-row">
              <span class="user-name" :title="row.realName">{{ row.realName }}</span>
              <el-tag :type="roleTagType(row.role)" size="small" effect="dark">{{ row.role }}</el-tag>
            </div>
            <span class="user-account">@{{ row.username }}</span>
          </div>
        </div>

        <div class="user-meta">
          <div class="meta-row">
            <el-icon class="meta-icon"><OfficeBuilding /></el-icon>
            <span class="meta-label">部门</span>
            <span class="meta-value">
              <template v-if="row.role === '客户'">{{ row.categoryName || '—' }}（公司）</template>
              <template v-else>{{ row.deptName || '未分配' }}</template>
            </span>
          </div>
          <div class="meta-row">
            <el-icon class="meta-icon"><Key /></el-icon>
            <span class="meta-label">密码</span>
            <span class="meta-value mono">{{ row.password || '—' }}</span>
          </div>
          <div class="meta-row">
            <el-icon class="meta-icon"><CircleCheck /></el-icon>
            <span class="meta-label">状态</span>
            <el-switch
              :model-value="row.isEnable === 1"
              :disabled="row.id === userStore.userInfo?.id"
              size="small"
              @change="(v) => onSetEnable(row, v)"
            />
            <span class="meta-value">{{ row.isEnable === 1 ? '启用' : '停用' }}</span>
            <el-tag v-if="row.isLocked" type="warning" size="small" effect="plain" class="lock-tag">
              <el-icon class="lock-icon"><Lock /></el-icon>已锁定
            </el-tag>
          </div>
        </div>

        <div class="user-foot">
          <el-button size="small" :icon="Edit" @click="openEdit(row)">编辑</el-button>
          <el-button size="small" type="primary" :icon="RefreshLeft" @click="openReset(row)">重置密码</el-button>
          <el-button
            v-if="row.isLocked && row.id !== userStore.userInfo?.id"
            size="small"
            type="warning"
            :icon="Unlock"
            :loading="unlockingId === row.id"
            @click="onUnlock(row)"
          >解锁</el-button>
          <span class="foot-spacer" />
          <el-button
            v-if="row.username !== 'admin' && row.id !== userStore.userInfo?.id"
            size="small"
            type="danger"
            :icon="Delete"
            @click="onDelete(row)"
          >删除</el-button>
        </div>
      </div>
    </div>

    <el-empty v-else :description="filterType === 'all' ? '暂无用户' : '该部门下暂无用户'" />

    <!-- 新建用户弹窗 -->
    <el-dialog v-model="createVisible" title="新建用户" width="min(480px, 92vw)">
      <el-form :model="createForm" label-width="90px">
        <el-form-item label="账号类型" required>
          <el-radio-group v-model="createForm.userType">
            <el-radio-button value="employee">内部员工</el-radio-button>
            <el-radio-button value="customer">客户账号</el-radio-button>
          </el-radio-group>
          <div v-if="createForm.userType === 'customer'" class="type-tip">
            客户账号只读：登录后可查看所属客户单位名下全部项目的节点进度，不能做任何修改
          </div>
        </el-form-item>
        <template v-if="createForm.userType === 'employee'">
          <el-form-item label="所属部门" required>
            <el-select v-model="createForm.deptId" placeholder="选择部门（仅组织归属）" style="width: 100%">
              <el-option v-for="d in internalDepts" :key="d.id" :label="d.deptName" :value="d.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="分配角色" required>
            <el-select v-model="createForm.role" placeholder="选择角色（决定权限）" style="width: 100%">
              <el-option v-for="r in roleChoices" :key="r" :label="r" :value="r" />
            </el-select>
            <div class="type-tip">角色决定账号权限；部门仅用于组织分组，与权限无关</div>
          </el-form-item>
        </template>
        <el-form-item v-else label="绑定客户单位" required>
          <el-select v-model="createForm.categoryId" filterable placeholder="选择客户单位（公司）" style="width: 100%">
            <el-option v-for="c in categories" :key="c.id" :label="c.categoryName" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="登录账号" required>
          <el-input v-model="createForm.username" maxlength="64" placeholder="如 qingdao_zhang" />
        </el-form-item>
        <el-form-item label="初始密码" required>
          <el-input v-model="createForm.password" maxlength="128" show-password />
        </el-form-item>
        <el-form-item label="真实姓名" required>
          <el-input v-model="createForm.realName" maxlength="64" placeholder="如 张工（青岛地铁对接人）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="submitCreate">创建</el-button>
      </template>
    </el-dialog>

    <!-- 编辑用户弹窗（部门 + 角色，权限与部门无关） -->
    <el-dialog v-model="editVisible" :title="`编辑用户 - ${editForm.realName || ''}`" width="min(460px, 92vw)">
      <el-form :model="editForm" label-width="90px">
        <template v-if="isEditCustomer">
          <div class="edit-customer-tip">
            <el-icon><InfoFilled /></el-icon>
            客户账号不参与部门与角色分配，仅可修改姓名；如需调整请删除后重建。
          </div>
          <el-form-item label="绑定客户单位"><el-input :model-value="editForm.categoryName" disabled /></el-form-item>
          <el-form-item label="分配角色"><el-input :model-value="editForm.role" disabled /></el-form-item>
        </template>
        <template v-else>
          <el-form-item label="所属部门" required>
            <el-select v-model="editForm.deptId" placeholder="选择部门" style="width: 100%">
              <el-option v-for="d in internalDepts" :key="d.id" :label="d.deptName" :value="d.id" />
            </el-select>
            <div class="type-tip">更换部门不会改变该账号的权限</div>
          </el-form-item>
          <el-form-item label="分配角色" required>
            <el-select v-model="editForm.role" placeholder="选择角色（决定权限）" style="width: 100%">
              <el-option v-for="r in roleChoices" :key="r" :label="r" :value="r" />
            </el-select>
          </el-form-item>
        </template>
        <el-form-item label="真实姓名" required>
          <el-input v-model="editForm.realName" maxlength="64" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingEdit" @click="submitEdit">保存</el-button>
      </template>
    </el-dialog>

    <!-- 部门管理弹窗：仅人员分组，不携带权限 -->
    <el-dialog v-model="deptDialogVisible" title="部门管理" width="min(480px, 92vw)">
      <div class="dept-tip">部门用于人员组织分组，不控制权限；权限通过给账号分配角色实现。客户账号无需创建部门，新建用户时直接选择客户类型。</div>
      <div class="dept-add">
        <el-input v-model="newDeptName" placeholder="新部门名称，如：运营部" size="small" maxlength="64" style="flex: 1" @keyup.enter="onAddDept" />
        <el-button type="primary" size="small" :loading="addingDept" @click="onAddDept">添加</el-button>
      </div>
      <el-table :data="internalDepts" size="small">
        <el-table-column label="部门名称" min-width="140">
          <template #default="{ row }">
            <el-icon class="dept-icon"><OfficeBuilding /></el-icon>
            <span class="dept-name">{{ row.deptName }}</span>
          </template>
        </el-table-column>
        <el-table-column label="人数" width="80" align="center">
          <template #default="{ row }">
            <span class="dept-count">{{ row.userCount }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="140" align="center">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openEditDept(row)">重命名</el-button>
            <el-button link type="danger" size="small" @click="onDeleteDept(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-dialog v-model="editDeptVisible" title="重命名部门" width="min(340px, 92vw)" append-to-body>
        <el-input v-model="editDeptForm.deptName" maxlength="64" placeholder="部门名称" />
        <template #footer>
          <el-button @click="editDeptVisible = false">取消</el-button>
          <el-button type="primary" :loading="savingDept" @click="onSaveDept">保存</el-button>
        </template>
      </el-dialog>
    </el-dialog>

    <!-- 重置密码弹窗 -->
    <el-dialog v-model="resetVisible" :title="`重置密码 - ${resetTarget?.realName}`" width="min(380px, 92vw)">
      <el-input v-model="newPassword" placeholder="新密码" maxlength="128" show-password type="password" />
      <template #footer>
        <el-button @click="resetVisible = false">取消</el-button>
        <el-button type="primary" :loading="resetting" @click="submitReset">确定</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { CircleCheck, Delete, Edit, InfoFilled, Key, Lock, OfficeBuilding, Plus, RefreshLeft, Unlock } from '@element-plus/icons-vue'
import { createUser, deleteUser, listUsers, resetPwd, setEnable, unlockUser, updateUser } from '@/api/sysUser'
import { addDept, deleteDept, listDepts, updateDept } from '@/api/sysDept'
import { listCategories } from '@/api/customer'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()

// 可分配角色（V1.4.2 简化为两类）；客户角色由客户账号自动获得
const roleChoices = ['普通', '管理员']

const loading = ref(false)
const tableData = ref([])
const internalDepts = ref([])
const categories = ref([])

const ROLE_KEY_MAP = { 管理员: 'admin', 普通: 'staff' }
function roleKey(role) { return ROLE_KEY_MAP[role] || 'customer' }
const ROLE_TAG_MAP = { 管理员: 'danger', 普通: 'primary' }
function roleTagType(role) { return ROLE_TAG_MAP[role] || 'primary' }

// ---- 部门/客户筛选 ----
const filterType = ref('all')
const filteredUsers = computed(() => {
  if (filterType.value === 'all') return tableData.value
  const [kind, id] = [filterType.value[0], Number(filterType.value.slice(1))]
  if (kind === 'd') return tableData.value.filter((u) => u.deptId === id)
  return tableData.value.filter((u) => u.categoryId === id)
})
function onFilterChange() { /* computed 已处理 */ }

async function loadData() {
  loading.value = true
  try {
    const [users, depts, cats] = await Promise.all([
      listUsers(),
      listDepts().catch(() => []),
      listCategories().catch(() => [])
    ])
    tableData.value = users
    internalDepts.value = (depts || []).filter((d) => d.deptType === 'internal')
    categories.value = cats || []
  } finally {
    loading.value = false
  }
}

// ---- 新建用户 ----
const createVisible = ref(false)
const creating = ref(false)
const createForm = reactive({
  userType: 'employee', deptId: null, role: null, categoryId: null,
  username: '', password: '', realName: ''
})

function openCreate() {
  Object.assign(createForm, {
    userType: 'employee', deptId: null, role: null, categoryId: null,
    username: '', password: '', realName: ''
  })
  createVisible.value = true
}

async function submitCreate() {
  if (!createForm.username || !createForm.password || !createForm.realName) {
    ElMessage.warning('请填写账号、密码和真实姓名')
    return
  }
  if (createForm.userType === 'employee') {
    if (!createForm.deptId) { ElMessage.warning('请选择所属部门'); return }
    if (!createForm.role) { ElMessage.warning('请为账号分配角色'); return }
  } else if (!createForm.categoryId) {
    ElMessage.warning('请选择绑定的客户单位')
    return
  }
  creating.value = true
  try {
    const payload = {
      username: createForm.username,
      password: createForm.password,
      realName: createForm.realName
    }
    if (createForm.userType === 'employee') {
      payload.deptId = createForm.deptId
      payload.role = createForm.role
    } else {
      payload.categoryId = createForm.categoryId
    }
    await createUser(payload)
    ElMessage.success('已创建')
    createVisible.value = false
    loadData()
  } finally {
    creating.value = false
  }
}

// ---- 编辑用户 ----
const editVisible = ref(false)
const savingEdit = ref(false)
const editForm = reactive({ id: null, deptId: null, role: null, realName: '', categoryName: '', categoryId: null })
const isEditCustomer = computed(() => editForm.categoryId != null || editForm.role === '客户')

function openEdit(row) {
  Object.assign(editForm, {
    id: row.id,
    deptId: row.deptId || null,
    role: row.role || null,
    realName: row.realName || '',
    categoryName: row.categoryName || '',
    categoryId: row.categoryId || null
  })
  editVisible.value = true
}

async function submitEdit() {
  if (!editForm.realName) { ElMessage.warning('请输入真实姓名'); return }
  if (!isEditCustomer.value) {
    if (!editForm.deptId) { ElMessage.warning('请选择所属部门'); return }
    if (!editForm.role) { ElMessage.warning('请为账号分配角色'); return }
  }
  savingEdit.value = true
  try {
    const payload = { id: editForm.id, realName: editForm.realName }
    if (!isEditCustomer.value) {
      payload.deptId = editForm.deptId
      payload.role = editForm.role
    }
    await updateUser(payload)
    ElMessage.success('已保存')
    editVisible.value = false
    loadData()
  } finally {
    savingEdit.value = false
  }
}

// ---- 部门管理（仅分组，无权限）----
const deptDialogVisible = ref(false)
const newDeptName = ref('')
const addingDept = ref(false)

async function onAddDept() {
  const name = newDeptName.value.trim()
  if (!name) { ElMessage.warning('请输入部门名称'); return }
  addingDept.value = true
  try {
    await addDept({ deptName: name, deptType: 'internal' })
    newDeptName.value = ''
    ElMessage.success('已添加部门')
    loadData()
  } finally {
    addingDept.value = false
  }
}

const editDeptVisible = ref(false)
const savingDept = ref(false)
const editDeptForm = reactive({ id: null, deptName: '' })

function openEditDept(row) {
  Object.assign(editDeptForm, { id: row.id, deptName: row.deptName })
  editDeptVisible.value = true
}

async function onSaveDept() {
  if (!editDeptForm.deptName.trim()) { ElMessage.warning('请输入部门名称'); return }
  savingDept.value = true
  try {
    await updateDept({ id: editDeptForm.id, deptName: editDeptForm.deptName.trim() })
    ElMessage.success('已保存')
    editDeptVisible.value = false
    loadData()
  } finally {
    savingDept.value = false
  }
}

async function onDeleteDept(row) {
  if (row.userCount > 0) {
    ElMessage.warning(`部门「${row.deptName}」下还有 ${row.userCount} 个用户，请先调整这些用户的部门`)
    return
  }
  await ElMessageBox.confirm(`确定删除部门「${row.deptName}」吗？（仅解除组织分组，不影响用户权限）`, '删除确认', { type: 'error', confirmButtonText: '确认删除' })
  await deleteDept({ id: row.id })
  ElMessage.success('已删除')
  loadData()
}

// ---- 启用/停用 ----
async function onSetEnable(row, val) {
  await setEnable({ userId: row.id, isEnable: val ? 1 : 0 })
  row.isEnable = val ? 1 : 0
  ElMessage.success(val ? '已启用' : '已停用')
}

// ---- 解锁账号（V1.4.6 登录防暴力破解）----
const unlockingId = ref(null)

async function onUnlock(row) {
  try {
    await ElMessageBox.confirm(
      `确定解锁账号「${row.realName}（${row.username}）」吗？将清除其登录失败计数与锁定状态。`,
      '解锁确认',
      { type: 'warning', confirmButtonText: '确认解锁' }
    )
  } catch {
    return // 用户取消
  }
  unlockingId.value = row.id
  try {
    await unlockUser({ userId: row.id })
    row.isLocked = false
    ElMessage.success('已解锁，账号可正常登录')
    loadData()
  } catch (e) {
    ElMessage.error(e?.message || '解锁失败')
  } finally {
    unlockingId.value = null
  }
}

// ---- 重置密码 ----
const resetVisible = ref(false)
const resetting = ref(false)
const resetTarget = ref(null)
const newPassword = ref('')

function openReset(row) {
  resetTarget.value = row
  newPassword.value = ''
  resetVisible.value = true
}

async function submitReset() {
  if (!newPassword.value) {
    ElMessage.warning('请输入新密码')
    return
  }
  resetting.value = true
  try {
    await resetPwd({ userId: resetTarget.value.id, newPassword: newPassword.value })
    ElMessage.success('已重置')
    resetVisible.value = false
    loadData()
  } finally {
    resetting.value = false
  }
}

onMounted(loadData)

// ---- 删除用户（V1.3）----
async function onDelete(row) {
  await ElMessageBox.confirm(
    `确定删除用户「${row.realName}（${row.username}）」吗？历史项目与日志记录将保留，删除后不可恢复。`,
    '删除确认',
    { type: 'error', confirmButtonText: '确认删除' }
  )
  await deleteUser({ userId: row.id })
  ElMessage.success('已删除')
  loadData()
}
</script>

<style scoped>
.header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; flex-wrap: wrap; gap: 8px; }
.header-actions { display: flex; gap: 8px; flex-wrap: wrap; }
.dept-filter { width: 200px; }
.title { font-size: 16px; font-weight: bold; }

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

.user-card {
  border: 1px solid var(--lk-border, #ebeef5);
  border-radius: 12px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 210px;
  transition: box-shadow 0.2s, border-color 0.2s, transform 0.2s;
}
.user-card:hover {
  border-color: var(--lk-primary, #409eff);
  box-shadow: var(--lk-shadow-md, 0 6px 18px rgba(64, 158, 255, 0.14));
  transform: translateY(-2px);
}
.skeleton-card { padding: 20px 16px; min-height: 0; }

.user-head { display: flex; align-items: center; gap: 12px; }
.user-avatar {
  width: 46px;
  height: 46px;
  flex: none;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  font-weight: 700;
  color: #fff;
  background: linear-gradient(135deg, var(--lk-primary, #409eff), #66b1ff);
}
.user-avatar.role-admin { background: linear-gradient(135deg, #f56c6c, #f78989); }
.user-avatar.role-staff { background: linear-gradient(135deg, var(--lk-primary, #409eff), #66b1ff); }
.user-avatar.role-customer { background: linear-gradient(135deg, #7d5fff, #a08cff); }

.user-title { display: flex; flex-direction: column; gap: 3px; min-width: 0; flex: 1; }
.user-name-row { display: flex; align-items: center; gap: 8px; min-width: 0; }
.user-name {
  font-size: 16px;
  font-weight: 700;
  color: var(--lk-text-1, #303133);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.user-account { font-size: 12px; color: var(--lk-text-3, #6f737a); }
.lock-tag { margin-left: 8px; display: inline-flex; align-items: center; gap: 2px; }
.lock-tag .lock-icon { font-size: 12px; }

.user-meta { display: flex; flex-direction: column; gap: 8px; flex: 1; }
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
.meta-value.mono { font-family: Consolas, 'Courier New', monospace; letter-spacing: 0.3px; }

.user-foot {
  display: flex;
  align-items: center;
  gap: 6px;
  border-top: 1px solid var(--lk-border, #ebeef5);
  padding-top: 10px;
  margin-top: auto;
  flex-wrap: wrap;
}
.foot-spacer { flex: 1; }

/* 部门管理弹窗 */
.dept-tip { font-size: 12px; color: var(--lk-text-3, #6f737a); line-height: 1.6; margin-bottom: 12px; }
.dept-add { display: flex; gap: 8px; margin-bottom: 12px; }
.dept-icon { color: var(--lk-primary, #409eff); vertical-align: -2px; margin-right: 6px; }
.dept-name { font-weight: 500; }
.dept-count { font-weight: 600; color: var(--lk-text-1, #303133); }
.type-tip { font-size: 12px; color: var(--lk-text-3, #6f737a); line-height: 1.5; margin-top: 4px; }
.edit-customer-tip {
  display: flex; align-items: center; gap: 6px;
  font-size: 13px; color: var(--lk-warning, #e6a23c);
  background: var(--lk-fill, #f5f7fa);
  border-radius: 8px; padding: 10px 12px; margin-bottom: 12px;
}
</style>
