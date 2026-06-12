import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'home',
    component: () => import('@/views/HomePage.vue'),
  },
  {
    path: '/detect',
    name: 'detect',
    component: () => import('@/views/DetectPage.vue'),
  },
  {
    path: '/detect/live',
    name: 'liveMonitor',
    component: () => import('@/views/LiveMonitor.vue'),
  },
  {
    path: '/history',
    name: 'history',
    component: () => import('@/views/HistoryPage.vue'),
  },
  {
    path: '/dashboard',
    name: 'dashboard',
    component: () => import('@/views/DashboardPage.vue'),
  },
  {
    path: '/devices',
    name: 'devices',
    component: () => import('@/views/DevicesPage.vue'),
  },
  {
    path: '/review',
    name: 'review',
    component: () => import('@/views/ReviewPage.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
