<template>
  <div class="rt">
    <!-- 首次加载骨架屏（阶段三）：loading 且无数据时以骨架代替转圈 -->
    <el-skeleton v-if="loading && data.length === 0 && !isMobile" animated :rows="7" class="rt-skeleton" />
    <div v-else-if="loading && data.length === 0 && isMobile" class="rt-cards">
      <div v-for="i in 4" :key="i" class="rt-card rt-card-skeleton">
        <el-skeleton animated :rows="3" />
      </div>
    </div>

    <!-- 空状态（支持 #empty 插槽放引导动作，如"新建项目"） -->
    <el-empty v-else-if="data.length === 0" :description="emptyText">
      <slot name="empty" />
    </el-empty>

    <!-- 桌面端（≥768px）：标准表格 -->
    <el-table
      v-else-if="!isMobile"
      :data="data"
      v-loading="loading"
      stripe
      :row-key="rowKey"
      class="rt-table"
    >
      <el-table-column
        v-for="col in columns"
        :key="col.prop"
        :prop="col.prop"
        :label="col.label"
        :min-width="col.minWidth"
        :width="col.width"
        :fixed="col.fixed"
        :align="col.align"
        :show-overflow-tooltip="col.ellipsis"
      >
        <template v-if="hasSlot(col.prop)" #default="{ row }">
          <slot :name="col.prop" :row="row" />
        </template>
      </el-table-column>
    </el-table>

    <!-- 移动端（<768px）：卡片列表 -->
    <div v-else class="rt-cards" v-loading="loading">
      <div v-for="(row, idx) in data" :key="cardKey(row, idx)" class="rt-card">
        <!-- 卡片标题（默认第一列） -->
        <div v-if="titleCol" class="rt-card-title">
          <slot :name="titleCol.prop" :row="row">{{ row[titleCol.prop] }}</slot>
        </div>
        <!-- 其余字段：label + value -->
        <div v-for="col in bodyCols" :key="col.prop" class="rt-field">
          <span class="rt-label">{{ col.label }}</span>
          <span class="rt-value">
            <slot :name="col.prop" :row="row">{{ formatValue(row[col.prop]) }}</slot>
          </span>
        </div>
        <!-- 操作列：独立按钮行 -->
        <div v-if="actionCol && hasSlot(actionCol.prop)" class="rt-actions">
          <slot :name="actionCol.prop" :row="row" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, useSlots } from 'vue'
import { useIsMobile } from '@/composables/useIsMobile'

const props = defineProps({
  // 列配置：[{ prop, label, minWidth?, width?, fixed?, align?, ellipsis? }]
  columns: { type: Array, required: true },
  data: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  // 卡片模式下作为标题的列 prop（默认第一列）
  cardTitleKey: { type: String, default: '' },
  // 操作列 prop，卡片模式下渲染为底部按钮行（桌面模式仍按普通列渲染）
  actionKey: { type: String, default: 'actions' },
  rowKey: { type: String, default: 'id' },
  // 空状态文案（与 #empty 插槽配合：插槽内放引导动作）
  emptyText: { type: String, default: '暂无数据' }
})

const slots = useSlots()
const hasSlot = (name) => !!slots[name]

const isMobile = useIsMobile(768)

const titleCol = computed(() => {
  if (props.cardTitleKey) return props.columns.find((c) => c.prop === props.cardTitleKey)
  return props.columns[0]
})
const actionCol = computed(() => props.columns.find((c) => c.prop === props.actionKey))
const bodyCols = computed(() =>
  props.columns.filter((c) => c.prop !== titleCol.value?.prop && c.prop !== props.actionKey)
)

function formatValue(v) {
  return v === null || v === undefined || v === '' ? '—' : String(v)
}
function cardKey(row, idx) {
  const k = props.rowKey ? row[props.rowKey] : undefined
  return k !== undefined && k !== null ? k : idx
}
</script>

<style scoped>
.rt-cards { min-height: 120px; }
.rt-skeleton { padding: 8px 0; }
.rt-card-skeleton { cursor: default; }
.rt-card {
  background: var(--lk-bg-card, #fff);
  border: 1px solid var(--lk-border-light, #e4e7ed);
  border-radius: var(--lk-radius-md, 10px);
  padding: 12px 14px;
  margin-bottom: 10px;
  box-shadow: var(--lk-shadow-sm, 0 1px 4px rgba(0, 0, 0, 0.04));
}
.rt-card-title {
  font-size: 15px;
  font-weight: bold;
  color: var(--lk-text-1, #1f2937);
  padding-bottom: 8px;
  margin-bottom: 8px;
  border-bottom: 1px dashed var(--lk-border-light, #e4e7ed);
  word-break: break-all;
}
.rt-field {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 5px 0;
  font-size: 13px;
  line-height: 1.5;
}
.rt-label {
  flex-shrink: 0;
  color: var(--lk-text-3, #909399);
}
.rt-value {
  flex: 1;
  min-width: 0;
  text-align: right;
  color: var(--lk-text-1, #303133);
  word-break: break-all;
}
.rt-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 2px 12px;
  padding-top: 8px;
  margin-top: 8px;
  border-top: 1px solid var(--lk-border-light, #e4e7ed);
}
.rt-actions :deep(.el-button) { margin-left: 0; }
</style>
