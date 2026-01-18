<template>
  <div class="settings-page">
    <a-page-header title="管理设置" subtitle="CAN指标平台配置管理" />

    <div class="settings-content">
      <!-- 左侧菜单 -->
      <a-menu
        class="settings-menu"
        :selected-keys="[currentSetting]"
        @menu-item-click="handleMenuClick"
      >
        <a-menu-item key="general">
          <template #icon><icon-settings /></template>
          基础设置
        </a-menu-item>
        <a-menu-item key="permission">
          <template #icon><icon-safe /></template>
          权限管理
        </a-menu-item>
        <a-menu-item key="notification">
          <template #icon><icon-notification /></template>
          通知配置
        </a-menu-item>
        <a-menu-item key="audit">
          <template #icon><icon-history /></template>
          审计日志
        </a-menu-item>
        <a-menu-item key="integration">
          <template #icon><icon-link /></template>
          集成配置
        </a-menu-item>
      </a-menu>

      <!-- 右侧内容 -->
      <div class="settings-panel">
        <!-- 基础设置 -->
        <a-card v-if="currentSetting === 'general'" title="基础设置">
          <a-form :model="generalSettings" layout="vertical">
            <a-form-item label="平台名称">
              <a-input v-model="generalSettings.platformName" />
            </a-form-item>
            <a-form-item label="默认时区">
              <a-select v-model="generalSettings.timezone">
                <a-option value="Asia/Shanghai">Asia/Shanghai (UTC+8)</a-option>
                <a-option value="UTC">UTC</a-option>
                <a-option value="America/New_York">America/New_York (UTC-5)</a-option>
              </a-select>
            </a-form-item>
            <a-form-item label="数据保留期限">
              <a-input-number v-model="generalSettings.dataRetentionDays" :min="30" :max="3650">
                <template #suffix>天</template>
              </a-input-number>
            </a-form-item>
            <a-form-item label="指标命名规范">
              <a-radio-group v-model="generalSettings.namingConvention">
                <a-radio value="snake_case">snake_case (下划线)</a-radio>
                <a-radio value="camelCase">camelCase (驼峰)</a-radio>
                <a-radio value="kebab-case">kebab-case (短横线)</a-radio>
              </a-radio-group>
            </a-form-item>
            <a-form-item label="启用指标审批流程">
              <a-switch v-model="generalSettings.enableApproval" />
            </a-form-item>
            <a-form-item>
              <a-button type="primary" @click="saveGeneralSettings">保存设置</a-button>
            </a-form-item>
          </a-form>
        </a-card>

        <!-- 权限管理 -->
        <a-card v-if="currentSetting === 'permission'" title="权限管理">
          <a-table :columns="roleColumns" :data="roles" :pagination="false">
            <template #permissions="{ record }">
              <a-space wrap>
                <a-tag v-for="perm in record.permissions" :key="perm" size="small">{{ perm }}</a-tag>
              </a-space>
            </template>
            <template #actions="{ record }">
              <a-space>
                <a-button type="text" size="small" @click="editRole(record)">编辑</a-button>
                <a-button type="text" size="small" status="danger" @click="deleteRole(record)" :disabled="record.isSystem">删除</a-button>
              </a-space>
            </template>
          </a-table>
          <a-button type="dashed" long style="margin-top: 16px" @click="showRoleModal = true">
            <template #icon><icon-plus /></template>
            添加角色
          </a-button>
        </a-card>

        <!-- 通知配置 -->
        <a-card v-if="currentSetting === 'notification'" title="通知配置">
          <a-form :model="notificationSettings" layout="vertical">
            <a-form-item label="指标异常告警">
              <a-switch v-model="notificationSettings.metricAlert" />
            </a-form-item>
            <a-form-item label="告警通知方式">
              <a-checkbox-group v-model="notificationSettings.alertChannels">
                <a-checkbox value="email">邮件</a-checkbox>
                <a-checkbox value="sms">短信</a-checkbox>
                <a-checkbox value="webhook">Webhook</a-checkbox>
                <a-checkbox value="dingtalk">钉钉</a-checkbox>
                <a-checkbox value="feishu">飞书</a-checkbox>
              </a-checkbox-group>
            </a-form-item>
            <a-form-item v-if="notificationSettings.alertChannels.includes('webhook')" label="Webhook URL">
              <a-input v-model="notificationSettings.webhookUrl" placeholder="https://..." />
            </a-form-item>
            <a-form-item label="指标更新通知">
              <a-switch v-model="notificationSettings.updateNotification" />
            </a-form-item>
            <a-form-item label="日报订阅">
              <a-switch v-model="notificationSettings.dailyReport" />
            </a-form-item>
            <a-form-item v-if="notificationSettings.dailyReport" label="日报发送时间">
              <a-time-picker v-model="notificationSettings.dailyReportTime" format="HH:mm" />
            </a-form-item>
            <a-form-item>
              <a-button type="primary" @click="saveNotificationSettings">保存设置</a-button>
            </a-form-item>
          </a-form>
        </a-card>

        <!-- 审计日志 -->
        <a-card v-if="currentSetting === 'audit'" title="审计日志">
          <template #extra>
            <a-space>
              <a-range-picker v-model="auditDateRange" style="width: 240px" />
              <a-button @click="exportAuditLogs">
                <template #icon><icon-download /></template>
                导出
              </a-button>
            </a-space>
          </template>
          <a-table :columns="auditColumns" :data="auditLogs" :pagination="{ pageSize: 10 }">
            <template #action="{ record }">
              <a-tag :color="getActionColor(record.action)">{{ record.action }}</a-tag>
            </template>
            <template #details="{ record }">
              <a-tooltip :content="record.details">
                <span class="details-text">{{ record.details }}</span>
              </a-tooltip>
            </template>
          </a-table>
        </a-card>

        <!-- 集成配置 -->
        <a-card v-if="currentSetting === 'integration'" title="集成配置">
          <a-collapse :default-active-key="['api']">
            <a-collapse-item key="api" header="API配置">
              <a-form layout="vertical">
                <a-form-item label="API访问地址">
                  <a-input :model-value="integrationSettings.apiUrl" readonly>
                    <template #append>
                      <a-button type="text" @click="copyApiUrl"><icon-copy /></a-button>
                    </template>
                  </a-input>
                </a-form-item>
                <a-form-item label="API密钥">
                  <a-input-password :model-value="integrationSettings.apiKey" readonly>
                    <template #append>
                      <a-button type="text" @click="regenerateApiKey">重新生成</a-button>
                    </template>
                  </a-input-password>
                </a-form-item>
                <a-form-item label="请求限制">
                  <a-input-number v-model="integrationSettings.rateLimit" :min="100" :max="10000">
                    <template #suffix>次/分钟</template>
                  </a-input-number>
                </a-form-item>
              </a-form>
            </a-collapse-item>
            <a-collapse-item key="bi" header="BI工具集成">
              <div class="bi-integrations">
                <div v-for="bi in biTools" :key="bi.name" class="bi-item">
                  <div class="bi-info">
                    <div class="bi-name">{{ bi.name }}</div>
                    <div class="bi-desc">{{ bi.description }}</div>
                  </div>
                  <a-switch v-model="bi.enabled" @change="toggleBiTool(bi)" />
                </div>
              </div>
            </a-collapse-item>
            <a-collapse-item key="scheduler" header="调度系统集成">
              <a-form layout="vertical">
                <a-form-item label="调度系统">
                  <a-select v-model="integrationSettings.scheduler">
                    <a-option value="airflow">Apache Airflow</a-option>
                    <a-option value="dolphin">DolphinScheduler</a-option>
                    <a-option value="azkaban">Azkaban</a-option>
                    <a-option value="custom">自定义</a-option>
                  </a-select>
                </a-form-item>
                <a-form-item label="调度系统地址">
                  <a-input v-model="integrationSettings.schedulerUrl" placeholder="http://..." />
                </a-form-item>
                <a-form-item>
                  <a-button type="primary" @click="testSchedulerConnection">测试连接</a-button>
                </a-form-item>
              </a-form>
            </a-collapse-item>
          </a-collapse>
        </a-card>
      </div>
    </div>

    <!-- 角色编辑弹窗 -->
    <a-modal v-model:visible="showRoleModal" title="添加角色" @ok="handleAddRole">
      <a-form :model="roleForm" layout="vertical">
        <a-form-item label="角色名称" required>
          <a-input v-model="roleForm.name" placeholder="请输入角色名称" />
        </a-form-item>
        <a-form-item label="角色描述">
          <a-input v-model="roleForm.description" placeholder="请输入角色描述" />
        </a-form-item>
        <a-form-item label="权限">
          <a-checkbox-group v-model="roleForm.permissions">
            <a-row>
              <a-col :span="12"><a-checkbox value="指标查看">指标查看</a-checkbox></a-col>
              <a-col :span="12"><a-checkbox value="指标编辑">指标编辑</a-checkbox></a-col>
              <a-col :span="12"><a-checkbox value="指标发布">指标发布</a-checkbox></a-col>
              <a-col :span="12"><a-checkbox value="指标删除">指标删除</a-checkbox></a-col>
              <a-col :span="12"><a-checkbox value="应用管理">应用管理</a-checkbox></a-col>
              <a-col :span="12"><a-checkbox value="系统设置">系统设置</a-checkbox></a-col>
            </a-row>
          </a-checkbox-group>
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Message } from '@arco-design/web-vue'

