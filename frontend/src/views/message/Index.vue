<template>
  <div class="msg-page">
    <!-- 页头：统计 + 全局操作 -->
    <div class="page-card">
      <div class="page-left">
        <h2 class="page-title">消息中心</h2>
        <div class="page-sub">
          <span>共 <b>{{ groups.length }}</b> 个项目</span>
          <i class="sep" />
          <span><b>{{ visibleTotal }}</b> 条消息</span>
          <template v-if="unreadTotal">
            <i class="sep" />
            <span class="sub-unread"><b>{{ unreadTotal }}</b> 条未读</span>
            <span v-if="unreadRoutineTotal" class="sub-routine">（另 {{ unreadRoutineTotal }} 条常规）</span>
          </template>
        </div>
      </div>
      <div class="page-right">
        <el-radio-group v-model="isRead" size="small" @change="onFilterChange">
          <el-radio-button :value="null">全部</el-radio-button>
          <el-radio-button :value="0">未读</el-radio-button>
          <el-radio-button :value="1">已读</el-radio-button>
        </el-radio-group>
        <el-tooltip
          placement="bottom"
          content="常规操作（表单填写、节点增删改）默认不再推送消息；打开后可查看历史记录，日常追溯请到「系统管理 → 日志」"
        >
          <span class="routine-switch">
            <el-switch v-model="includeRoutine" size="small" @change="loadData" />
            <span class="rs-text">显示常规操作</span>
          </span>
        </el-tooltip>
        <el-button type="primary" size="small" :icon="Check" :loading="markingAll" @click="onMarkAllRead">
          全部已读
        </el-button>
      </div>
    </div>

    <!-- 项目分组卡片 -->
    <div v-loading="loading" class="group-list">
      <el-empty
        v-if="!loading && groups.length === 0"
        :description="includeRoutine ? '暂无消息' : '暂无关键通知'"
      />

      <section
        v-for="(g, gi) in groups"
        :key="g.projectId"
        class="proj-card"
        :class="{ 'is-unread': g.unread > 0, 'is-open': isOpen(g.projectId) }"
        :style="{ '--i': gi }"
      >
        <!-- 组头 -->
        <header class="pj-head" @click="toggle(g.projectId)">
          <span class="pj-accent" />
          <span class="pj-ico"><el-icon :size="17"><Folder /></el-icon></span>
          <div class="pj-info">
            <div class="pj-title">
              <span class="pj-name">{{ g.projectName }}</span>
              <span v-if="g.unread" class="pj-unread">{{ g.unread }} 条未读</span>
            </div>
            <div class="pj-meta">
              最近 {{ formatTime(g.latestTime) }} · 共 {{ g.total }} 条
              <template v-if="g.filteredTotal !== g.total"> · 当前筛选 {{ g.filteredTotal }} 条</template>
              <template v-if="g.unreadRoutine"> · 常规未读 {{ g.unreadRoutine }} 条</template>
            </div>
          </div>
          <div class="pj-ops" @click.stop>
            <el-button link size="small" :disabled="!g.unread" @click="markGroupRead(g)">本项目全部已读</el-button>
            <el-button link size="small" @click="goProject(g)">进入项目</el-button>
            <el-icon class="pj-arrow" :class="{ open: isOpen(g.projectId) }"><ArrowDown /></el-icon>
          </div>
        </header>

        <!-- 组体：类型 chips + 消息条目 -->
        <el-collapse-transition>
          <div v-show="isOpen(g.projectId)" class="pj-body">
            <div class="chips">
              <button
                v-for="c in g.chips"
                :key="c.key"
                type="button"
                class="chip"
                :class="{ active: activeChip(g.projectId) === c.key }"
                @click="setChip(g.projectId, c.key)"
              >
                {{ c.label }}<span class="chip-n">{{ c.count }}</span>
              </button>
            </div>

            <p v-if="g.items.length === 0" class="pj-empty">该分类下暂无消息</p>

            <div
              v-for="m in g.items"
              :key="m.id"
              class="mi"
              :class="{ unread: m.isRead === 0 }"
              @click="openMessage(m)"
            >
              <span class="mi-dot" />
              <el-icon class="mi-ico"><component :is="typeIcon(m.msgType)" /></el-icon>
              <div class="mi-main">
                <div class="mi-text">
                  <b v-if="splitMessage(m).actor" class="mi-actor">{{ splitMessage(m).actor }}</b>
                  <span>{{ splitMessage(m).text }}</span>
                </div>
                <div class="mi-sub">
                  <span class="mi-type">{{ typeLabel(m.msgType) }}</span>
                  <span class="mi-time">{{ relativeTime(m.createTime) }}</span>
                </div>
              </div>
              <el-icon class="mi-go"><ArrowRight /></el-icon>
            </div>

            <div v-if="g.filteredTotal > g.items.length" class="pj-more">
              <el-button link type="primary" size="small" @click="showMore(g.projectId)">
                展开剩余 {{ g.filteredTotal - g.items.length }} 条
              </el-button>
            </div>
          </div>
        </el-collapse-transition>
      </section>
    </div>

    <p v-if="truncated" class="trunc-hint">
      仅展示最近 {{ FETCH_CAP }} 条，更早的记录请到「系统管理 → 日志」查询
    </p>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowDown, ArrowRight, Check, Folder } from '@element-plus/icons-vue'
