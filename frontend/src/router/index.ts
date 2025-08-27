import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: Home,
      meta: {
        title: 'APS 烟草生产计划系统'
      }
    },
    {
      path: '/decade-plan/entry',
      name: 'decade-plan-entry',
      component: () => import('../views/DecadePlanEntry.vue'),
      meta: {
        title: '卷包旬计划录入'
      }
    },
    {
      path: '/decade-plan/detail/:batchId',
      name: 'decade-plan-detail',
      component: () => import('../views/DecadePlanDetail.vue'),
      meta: {
        title: '旬计划详情'
      },
      props: true
    },
    {
      path: '/about',
      name: 'about',
      component: () => import('../views/AboutView.vue'),
      meta: {
        title: '关于系统'
      }
    },
  ],
})

// 路由守卫
router.beforeEach((to, from, next) => {
  // 设置页面标题
  if (to.meta.title) {
    document.title = `${to.meta.title} - APS 系统`
  } else {
    document.title = 'APS 烟草生产计划系统'
  }
  
  next()
})

export default router
