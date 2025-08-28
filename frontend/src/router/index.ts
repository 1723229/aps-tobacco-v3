import { createRouter, createWebHistory } from "vue-router";
import Home from "../views/Home.vue";

const router = createRouter({
    history: createWebHistory(import.meta.env.BASE_URL),
    routes: [
        {
            path: "/",
            name: "home",
            component: Home,
            meta: {
                title: "APS 烟草生产计划系统",
            },
        },
        {
            path: "/decade-plan/entry",
            name: "decade-plan-entry",
            component: () => import("../views/DecadePlanEntry.vue"),
            meta: {
                title: "卷包旬计划录入",
            },
        },
        {
            path: "/decade-plan/detail/:batchId",
            name: "decade-plan-detail",
            component: () => import("../views/DecadePlanDetail.vue"),
            meta: {
                title: "旬计划详情",
            },
            props: true,
        },
        {
            path: "/scheduling",
            name: "SchedulingManagement",
            component: () => import("../views/SchedulingManagement.vue"),
            meta: {
                title: "智能排产管理",
            },
        },
        {
            path: "/scheduling/history",
            name: "SchedulingHistory",
            component: () => import("../views/SchedulingHistory.vue"),
            meta: {
                title: "排产历史记录",
            },
        },
        {
            path: "/scheduling/task/:taskId",
            name: "SchedulingTaskDetail",
            component: () => import("../views/SchedulingTaskDetail.vue"),
            meta: {
                title: "排产任务详情",
            },
            props: true,
        },
        {
            path: "/gantt-chart",
            name: "GanttChart",
            component: () => import("../views/GanttChart.vue"),
            meta: {
                title: "生产甘特图",
            },
        },

        {
            path: "/machine-config",
            name: "MachineConfig",
            component: () => import("../views/MachineConfig.vue"),
            meta: {
                title: "机台配置管理",
            },
        },
    ],
});

// 路由守卫
router.beforeEach((to, from, next) => {
    // 设置页面标题
    if (to.meta.title) {
        document.title = `${to.meta.title} - APS 系统`;
    } else {
        document.title = "APS 烟草生产计划系统";
    }

    next();
});

export default router;