import { markRead, markReadAll, myMessages } from '@/api/message'
import { useMessageStore } from '@/stores/message'
import {
  CHIP_DEFS,
  chipOf,
  formatTime,
  isRoutine,
  projectNameOf,
  relativeTime,
  splitMessage,
  typeIcon,
  typeLabel
} from '@/utils/message'

const router = useRouter()
const messageStore = useMessageStore()

const PAGE_SIZE = 200          // 后端 PageQuery 上限
const FETCH_CAP = 1000         // 最多回捞 1000 条（5 页），避免异常数据把页面拖死
const GROUP_LIMIT = 5          // 每个项目默认展示条数，其余折叠

const loading = ref(false)
const markingAll = ref(false)
const rawMessages = ref([])
const truncated = ref(false)
const isRead = ref(null)
const includeRoutine = ref(false)

const openMap = reactive({})   // projectId -> 是否展开
const chipMap = reactive({})   // projectId -> 当前 chip
const limitMap = reactive({})  // projectId -> 已展示条数

const isOpen = (pid) => openMap[pid] === true
const activeChip = (pid) => chipMap[pid] || 'all'

function toggle(pid) {
  openMap[pid] = !isOpen(pid)
}
function setChip(pid, key) {
  chipMap[pid] = key
  limitMap[pid] = GROUP_LIMIT
}
function showMore(pid) {
  limitMap[pid] = (limitMap[pid] || GROUP_LIMIT) + 20
}

async function loadData() {
  loading.value = true
  try {
    let items = []
    let total = 0
    let page = 1
    while (page <= Math.ceil(FETCH_CAP / PAGE_SIZE)) {
      const params = { pageNum: page, pageSize: PAGE_SIZE }
      if (includeRoutine.value) params.includeRoutine = true
      const data = await myMessages(params)
      total = data.total || 0
      items = items.concat(data.items || [])
      if (!data.items?.length || items.length >= total) break
      page += 1
    }
    rawMessages.value = items
    truncated.value = total > items.length
    // 默认展开「有未读」的项目，其余收起
    for (const m of items) {
      if (m.projectId != null && openMap[m.projectId] === undefined) {
        openMap[m.projectId] = m.isRead === 0
      }
    }
  } finally {
    loading.value = false
  }
}

