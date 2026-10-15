// 消息展示工具（V1.4.21）
// 消息中心与顶部铃铛共用：类型元数据、项目名解析、文案精简、相对时间。
// 说明：message.msg_content 由后端 message_service 按固定模板生成，项目名固定出现在
// 第一个「」内（如「王云云 在项目「XX项目」中新增了节点：YY」）。这里把这些模板
// 还原成「操作人 + 动作」两段，既可去掉每个项目分组里重复的项目名，又能做更好的排版；
// 任何一条匹配不上就原样显示，不影响可用性。
import {
  ChatDotRound,
  CircleCheck,
  Delete,
  Document,
  EditPen,
  Plus,
  Star
} from '@element-plus/icons-vue'

/** 消息类型元数据：label 用于展示，icon 用于列表左侧图标，chip 为组内筛选分组，routine 标记常规操作 */
export const TYPE_META = {
  customer_review: { label: '客户审核', icon: CircleCheck, chip: 'review', routine: false },
  evaluation_create: { label: '客户评价', icon: Star, chip: 'evaluation', routine: false },
  comment_create: { label: '新评论', icon: ChatDotRound, chip: 'comment', routine: false },
  node_create: { label: '节点新增', icon: Plus, chip: 'node', routine: true },
  node_update: { label: '节点修改', icon: EditPen, chip: 'node', routine: true },
  node_delete: { label: '节点删除', icon: Delete, chip: 'node', routine: true },
  form_update: { label: '表单填写', icon: Document, chip: 'form', routine: true }
}

/** 组内类型筛选 chips（按此顺序展示，计数为 0 的不显示） */
export const CHIP_DEFS = [
  { key: 'all', label: '全部' },
  { key: 'review', label: '客户审核' },
  { key: 'evaluation', label: '客户评价' },
  { key: 'comment', label: '评论' },
  { key: 'node', label: '节点' },
  { key: 'form', label: '表单' }
]

export function chipOf(msgType) {
  return TYPE_META[msgType]?.chip || 'other'
}

/** 常规操作类型（后端默认不再产生这类消息，历史数据默认隐藏） */
export const ROUTINE_TYPES = ['node_create', 'node_update', 'node_delete', 'form_update']

export function typeLabel(t) {
  return TYPE_META[t]?.label || t
}

export function typeIcon(t) {
  return TYPE_META[t]?.icon || Document
}

export function isRoutine(t) {
  return ROUTINE_TYPES.includes(t)
}

/** 从消息文案里取项目名（模板中第一个「」即项目名）；取不到返回空串 */
export function projectNameOf(content) {
  const m = /「([^」]+)」/.exec(content || '')
  return m ? m[1] : ''
}

// 文案精简规则：去掉「在项目「XX」」这种在分组视图里重复的信息
const CONTENT_RULES = [
  [/^(.*?) 在项目「[^」]+」中新增了节点：(.*)$/, '$1 新增了节点：$2'],
  [/^(.*?) 在项目「[^」]+」中修改了节点：(.*)$/, '$1 修改了节点：$2'],
  [/^(.*?) 在项目「[^」]+」中删除了节点：(.*)$/, '$1 删除了节点：$2'],
  [/^(.*?) 在项目「[^」]+」的「(.+?)」中填写了表单$/, '$1 填写了「$2」的表单'],
  [/^(.*?) 在项目「[^」]+」中发表了评论：(.*)$/, '$1 发表评论：$2'],
  [/^(.*?) 在项目「[^」]+」的「(.+?)」完成审核：(.*)$/, '$1 审核「$2」：$3'],
  [/^客户已对项目「[^」]+」提交满意度评价$/, '客户提交了满意度评价']
]

function cleanContent(raw) {
  for (const [re, rep] of CONTENT_RULES) {
    if (re.test(raw)) return raw.replace(re, rep)
  }
  return raw
}

/**
 * 拆分消息：{ projectName, actor, text }
 * actor = 操作人姓名（评价类消息没有操作人，为空串），text = 去掉项目名后的正文
 */
export function splitMessage(msg) {
  const raw = msg?.msgContent || ''
  const projectName = projectNameOf(raw)
  const cleaned = cleanContent(raw)
  const sp = cleaned.indexOf(' ')
  // 姓名通常不含空格且很短；超过 20 字符视为无操作人的普通文案
  if (sp > 0 && sp <= 20) {
    return { projectName, actor: cleaned.slice(0, sp), text: cleaned.slice(sp + 1) }
  }
  return { projectName, actor: '', text: cleaned }
}

/** 消息文案（已精简） */
export function displayContent(msg) {
  const { actor, text } = splitMessage(msg)
  return actor ? `${actor} ${text}` : text
}

function toDate(v) {
  if (!v) return null
  // 兼容 "2026-10-14 10:31:30" 与 ISO 带 T 两种格式
  const d = new Date(String(v).replace(' ', 'T'))
  return Number.isNaN(d.getTime()) ? null : d
}

function pad(n) {
  return String(n).padStart(2, '0')
}

/** 绝对时间：今天只显示时分，其余显示 月-日 时:分 */
export function formatTime(v) {
  const d = toDate(v)
  if (!d) return ''
  const now = new Date()
  const hm = `${pad(d.getHours())}:${pad(d.getMinutes())}`
  if (d.toDateString() === now.toDateString()) return `今天 ${hm}`
  if (d.getFullYear() === now.getFullYear()) return `${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${hm}`
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

/** 相对时间：刚刚 / N 分钟前 / N 小时前 / 昨天 / 月-日 */
export function relativeTime(v) {
  const d = toDate(v)
  if (!d) return ''
  const diff = Date.now() - d.getTime()
  if (diff < 60 * 1000) return '刚刚'
  if (diff < 60 * 60 * 1000) return `${Math.floor(diff / 60000)} 分钟前`
  if (diff < 24 * 60 * 60 * 1000) return `${Math.floor(diff / 3600000)} 小时前`
  const days = Math.floor(diff / 86400000)
  if (days === 1) return '昨天'
  if (days < 7) return `${days} 天前`
  return formatTime(v)
}