const currentSetting = ref('general')

const generalSettings = ref({
  platformName: 'NL2MQL2SQL 指标平台',
  timezone: 'Asia/Shanghai',
  dataRetentionDays: 365,
  namingConvention: 'snake_case',
  enableApproval: false
})

const notificationSettings = ref({
  metricAlert: true,
  alertChannels: ['email', 'dingtalk'],
  webhookUrl: '',
  updateNotification: true,
  dailyReport: false,
  dailyReportTime: '09:00'
})

const integrationSettings = ref({
  apiUrl: 'https://api.example.com/v1/metrics',
  apiKey: 'sk-xxxxxxxxxxxxxxxxxxxx',
  rateLimit: 1000,
  scheduler: 'airflow',
  schedulerUrl: ''
})

const auditDateRange = ref<string[]>([])
const showRoleModal = ref(false)
const roleForm = ref({
  name: '',
  description: '',
  permissions: [] as string[]
})

const roles = ref([
  { id: 1, name: '管理员', description: '系统管理员', permissions: ['指标查看', '指标编辑', '指标发布', '指标删除', '应用管理', '系统设置'], isSystem: true },
  { id: 2, name: '数据分析师', description: '数据分析人员', permissions: ['指标查看', '指标编辑', '应用管理'], isSystem: false },
  { id: 3, name: '普通用户', description: '只读用户', permissions: ['指标查看'], isSystem: false }
])

