import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'home',
    component: () => import('@/views/HomeView.vue'),
    meta: { title: '工作台', requiresAuth: true },
  },
  {
    path: '/resumes',
    name: 'resumes',
    component: () => import('@/views/ResumesView.vue'),
    meta: { title: '我的简历', requiresAuth: true },
  },
  {
    path: '/resumes/:id',
    name: 'resume-workspace',
    component: () => import('@/views/ResumeWorkspaceView.vue'),
    meta: { title: '简历结构化', requiresAuth: true },
  },
  {
    path: '/resumes/:id/diagnose',
    name: 'diagnosis',
    component: () => import('@/views/DiagnosisView.vue'),
    meta: { title: '四维诊断', requiresAuth: true },
  },
  {
    path: '/jds',
    name: 'jds',
    component: () => import('@/views/JdsView.vue'),
    meta: { title: '岗位描述', requiresAuth: true },
  },
  {
    path: '/interviews',
    name: 'interviews',
    component: () => import('@/views/InterviewsView.vue'),
    meta: { title: '模拟面试', requiresAuth: true },
  },
  {
    path: '/interviews/:id',
    name: 'interview-room',
    component: () => import('@/views/InterviewRoomView.vue'),
    meta: { title: '面试间', requiresAuth: true },
  },
  {
    path: '/growth',
    name: 'growth',
    component: () => import('@/views/GrowthView.vue'),
    meta: { title: '成长分析', requiresAuth: true },
  },
  {
    path: '/auth',
    name: 'auth',
    component: () => import('@/views/AuthView.vue'),
    meta: { title: '登录 / 注册', publicOnly: true },
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('@/views/NotFoundView.vue'),
    meta: { title: '页面不存在' },
  },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()

  if (to.meta.requiresAuth || to.meta.publicOnly) {
    await auth.restore()
  }

  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return { name: 'auth', query: { redirect: to.fullPath } }
  }

  if (to.meta.publicOnly && auth.isAuthenticated) {
    return { name: 'home' }
  }

  return true
})

router.afterEach((to) => {
  const title = typeof to.meta.title === 'string' ? to.meta.title : ''
  document.title = title ? `${title} · 智能简历诊断与面试模拟平台` : '智能简历诊断与面试模拟平台'
})

export default router
