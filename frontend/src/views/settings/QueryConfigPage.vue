<template>
  <div class="query-config-page">
    <a-card title="问数配置" :bordered="false">
      <template #extra>
        <a-button type="primary" @click="handleSave">保存配置</a-button>
      </template>
      
      <a-tabs default-active-key="time_format">
        <a-tab-pane key="time_format" title="时间格式化配置">
          <div class="config-section">
            <div class="section-header">
              <h3>时间格式化类型</h3>
              <a-button type="outline" size="small" @click="addTimeFormat">
                <template #icon><icon-plus /></template>
                添加格式
              </a-button>
            </div>
            
            <a-table :data="timeFormats" :pagination="false">
              <template #columns>
                <a-table-column title="格式名称 (如 YYYY-MM)" data-index="name">
                  <template #cell="{ record }">
                    <a-input v-model="record.name" placeholder="请输入格式" />
                  </template>
                </a-table-column>
                <a-table-column title="显示标签 (如 按月)" data-index="label">
                  <template #cell="{ record }">
                    <a-input v-model="record.label" placeholder="请输入标签" />
                  </template>
                </a-table-column>
                <a-table-column title="后缀标识 (如 month)" data-index="suffix">
                  <template #cell="{ record }">
                    <a-input v-model="record.suffix" placeholder="请输入后缀" />
                  </template>
                </a-table-column>
                <a-table-column title="默认格式" data-index="is_default" :width="100">
                  <template #cell="{ record }">
                    <a-switch v-model="record.is_default" @change="(val) => handleDefaultChange(record, val)" />
                  </template>
                </a-table-column>
                <a-table-column title="操作" :width="80">
                  <template #cell="{ index }">
                    <a-button type="text" status="danger" @click="removeTimeFormat(index)">
                      <template #icon><icon-delete /></template>
                    </a-button>
                  </template>
                </a-table-column>
              </template>
            </a-table>
            
            <a-alert type="info" style="margin-top: 20px">
              提示：格式名称和后缀标识需要与后端解析逻辑保持对应。后缀标识将用于生成衍生维度名称（如 date__month）。
            </a-alert>
          </div>
        </a-tab-pane>
      </a-tabs>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Message } from '@arco-design/web-vue'
import { getSystemSetting, updateSystemSetting } from '@/api/settings'
import { IconPlus, IconDelete } from '@arco-design/web-vue/es/icon'

interface TimeFormat {
  name: string
  label: string
  suffix: string
  is_default: boolean
}

const timeFormats = ref<TimeFormat[]>([])

async function fetchConfig() {
  try {
    const res = await getSystemSetting('time_formats')
    timeFormats.value = res.value || []
  } catch (error) {
    console.error('Failed to fetch time formats:', error)
  }
}

function addTimeFormat() {
  timeFormats.value.push({
    name: '',
    label: '',
    suffix: '',
    is_default: false
  })
}

function removeTimeFormat(index: number) {
  timeFormats.value.splice(index, 1)
}

function handleDefaultChange(record: TimeFormat, val: any) {
  if (val) {
    timeFormats.value.forEach(item => {
      if (item !== record) item.is_default = false
    })
  }
}

async function handleSave() {
  // Validate
  if (timeFormats.value.some(f => !f.name || !f.label || !f.suffix)) {
    Message.warning('请填写完整的格式信息')
    return
  }

  try {
    await updateSystemSetting('time_formats', {
      value: timeFormats.value,
      description: '支持的时间格式化类型'
    })
    Message.success('保存成功')
  } catch (error) {
    Message.error('保存失败')
  }
}

onMounted(() => {
  fetchConfig()
})
</script>

<style scoped>
.query-config-page {
  padding: 0;
}
.config-section {
  padding: 16px 0;
}
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.section-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 500;
}
</style>