const auditLogs = ref([
  { id: 1, time: '2024-01-15 10:30:00', user: 'admin', action: '创建', target: '销售额指标', details: '创建了新的基础指标：销售额(gmv)' },
  { id: 2, time: '2024-01-15 10:25:00', user: 'analyst', action: '编辑', target: '订单量指标', details: '修改了指标计算逻辑' },
  { id: 3, time: '2024-01-15 10:20:00', user: 'admin', action: '发布', target: '客单价指标', details: '发布了指标到生产环境' },
  { id: 4, time: '2024-01-15 10:15:00', user: 'admin', action: '删除', target: '测试指标', details: '删除了测试用指标' },
  { id: 5, time: '2024-01-15 10:10:00', user: 'data_team', action: '查看', target: '用户留存率', details: '查看了指标详情' }
])

const biTools = ref([
  { name: 'Tableau', description: '连接Tableau进行可视化分析', enabled: true },
  { name: 'PowerBI', description: '连接Microsoft PowerBI', enabled: false },
  { name: 'Superset', description: '连接Apache Superset', enabled: true },
  { name: 'Metabase', description: '连接Metabase', enabled: false }
])

const roleColumns = [
  { title: '角色名称', dataIndex: 'name' },
  { title: '描述', dataIndex: 'description' },
  { title: '权限', slotName: 'permissions' },
  { title: '操作', slotName: 'actions', width: 120 }
]

const auditColumns = [
  { title: '时间', dataIndex: 'time', width: 160 },
  { title: '用户', dataIndex: 'user', width: 100 },
  { title: '操作', slotName: 'action', width: 80 },
  { title: '对象', dataIndex: 'target', width: 150 },
  { title: '详情', slotName: 'details' }
]

function handleMenuClick(key: string) {
  currentSetting.value = key
}

function getActionColor(action: string) {
  const colors: Record<string, string> = {
    '创建': 'green',
    '编辑': 'blue',
    '发布': 'purple',
    '删除': 'red',
    '查看': 'gray'
  }
  return colors[action] || 'gray'
}

function saveGeneralSettings() {
  Message.success('设置已保存')
}

function saveNotificationSettings() {
  Message.success('通知设置已保存')
}

function editRole(role: { name: string }) {
  Message.info(`编辑角色: ${role.name}`)
}

function deleteRole(role: { name: string }) {
  Message.warning(`删除角色: ${role.name}`)
}

function handleAddRole() {
  if (!roleForm.value.name) {
    Message.error('请输入角色名称')
    return
  }
  roles.value.push({
    id: Date.now(),
    name: roleForm.value.name,
    description: roleForm.value.description,
    permissions: roleForm.value.permissions,
    isSystem: false
  })
  Message.success('角色添加成功')
  showRoleModal.value = false
  roleForm.value = { name: '', description: '', permissions: [] }
}

function exportAuditLogs() {
  Message.info('导出审计日志')
}

function copyApiUrl() {
  navigator.clipboard.writeText(integrationSettings.value.apiUrl)
  Message.success('已复制到剪贴板')
}

function regenerateApiKey() {
  Message.info('API密钥已重新生成')
}

function toggleBiTool(bi: { name: string; enabled: boolean }) {
  Message.success(`${bi.name} ${bi.enabled ? '已启用' : '已禁用'}`)
}

function testSchedulerConnection() {
  Message.info('测试连接中...')
}
</script>

<style scoped>
.settings-page {
  padding: 0;
}

.settings-content {
  display: flex;
  gap: 16px;
  margin-top: 16px;
}

.settings-menu {
  width: 200px;
  flex-shrink: 0;
  border-radius: 4px;
}

.settings-panel {
  flex: 1;
  min-width: 0;
}

.bi-integrations {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.bi-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #f7f8fa;
  border-radius: 4px;
}

.bi-name {
  font-weight: 500;
}

.bi-desc {
  font-size: 12px;
  color: #86909c;
}

.details-text {
  display: inline-block;
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
