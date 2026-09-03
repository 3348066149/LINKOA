// 路由定义 + 守卫（PRD 9.1 页面清单 / 9.4 守卫规则）
import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'

const ALL = null // 全部角色可见

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/login/Index.vue'),
    meta: { title: '登录', public: true }
  },
  {
    path: '/',
    component: () => import('@/layouts/MainLayout.vue'),
    children: [
      {
        path: '',
        name: 'Dashboard',
        component: () => import('@/views/dashboard/Index.vue'),
        meta: { title: '首页', roles: ALL }
      },
      {
        path: 'projects',
        name: 'ProjectList',
        component: () => import('@/views/project/List.vue'),
        meta: { title: '项目列表', roles: ALL }
      },
      {
        path: 'projects/:id',
        name: 'ProjectDetail',
        component: () => import('@/views/project/Detail.vue'),
        meta: { title: '项目详情', roles: ALL }
      },
      {
        path: 'customers',
        name: 'Customer',
        component: () => import('@/views/customer/Index.vue'),
        meta: { title: '客户管理', roles: ALL }
      },
      {
        path: 'templates',
        name: 'TemplateList',
        component: () => import('@/views/template/List.vue'),
        meta: { title: '模板列表', roles: ALL }
      },
      {
        path: 'templates/:id/edit',
        name: 'TemplateEdit',
        component: () => import('@/views/template/Edit.vue'),
        meta: { title: '模板编辑', roles: ['管理员'] }
      },
      {
        path: 'system/users',
        name: 'SysUser',
        component: () => import('@/views/system/User.vue'),
        meta: { title: '用户管理', roles: ['管理员'] }
      },
      {
        path: 'system/nodeTemplates',
        name: 'NodeTemplate',
        component: () => import('@/views/system/NodeTemplate.vue'),
        meta: { title: '节点模板', roles: ['管理员'] }
      },
      {
        path: 'system/aiConfig',
        name: 'AiConfig',
        component: () => import('@/views/system/AiConfig.vue'),
        meta: { title: 'AI设置', roles: ['管理员'] }
      },
      {
        path: 'system/logs',
        name: 'SysLog',
        component: () => import('@/views/system/Log.vue'),
        meta: { title: '审计日志', roles: ['管理员'] }
      },
      {
        path: 'messages',
        name: 'Message',
        component: () => import('@/views/message/Index.vue'),
        meta: { title: '消息中心', roles: ALL }
      },
      {
        path: 'reports',
        name: 'Report',
        component: () => import('@/views/report/Index.vue'),
        meta: { title: '报表导出', roles: ['管理员'] }
      },
      {
        path: 'files',
        name: 'Files',
        component: () => import('@/views/files/Index.vue'),
        meta: { title: '文件管理', roles: ALL }
      }
    ]
  },
  // 客户门户：独立只读界面（客户登录后只能看自己的项目与节点进度）
  {
    path: '/client',
    name: 'ClientHome',
    component: () => import('@/views/client/Index.vue'),
    meta: { title: '我的项目', roles: ['客户'] }
  },
  {
    path: '/client/projects/:id',
    name: 'ClientProject',
    component: () => import('@/views/client/Project.vue'),
    meta: { title: '项目进度', roles: ['客户'] }
  },
  // 404：未匹配路由渲染真实错误页（阶段三），未登录时守卫会优先拦截到 /login
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/error/NotFound.vue'),
    meta: { title: '页面不存在' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to) => {
  const userStore = useUserStore()
  // 未登录访问任何页面 -> /login
  if (!to.meta.public && !userStore.isLogin) {
    return '/login'
  }
  // 已登录访问 /login -> 按角色跳转
  if (to.path === '/login' && userStore.isLogin) {
    return userStore.role === '客户' ? '/client' : '/'
  }
  // 客户账号：只能访问客户门户，访问 OA 内部页面一律回门户
  if (userStore.role === '客户' && !to.path.startsWith('/client')) {
    return '/client'
  }
  // 非客户访问客户门户 -> 回 OA 首页
  if (to.path.startsWith('/client') && userStore.role !== '客户') {
    return '/'
  }
  // 直接输入 URL 访问无权限页面 -> 首页
  if (to.meta.roles && !userStore.hasRole(to.meta.roles)) {
    return userStore.role === '客户' ? '/client' : '/'
  }
  document.title = to.meta.title ? `${to.meta.title} - 领客文创` : '领客文创 OA'
  return true
})

export default router