const groups = computed(() => {
  const byProject = new Map()
  for (const m of rawMessages.value) {
    const pid = m.projectId ?? 0
    if (!byProject.has(pid)) byProject.set(pid, [])
    byProject.get(pid).push(m)
  }

  const list = []
  for (const [pid, msgs] of byProject) {
    const sorted = [...msgs].sort((a, b) => String(b.createTime || '').localeCompare(String(a.createTime || '')))
    // 未读数只算「关键通知」—— 与铃铛红点口径一致；常规未读单独统计、单独展示，
    // 避免打开「显示常规操作」后出现「页头 81 条未读、铃铛 11」的割裂感。
    // 也不受「已读/未读」筛选影响，否则切到「已读」时徽标会全空。
    const unread = msgs.filter((m) => m.isRead === 0 && !isRoutine(m.msgType)).length
    const unreadRoutine = msgs.filter((m) => m.isRead === 0 && isRoutine(m.msgType)).length
    // 当前已读/未读筛选后的消息
    const filtered = isRead.value === null ? sorted : sorted.filter((m) => m.isRead === isRead.value)

    // chips 按当前可见消息动态生成（计数为 0 的不显示）
    const counts = {}
    for (const m of filtered) {
      const k = chipOf(m.msgType)
      counts[k] = (counts[k] || 0) + 1
    }
    const chips = CHIP_DEFS
      .filter((c) => c.key === 'all' || counts[c.key])
      .map((c) => ({ ...c, count: c.key === 'all' ? filtered.length : counts[c.key] }))

    const chip = activeChip(pid)
    const matched = chip === 'all' ? filtered : filtered.filter((m) => chipOf(m.msgType) === chip)

    list.push({
      projectId: pid,
      projectName: projectNameOf(sorted[0]?.msgContent) || (pid ? `项目 #${pid}` : '未关联项目'),
      total: msgs.length,
      unread,
      unreadRoutine,
      latestTime: sorted[0]?.createTime,
      chips,
      filteredTotal: matched.length,
      items: matched.slice(0, limitMap[pid] || GROUP_LIMIT)
    })
  }

  // 排序：有未读的项目置顶，其次按最近活跃时间倒序
  list.sort((a, b) => {
    const u = Number(b.unread > 0) - Number(a.unread > 0)
    if (u !== 0) return u
    return String(b.latestTime || '').localeCompare(String(a.latestTime || ''))
  })
  return list
})

const visibleTotal = computed(() => groups.value.reduce((s, g) => s + g.filteredTotal, 0))
const unreadTotal = computed(() => groups.value.reduce((s, g) => s + g.unread, 0))
const unreadRoutineTotal = computed(() => groups.value.reduce((s, g) => s + g.unreadRoutine, 0))

function onFilterChange() {
  // 切换已读/未读后重置各项目的展开与分页，避免状态错位
  for (const pid of Object.keys(openMap)) {
    openMap[pid] = false
    limitMap[pid] = GROUP_LIMIT
  }
  for (const g of groups.value) {
    if (g.unread) openMap[g.projectId] = true
  }
}

async function openMessage(m) {
  if (m.isRead === 0) {
    await markRead({ messageId: m.id }).catch(() => {})
    m.isRead = 1
    messageStore.fetchUnread()
  }
  if (m.projectId) router.push(`/projects/${m.projectId}`)
}

function goProject(g) {
  if (g.projectId) router.push(`/projects/${g.projectId}`)
}

async function markGroupRead(g) {
  const data = await markReadAll({ projectId: g.projectId, includeRoutine: includeRoutine.value })
  ElMessage.success(`已将该项目的 ${data.count} 条标记为已读`)
  messageStore.fetchUnread()
  loadData()
}

