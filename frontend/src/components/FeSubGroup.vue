<template>
  <div class="fe-subgroup">
    <div class="fe-subgroup-header">
      <span class="fe-tag">子组</span>
      <span class="fe-tag">组内</span>
      <a-radio-group v-model="group.operator" type="button" size="mini">
        <a-radio value="AND">AND</a-radio>
        <a-radio value="OR">OR</a-radio>
      </a-radio-group>
      <a-button type="text" status="danger" size="mini" @click="$emit('removeItem', selfIndex)">
        <template #icon><icon-close /></template>
      </a-button>
    </div>

    <div v-for="(item, idx) in group.items" :key="idx" class="fe-item">
      <!-- 叶子条件 -->
      <div v-if="item.type === 'condition'" class="fe-row">
        <a-select v-model="item.field" placeholder="字段" style="width: 160px" allow-clear>
          <a-option v-for="d in dimensions" :key="d.id || d.physical_column" :value="d.physical_column">{{ d.display_name || d.name }}</a-option>
        </a-select>
        <a-select v-model="item.op" style="width: 90px">
          <a-option value="=">=</a-option>
          <a-option value="!=">!=</a-option>
          <a-option value=">">></a-option>
          <a-option value="<"><</a-option>
          <a-option value=">=">>=</a-option>
          <a-option value="<="><=</a-option>
          <a-option value="LIKE">LIKE</a-option>
          <a-option value="IN">IN</a-option>
          <a-option value="NOT IN">NOT IN</a-option>
        </a-select>
        <a-input v-model="item.value" placeholder="值" style="flex: 1" />
        <a-button type="text" status="danger" size="mini" @click="group.items.splice(idx, 1)">
          <template #icon><icon-close /></template>
        </a-button>
      </div>

      <!-- 递归子组 -->
      <div v-else-if="item.type === 'subgroup'" class="fe-subgroup fe-subgroup-deep">
        <FeSubGroup
          :group="item"
          :dimensions="dimensions"
          :depth="depth + 1"
          :self-index="idx"
          @remove-item="(i: number) => group.items.splice(i, 1)"
        />
      </div>
    </div>

    <div class="fe-subgroup-actions">
      <a-button type="text" size="mini" @click="group.items.push({ type: 'condition', field: '', op: '=', value: '' })">
        <template #icon><icon-plus /></template>添加条件
      </a-button>
      <a-button v-if="depth < 8" type="text" size="mini" @click="group.items.push({ type: 'subgroup', operator: 'AND', items: [{ type: 'condition', field: '', op: '=', value: '' }] })">
        <template #icon><icon-plus /></template>添加子组
      </a-button>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent, type PropType } from 'vue'

interface FeCondition {
  type: 'condition'
  field: string
  op: string
  value: string
}

interface FeSubGroup {
  type: 'subgroup'
  operator: 'AND' | 'OR'
  items: Array<FeCondition | FeSubGroup>
}

export default defineComponent({
  name: 'FeSubGroup',
  props: {
    group: { type: Object as PropType<FeSubGroup>, required: true },
    dimensions: { type: Array as PropType<any[]>, default: () => [] },
    depth: { type: Number, default: 0 },
    selfIndex: { type: Number, default: 0 }
  },
  emits: ['removeItem']
})
</script>

<style scoped>
.fe-subgroup { border: 1px dashed var(--color-border-3); border-radius: 4px; padding: 8px 10px; margin-bottom: 6px; background: var(--color-bg-2); }
.fe-subgroup-deep { background: var(--color-fill-1); }
.fe-subgroup-header { display: flex; align-items: center; gap: 6px; margin-bottom: 6px; }
.fe-tag { font-size: 11px; color: var(--color-text-3); background: var(--color-fill-2); padding: 1px 6px; border-radius: 4px; }
.fe-item { margin-bottom: 4px; }
.fe-row { display: flex; gap: 6px; align-items: center; margin-bottom: 4px; }
.fe-subgroup-actions { display: flex; gap: 8px; padding-top: 4px; }
</style>
