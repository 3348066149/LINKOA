// 节点图标工具：预设 20 个常用图标 + 自定义图标（uploads 路径）判定
import {
  Aim, Box, Collection, Compass, DataAnalysis, Document, EditPen, Files,
  FolderOpened, Link, MagicStick, Memo, Monitor, Notebook, Picture,
  PictureFilled, ShoppingCart, Stamp, Tickets, TrendCharts
} from '@element-plus/icons-vue'

// 预设 20 个图标（管理员可选；画布节点库与画布节点共用）
export const PRESET_ICONS = [
  { name: 'Document', label: '文档' },
  { name: 'Picture', label: '图片' },
  { name: 'DataAnalysis', label: '数据' },
  { name: 'TrendCharts', label: '趋势' },
  { name: 'EditPen', label: '编辑' },
  { name: 'Files', label: '文件' },
  { name: 'FolderOpened', label: '文件夹' },
  { name: 'Link', label: '链接' },
  { name: 'PictureFilled', label: '相册' },
  { name: 'Box', label: '盒子' },
  { name: 'Monitor', label: '监控' },
  { name: 'Aim', label: '目标' },
  { name: 'Tickets', label: '工单' },
  { name: 'Memo', label: '备忘' },
  { name: 'Notebook', label: '记事本' },
  { name: 'Collection', label: '收藏' },
  { name: 'Stamp', label: '印章' },
  { name: 'ShoppingCart', label: '购物' },
  { name: 'Compass', label: '指南' },
  { name: 'MagicStick', label: '魔法' }
]

export const ICON_MAP = {
  Aim, Box, Collection, Compass, DataAnalysis, Document, EditPen, Files,
  FolderOpened, Link, MagicStick, Memo, Monitor, Notebook, Picture,
  PictureFilled, ShoppingCart, Stamp, Tickets, TrendCharts
}

// 是否为自定义上传的图标图片（相对 uploads/ 路径）
export function isImageIcon(icon) {
  return !!icon && (icon.startsWith('uploads/') || icon.startsWith('node_icon/') || icon.startsWith('http'))
}

// 完整图标 URL（相对 uploads/ 的相对路径 → /uploads/xxx）
export function iconUrl(icon) {
  if (!icon) return ''
  return `/uploads/${icon.replace(/^uploads\//, '')}`
}