async function onMarkAllRead() {
  markingAll.value = true
  try {
    const data = await markReadAll({ includeRoutine: includeRoutine.value })
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
.msg-page { display: flex; flex-direction: column; gap: 14px; }

/* ---------- 页头 ---------- */
.page-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  padding: 16px 20px;
  background: linear-gradient(180deg, #fff 0%, #fcfcfb 100%);
  border: 1px solid var(--lk-border-lighter, #ebeef5);
  border-radius: var(--lk-radius-lg, 12px);
  box-shadow: var(--lk-shadow-sm);
}
.page-title { font-size: 18px; font-weight: 700; letter-spacing: 0.2px; margin: 0; color: var(--lk-text-1, #303133); }
.page-sub { display: flex; align-items: center; gap: 8px; margin-top: 6px; font-size: var(--lk-font-xs, 12px); color: var(--lk-text-3, #6f737a); }
.page-sub b { color: var(--lk-text-1, #303133); font-weight: 700; }
.page-sub .sub-unread b { color: var(--lk-accent, #e2231a); }
.sub-routine { color: var(--lk-text-4, #9aa0a6); }
.sep { width: 3px; height: 3px; border-radius: 50%; background: var(--lk-text-4, #9aa0a6); }
.page-right { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.routine-switch { display: inline-flex; align-items: center; gap: 6px; cursor: pointer; }
.rs-text { font-size: var(--lk-font-xs, 12px); color: var(--lk-text-3, #6f737a); }

/* ---------- 项目分组卡片 ---------- */
.group-list { display: flex; flex-direction: column; gap: 12px; }
.proj-card {
  position: relative;
  background: var(--lk-bg-card, #fff);
  border: 1px solid var(--lk-border-lighter, #ebeef5);
  border-radius: var(--lk-radius-lg, 12px);
  box-shadow: var(--lk-shadow-sm);
  overflow: hidden;
  transition: box-shadow var(--lk-transition-base, 0.25s) var(--lk-ease, ease),
              transform var(--lk-transition-base, 0.25s) var(--lk-ease, ease),
              border-color var(--lk-transition-base, 0.25s) var(--lk-ease, ease);
  animation: card-in 0.32s var(--lk-ease, ease) both;
  animation-delay: calc(var(--i, 0) * 40ms);
}
.proj-card:hover { box-shadow: var(--lk-shadow-md); transform: translateY(-1px); border-color: #e0e0dd; }
.proj-card.is-open { box-shadow: var(--lk-shadow-md); }
.proj-card.is-unread { border-color: #f2d7d4; }

@keyframes card-in {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: none; }
}

/* 组头 */
.pj-head {
  position: relative;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 18px 14px 20px;
  cursor: pointer;
  user-select: none;
}
.pj-accent {
  position: absolute;
  left: 0; top: 0; bottom: 0;
  width: 3px;
  background: var(--lk-border, #dcdfe6);
  transition: background var(--lk-transition-base, 0.25s) var(--lk-ease, ease);
}
.proj-card.is-unread .pj-accent { background: var(--lk-accent, #e2231a); }
.proj-card.is-open .pj-accent { background: var(--lk-primary, #161616); }
.proj-card.is-open.is-unread .pj-accent { background: var(--lk-accent, #e2231a); }

.pj-ico {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px; height: 36px;
  border-radius: 10px;
  color: #fff;
  background: linear-gradient(135deg, #2b2b2b 0%, #161616 100%);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.16);
  flex: none;
}
.pj-info { flex: 1; min-width: 0; }
.pj-title { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.pj-name { font-size: 15px; font-weight: 700; color: var(--lk-text-1, #303133); word-break: break-all; }
.pj-unread {
  font-size: 11px;
  line-height: 1;
  padding: 4px 8px;
  border-radius: var(--lk-radius-round, 999px);
  color: #fff;
  background: var(--lk-accent, #e2231a);
  box-shadow: 0 2px 6px var(--lk-accent-glow, rgba(226, 35, 26, 0.4));
  animation: pulse 2.4s ease-in-out infinite;
}
@keyframes pulse {
  0%, 100% { box-shadow: 0 2px 6px rgba(226, 35, 26, 0.35); }
  50% { box-shadow: 0 2px 12px rgba(226, 35, 26, 0.6); }
}
.pj-meta { margin-top: 4px; font-size: var(--lk-font-xs, 12px); color: var(--lk-text-3, #6f737a); }
.pj-ops { display: flex; align-items: center; gap: 4px; flex: none; }
.pj-arrow {
  margin-left: 6px;
  color: var(--lk-text-3, #6f737a);
  transition: transform var(--lk-transition-base, 0.25s) var(--lk-ease, ease);
}
.pj-arrow.open { transform: rotate(180deg); }

/* 组体 */
.pj-body { padding: 0 18px 14px 20px; }

/* 类型 chips */
.chips { display: flex; flex-wrap: wrap; gap: 8px; padding: 10px 0 12px; border-top: 1px dashed var(--lk-border-lighter, #ebeef5); }
.chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 26px;
  padding: 0 12px;
  font-size: var(--lk-font-xs, 12px);
  font-family: inherit;
  color: var(--lk-text-2, #606266);
  background: #fff;
  border: 1px solid var(--lk-border-light, #e4e7ed);
  border-radius: var(--lk-radius-round, 999px);
  cursor: pointer;
  transition: all var(--lk-transition-fast, 0.15s) var(--lk-ease, ease);
}
.chip:hover { border-color: var(--lk-primary-lighter, #8f8f8f); color: var(--lk-text-1, #303133); }
.chip.active {
  color: #fff;
  background: var(--lk-primary, #161616);
  border-color: var(--lk-primary, #161616);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.16);
}
.chip-n { font-size: 11px; opacity: 0.72; font-variant-numeric: tabular-nums; }

/* 消息条目 */
.mi {
  position: relative;
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 11px 10px 11px 12px;
  border-radius: var(--lk-radius-md, 8px);
  cursor: pointer;
  transition: background var(--lk-transition-fast, 0.15s) var(--lk-ease, ease),
              transform var(--lk-transition-fast, 0.15s) var(--lk-ease, ease);
}
.mi + .mi { margin-top: 2px; }
.mi:hover { background: var(--lk-bg-hover, #f5f7fa); transform: translateX(2px); }
.mi.unread { background: #fffaf9; }
.mi.unread:hover { background: #fff4f3; }
.mi-dot {
  width: 6px; height: 6px; border-radius: 50%;
  margin-top: 7px; flex: none;
  background: transparent;
}
.mi.unread .mi-dot { background: var(--lk-accent, #e2231a); }
.mi-ico { margin-top: 3px; font-size: 15px; color: var(--lk-text-4, #9aa0a6); flex: none; }
.mi.unread .mi-ico { color: var(--lk-accent, #e2231a); }
.mi-main { flex: 1; min-width: 0; }
.mi-text { font-size: var(--lk-font-md, 14px); line-height: 1.55; color: var(--lk-text-2, #606266); word-break: break-all; }
.mi-actor { color: var(--lk-text-1, #303133); font-weight: 700; margin-right: 2px; }
.mi.unread .mi-text { color: var(--lk-text-1, #303133); }
.mi-sub { display: flex; align-items: center; gap: 10px; margin-top: 5px; font-size: var(--lk-font-xs, 12px); color: var(--lk-text-4, #9aa0a6); }
.mi-type {
  padding: 1px 7px;
  border: 1px solid var(--lk-border-light, #e4e7ed);
  border-radius: var(--lk-radius-round, 999px);
  color: var(--lk-text-3, #6f737a);
  background: #fff;
}
.mi-go {
  margin-top: 4px;
  color: transparent;
  flex: none;
  transition: color var(--lk-transition-fast, 0.15s) var(--lk-ease, ease),
              transform var(--lk-transition-fast, 0.15s) var(--lk-ease, ease);
}
.mi:hover .mi-go { color: var(--lk-text-3, #6f737a); transform: translateX(2px); }

.pj-empty { padding: 18px 0; text-align: center; font-size: var(--lk-font-sm, 13px); color: var(--lk-text-4, #9aa0a6); }
.pj-more { padding-top: 8px; text-align: center; }
.trunc-hint { margin: 0; text-align: center; font-size: var(--lk-font-xs, 12px); color: var(--lk-text-4, #9aa0a6); }

@media (max-width: 768px) {
  .page-card { align-items: flex-start; }
  .pj-head { padding: 12px 12px 12px 16px; }
  .pj-body { padding: 0 12px 12px 16px; }
  .pj-ico { display: none; }
  .pj-ops :deep(.el-button) { display: none; }
}
</style>
