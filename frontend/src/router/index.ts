import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  // 主布局 - Agent 查询页面（默认首页）
  {
    path: '/',
    component: () => import('@/views/layout/MainLayout.vue'),
    redirect: '/agent-query',
    children: [
      {
        path: 'query',
        name: 'Query',
        component: () => import('@/views/query/QueryPage.vue'),
        meta: { title: '智能问数', icon: 'icon-search' }
      },
      {
        path: 'agent-query',
        name: 'AgentQuery',
        component: () => import('@/views/query/AgentQueryPage.vue'),
        meta: { title: 'Agent查询', icon: 'icon-thunderbolt' }
      },
      {
        path: 'query/history',
        name: 'QueryHistory',
        component: () => import('@/views/query/HistoryPage.vue'),
        meta: { title: '查询历史', icon: 'icon-history' }
      }
    ]
  },
  
  // 管理中心 - 独立布局
  {
    path: '/management',
    component: () => import('@/views/management/ManagementLayout.vue'),
    redirect: '/management/data/datasources',
    children: [
      // 数据管理
      {
        path: 'data/datasources',
        name: 'DataSources',
        component: () => import('@/views/semantic/DataSourceList.vue'),
        meta: { title: '数据源管理' }
      },
      {
        path: 'data/datasets',
        name: 'Datasets',
        component: () => import('@/views/semantic/DatasetList.vue'),
        meta: { title: '物理表管理' }
      },
      {
        path: 'data/metrics',
        name: 'Metrics',
        component: () => import('@/views/semantic/MetricList.vue'),
        meta: { title: '指标管理' }
      },
      {
        path: 'data/dimensions',
        name: 'Dimensions',
        component: () => import('@/views/semantic/DimensionList.vue'),
        meta: { title: '维度管理' }
      },
      {
        path: 'data/views',
        name: 'Views',
        component: () => import('@/views/semantic/ViewList.vue'),
        meta: { title: '视图管理' }
      },
      {
        path: 'data/views/:id',
        name: 'ViewDesigner',
        component: () => import('@/views/semantic/ViewDesigner.vue'),
        meta: { title: '视图设计器', hidden: true }
      },
      {
        path: 'data/dictionaries',
        name: 'Dictionaries',
        component: () => import('@/views/semantic/DictionaryManage.vue'),
        meta: { title: '字典管理' }
      },
      
      // 系统配置
      {
        path: 'system/model',
        name: 'ModelConfig',
        component: () => import('@/views/settings/ModelConfigPage.vue'),
        meta: { title: '模型配置' }
      },
      {
        path: 'system/query',
        name: 'QueryConfig',
        component: () => import('@/views/settings/QueryConfigPage.vue'),
        meta: { title: '问数配置' }
      },
      {
        path: 'system/lineage',
        name: 'Lineage',
        component: () => import('@/views/semantic/LineagePage.vue'),
        meta: { title: '血缘管理' }
      },
      
      // 高级模块 - AIR
      {
        path: 'advanced/air/workbook',
        name: 'Workbook',
        component: () => import('@/views/air/WorkbookPage.vue'),
        meta: { title: 'AIR - 工作簿' }
      },
      {
        path: 'advanced/air/integration',
        name: 'Integration',
        component: () => import('@/views/air/IntegrationPage.vue'),
        meta: { title: 'AIR - 数据集成' }
      },
      {
        path: 'advanced/air/consolidation',
        name: 'Consolidation',
        component: () => import('@/views/air/ConsolidationPage.vue'),
        meta: { title: 'AIR - 数据整合' }
      },
      {
        path: 'advanced/air/acceleration',
        name: 'AirAcceleration',
        component: () => import('@/views/air/AccelerationPage.vue'),
        meta: { title: 'AIR - 数据加速' }
      },
      
      // 高级模块 - CAN
      {
        path: 'advanced/can/catalog',
        name: 'Catalog',
        component: () => import('@/views/can/CatalogPage.vue'),
        meta: { title: 'CAN - 指标目录' }
      },
      {
        path: 'advanced/can/application',
        name: 'Application',
        component: () => import('@/views/can/ApplicationPage.vue'),
        meta: { title: 'CAN - 指标应用' }
      },
      {
        path: 'advanced/can/acceleration',
        name: 'CanAcceleration',
        component: () => import('@/views/can/AccelerationPage.vue'),
        meta: { title: 'CAN - 指标加速' }
      },
      {
        path: 'advanced/can/settings',
        name: 'CanSettings',
        component: () => import('@/views/can/SettingsPage.vue'),
        meta: { title: 'CAN - 管理设置' }
      },
      
      // 高级模块 - BIG
      {
        path: 'advanced/big/lineage',
        name: 'OperatorLineage',
        component: () => import('@/views/big/OperatorLineagePage.vue'),
        meta: { title: 'BIG - 算子级血缘' }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
