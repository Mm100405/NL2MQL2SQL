import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    component: () => import('@/views/layout/MainLayout.vue'),
    redirect: '/query',
    children: [
      // 智能问数
      {
        path: 'query',
        name: 'Query',
        component: () => import('@/views/query/QueryPage.vue'),
        meta: { title: '智能问数', icon: 'icon-search' }
      },
      {
        path: 'query/history',
        name: 'QueryHistory',
        component: () => import('@/views/query/HistoryPage.vue'),
        meta: { title: '查询历史', icon: 'icon-history' }
      },
      // 语义层管理
      {
        path: 'semantic',
        name: 'Semantic',
        redirect: '/semantic/datasources',
        meta: { title: '语义层管理', icon: 'icon-layers' },
        children: [
          {
            path: 'datasources',
            name: 'DataSources',
            component: () => import('@/views/semantic/DataSourceList.vue'),
            meta: { title: '数据源管理' }
          },
          {
            path: 'datasets',
            name: 'Datasets',
            component: () => import('@/views/semantic/DatasetList.vue'),
            meta: { title: '数据集管理' }
          },
          {
            path: 'metrics',
            name: 'Metrics',
            component: () => import('@/views/semantic/MetricList.vue'),
            meta: { title: '指标管理' }
          },
          {
            path: 'dimensions',
            name: 'Dimensions',
            component: () => import('@/views/semantic/DimensionList.vue'),
            meta: { title: '维度管理' }
          },
          {
            path: 'lineage',
            name: 'Lineage',
            component: () => import('@/views/semantic/LineagePage.vue'),
            meta: { title: '血缘管理' }
          }
        ]
      },
      // 系统设置
      {
        path: 'settings',
        name: 'Settings',
        redirect: '/settings/model',
        meta: { title: '系统设置', icon: 'icon-settings' },
        children: [
          {
            path: 'model',
            name: 'ModelConfig',
            component: () => import('@/views/settings/ModelConfigPage.vue'),
            meta: { title: '模型配置' }
          }
        ]
      },
      // AIR模块（预留）
      {
        path: 'air',
        name: 'Air',
        redirect: '/air/workbook',
        meta: { title: 'AIR', icon: 'icon-cloud', reserved: true },
        children: [
          {
            path: 'workbook',
            name: 'Workbook',
            component: () => import('@/views/air/WorkbookPage.vue'),
            meta: { title: '工作簿' }
          },
          {
            path: 'integration',
            name: 'Integration',
            component: () => import('@/views/air/IntegrationPage.vue'),
            meta: { title: '数据集成' }
          },
          {
            path: 'consolidation',
            name: 'Consolidation',
            component: () => import('@/views/air/ConsolidationPage.vue'),
            meta: { title: '数据整合' }
          },
          {
            path: 'acceleration',
            name: 'AirAcceleration',
            component: () => import('@/views/air/AccelerationPage.vue'),
            meta: { title: '数据加速' }
          }
        ]
      },
      // CAN模块（预留）
      {
        path: 'can',
        name: 'Can',
        redirect: '/can/catalog',
        meta: { title: 'CAN', icon: 'icon-bar-chart', reserved: true },
        children: [
          {
            path: 'catalog',
            name: 'Catalog',
            component: () => import('@/views/can/CatalogPage.vue'),
            meta: { title: '指标目录' }
          },
          {
            path: 'application',
            name: 'Application',
            component: () => import('@/views/can/ApplicationPage.vue'),
            meta: { title: '指标应用' }
          },
          {
            path: 'can-acceleration',
            name: 'CanAcceleration',
            component: () => import('@/views/can/AccelerationPage.vue'),
            meta: { title: '指标加速' }
          },
          {
            path: 'can-settings',
            name: 'CanSettings',
            component: () => import('@/views/can/SettingsPage.vue'),
            meta: { title: '管理设置' }
          }
        ]
      },
      // BIG模块（预留）
      {
        path: 'big',
        name: 'Big',
        redirect: '/big/operator-lineage',
        meta: { title: 'BIG', icon: 'icon-branch', reserved: true },
        children: [
          {
            path: 'operator-lineage',
            name: 'OperatorLineage',
            component: () => import('@/views/big/OperatorLineagePage.vue'),
            meta: { title: '算子级血缘' }
          }
        ]
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
