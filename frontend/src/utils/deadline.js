// 截止倒计时工具：项目卡片色带 + 项目详情页共用
//
// 颜色分档（按剩余天数比例递进）：
//   > 30 天   success  充裕（绿）
//   16 - 30 天 primary  正常（蓝）
//   6 - 15 天  warning  需注意（橙）
//   1 - 5 天   danger   紧急（红，呼吸闪烁）
//   已逾期     danger   逾期（红，呼吸闪烁）
// 已归档或未设置截止时间：返回 null（不显示）
//
// V1.4.19：传入 stageName 后，label 变为「距 {环节名} 剩 N 天」
export function deadlineInfo(expectTime, projectStatus, stageName) {
  if (!expectTime || projectStatus === '已归档') return null
  const end = new Date(typeof expectTime === 'string' ? expectTime.replace(' ', 'T') : expectTime).getTime()
  if (Number.isNaN(end)) return null

  const diffDays = Math.ceil((end - Date.now()) / 86400000)
  const prefix = stageName ? `距${stageName}` : '距截止'

  if (diffDays > 30) {
    return { label: `${prefix}剩 ${diffDays} 天`, type: 'success', level: '充裕', overdue: false }
  }
  if (diffDays > 15) {
    return { label: `${prefix}剩 ${diffDays} 天`, type: 'primary', level: '正常', overdue: false }
  }
  if (diffDays > 5) {
    return { label: `${prefix}剩 ${diffDays} 天`, type: 'warning', level: '需注意', overdue: false }
  }
  if (diffDays > 0) {
    return { label: `${prefix}剩 ${diffDays} 天`, type: 'danger', level: '紧急', overdue: false }
  }

  // 已逾期：不足一天显示「已逾期」，否则「已逾期 X 天」
  const overdueDays = Math.floor((Date.now() - end) / 86400000)
  return {
    label: overdueDays > 0 ? `${stageName ? stageName + ' ' : ''}已逾期 ${overdueDays} 天` : '已逾期',
    type: 'danger',
    level: '已逾期',
    overdue: true
  }
}
