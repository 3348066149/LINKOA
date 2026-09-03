<template>
  <div v-if="evaluation" class="eval-stars" :class="{ 'low-score': lowScore }">
    <div v-for="d in dims" :key="d.key" class="eval-row">
      <span class="eval-label">{{ d.label }}</span>
      <el-rate :model-value="evaluation[d.key] || 0" disabled />
      <span class="eval-num">{{ evaluation[d.key] || 0 }} 分</span>
    </div>
    <div v-if="showRemark && evaluation.customerRemark" class="eval-remark">
      <span class="eval-remark-label">客户备注</span>
      <span class="eval-remark-text">{{ evaluation.customerRemark }}</span>
    </div>
    <div v-if="showTime && evaluation.evaluateTime" class="eval-time">
      评价时间：{{ (evaluation.evaluateTime || '').slice(0, 16) }}
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

// 只读三项星评展示组件：客户卡片 / 内部列表弹窗 / 详情区块复用
const props = defineProps({
  evaluation: { type: Object, default: null },
  showRemark: { type: Boolean, default: true },
  showTime: { type: Boolean, default: true }
})

const dims = [
  { label: '设计满意度', key: 'designScore' },
  { label: '服务响应速度', key: 'serviceScore' },
  { label: '最终产品', key: 'productScore' }
]

// 低分标红：任一单项 <= 2
const lowScore = computed(() => {
  const e = props.evaluation
  if (!e) return false
  return [e.designScore, e.serviceScore, e.productScore].some((s) => s <= 2)
})
</script>

<style scoped>
.eval-stars {
  padding: 10px 12px;
  border-radius: 8px;
  background: var(--lk-fill-1, #f5f7fa);
}
.eval-stars.low-score {
  background: #fef0f0;
  border: 1px solid var(--lk-danger, #f56c6c);
}
.eval-row {
  display: flex;
  align-items: center;
  gap: 8px;
  line-height: 24px;
}
.eval-label {
  width: 96px;
  font-size: 13px;
  color: var(--lk-text-1, #303133);
  flex-shrink: 0;
}
.eval-num {
  font-size: 12px;
  color: var(--lk-text-2, #606266);
}
.low-score .eval-label,
.low-score .eval-num {
  color: var(--lk-danger, #f56c6c);
  font-weight: bold;
}
.low-score :deep(.el-rate__icon.is-active) {
  color: var(--lk-danger, #f56c6c);
}
.eval-remark {
  margin-top: 8px;
  font-size: 13px;
  color: var(--lk-text-2, #606266);
  line-height: 1.6;
}
.eval-remark-label {
  font-weight: bold;
  margin-right: 6px;
  color: var(--lk-text-1, #303133);
}
.eval-remark-text {
  white-space: pre-wrap;
  word-break: break-all;
}
.eval-time {
  margin-top: 6px;
  font-size: 12px;
  color: var(--lk-text-3, #6f737a);
}
</style>
