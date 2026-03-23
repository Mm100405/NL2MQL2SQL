<template>
  <div class="fe-editor">
    <div v-for="(group, gi) in modelValue" :key="gi" class="fe-group">
      <!-- 组头部 -->
      <div class="fe-group-header">
        <span class="fe-group-label">条件组 {{ gi + 1 }}</span>
        <span class="fe-tag">组内</span>
        <a-radio-group v-model="group.operator" type="button" size="mini">
          <a-radio value="AND">AND</a-radio>
          <a-radio value="OR">OR</a-radio>
        </a-radio-group>
        <a-button v-if="modelValue.length > 1" type="text" status="danger" size="mini" @click="removeGroup(gi)">
          <template #icon><icon-delete /></template>删除组
        </a-button>
      </div>

      <!-- 组内项目（条件 + 子组） -->
      <div v-for="(item, ii) in group.items" :key="ii" class="fe-item">
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
          <a-button type="text" status="danger" size="mini" @click="removeItem(group, ii)">
            <template #icon><icon-close /></template>
          </a-button>
        </div>

        <!-- 递归子组 -->
        <div v-else-if="item.type === 'subgroup'" class="fe-subgroup">
          <div class="fe-subgroup-header">
            <span class="fe-tag">子组</span>
            <span class="fe-tag">组内</span>
            <a-radio-group v-model="item.operator" type="button" size="mini">
              <a-radio value="AND">AND</a-radio>
              <a-radio value="OR">OR</a-radio>
            </a-radio-group>
            <a-button type="text" status="danger" size="mini" @click="removeItem(group, ii)">
              <template #icon><icon-close /></template>
            </a-button>
          </div>
          <!-- 递归渲染子组内部 -->
          <div v-for="(sub, si) in item.items" :key="si" class="fe-item">
            <div v-if="sub.type === 'condition'" class="fe-row">
              <a-select v-model="sub.field" placeholder="字段" style="width: 160px" allow-clear>
                <a-option v-for="d in dimensions" :key="d.id || d.physical_column" :value="d.physical_column">{{ d.display_name || d.name }}</a-option>
              </a-select>
              <a-select v-model="sub.op" style="width: 90px">
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
              <a-input v-model="sub.value" placeholder="值" style="flex: 1" />
              <a-button type="text" status="danger" size="mini" @click="item.items.splice(si, 1)">
                <template #icon><icon-close /></template>
              </a-button>
            </div>
            <!-- 再次递归子组（第三层+） -->
            <div v-else-if="sub.type === 'subgroup'" class="fe-subgroup fe-subgroup-deep">
              <div class="fe-subgroup-header">
                <span class="fe-tag">子组</span>
                <span class="fe-tag">组内</span>
                <a-radio-group v-model="sub.operator" type="button" size="mini">
                  <a-radio value="AND">AND</a-radio>
                  <a-radio value="OR">OR</a-radio>
                </a-radio-group>
                <a-button type="text" status="danger" size="mini" @click="item.items.splice(si, 1)">
                  <template #icon><icon-close /></template>
                </a-button>
              </div>
              <div v-for="(deep, di) in sub.items" :key="di" class="fe-item">
                <div v-if="deep.type === 'condition'" class="fe-row">
                  <a-select v-model="deep.field" placeholder="字段" style="width: 160px" allow-clear>
                    <a-option v-for="d in dimensions" :key="d.id || d.physical_column" :value="d.physical_column">{{ d.display_name || d.name }}</a-option>
                  </a-select>
                  <a-select v-model="deep.op" style="width: 90px">
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
                  <a-input v-model="deep.value" placeholder="值" style="flex: 1" />
                  <a-button type="text" status="danger" size="mini" @click="sub.items.splice(di, 1)">
                    <template #icon><icon-close /></template>
                  </a-button>
                </div>
                <!-- 第四层递归：用组件自引用 -->
                <div v-else-if="deep.type === 'subgroup'" class="fe-subgroup fe-subgroup-deep">
                  <div class="fe-subgroup-header">
                    <span class="fe-tag">子组</span>
                    <span class="fe-tag">组内</span>
                    <a-radio-group v-model="deep.operator" type="button" size="mini">
                      <a-radio value="AND">AND</a-radio>
                      <a-radio value="OR">OR</a-radio>
                    </a-radio-group>
                    <a-button type="text" status="danger" size="mini" @click="sub.items.splice(di, 1)">
                      <template #icon><icon-close /></template>
                    </a-button>
                  </div>
                  <div v-for="(d2, d2i) in deep.items" :key="d2i" class="fe-item">
                    <div v-if="d2.type === 'condition'" class="fe-row">
                      <a-select v-model="d2.field" placeholder="字段" style="width: 160px" allow-clear>
                        <a-option v-for="d in dimensions" :key="d.id || d.physical_column" :value="d.physical_column">{{ d.display_name || d.name }}</a-option>
                      </a-select>
                      <a-select v-model="d2.op" style="width: 90px">
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
                      <a-input v-model="d2.value" placeholder="值" style="flex: 1" />
                      <a-button type="text" status="danger" size="mini" @click="deep.items.splice(d2i, 1)">
                        <template #icon><icon-close /></template>
                      </a-button>
                    </div>
                    <!-- 第五层+：递归组件自引用 -->
                    <div v-else-if="d2.type === 'subgroup'">
                      <FeSubGroup
                        :group="d2"
                        :dimensions="dimensions"
                        :depth="(depth || 0) + 1"
                        @remove-item="(idx: number) => deep.items.splice(idx, 1)"
                      />
                    </div>
                  </div>
                  <div class="fe-subgroup-actions">
                    <a-button type="text" size="mini" @click="deep.items.push({ type: 'condition', field: '', op: '=', value: '' })">
                      <template #icon><icon-plus /></template>添加条件
                    </a-button>
                    <a-button v-if="(depth || 0) < 5" type="text" size="mini" @click="deep.items.push({ type: 'subgroup', operator: 'AND', items: [{ type: 'condition', field: '', op: '=', value: '' }] })">
                      <template #icon><icon-plus /></template>添加子组
                    </a-button>
                  </div>
                </div>
              </div>
              <div class="fe-subgroup-actions">
                <a-button type="text" size="mini" @click="sub.items.push({ type: 'condition', field: '', op: '=', value: '' })">
                  <template #icon><icon-plus /></template>添加条件
                </a-button>
                <a-button v-if="(depth || 0) < 5" type="text" size="mini" @click="sub.items.push({ type: 'subgroup', operator: 'AND', items: [{ type: 'condition', field: '', op: '=', value: '' }] })">
                  <template #icon><icon-plus /></template>添加子组
                </a-button>
              </div>
            </div>
          </div>
          <div class="fe-subgroup-actions">
            <a-button type="text" size="mini" @click="item.items.push({ type: 'condition', field: '', op: '=', value: '' })">
              <template #icon><icon-plus /></template>添加条件
            </a-button>
            <a-button v-if="(depth || 0) < 5" type="text" size="mini" @click="item.items.push({ type: 'subgroup', operator: 'AND', items: [{ type: 'condition', field: '', op: '=', value: '' }] })">
              <template #icon><icon-plus /></template>添加子组
            </a-button>
          </div>
        </div>
      </div>

      <!-- 组内添加按钮 -->
      <div class="fe-group-actions">
        <a-button type="text" size="mini" @click="group.items.push({ type: 'condition', field: '', op: '=', value: '' })">
          <template #icon><icon-plus /></template>添加条件
        </a-button>
        <a-button type="text" size="mini" @click="group.items.push({ type: 'subgroup', operator: 'AND', items: [{ type: 'condition', field: '', op: '=', value: '' }] })">
          <template #icon><icon-plus /></template>添加子组
        </a-button>
      </div>
    </div>

    <!-- 组间连接符 -->
    <div v-if="modelValue.length > 1" class="fe-connector">
      <span class="fe-connector-label">组间关系：</span>
      <a-radio-group v-model="rootOperator" type="button" size="mini">
        <a-radio value="AND">AND</a-radio>
        <a-radio value="OR">OR</a-radio>
      </a-radio-group>
    </div>
    <a-button type="dashed" size="small" long @click="addGroup">
      <template #icon><icon-plus /></template>添加条件组
    </a-button>
  </div>
</template>

<script lang="ts">
import { defineComponent, type PropType } from 'vue'
import FeSubGroup from './FeSubGroup.vue'

export interface FeCondition {
  type: 'condition'
  field: string
  op: string
  value: string
}

export interface FeSubGroup {
  type: 'subgroup'
  operator: 'AND' | 'OR'
  items: Array<FeCondition | FeSubGroup>
}

export interface FeGroup {
  operator: 'AND' | 'OR'
  items: Array<FeCondition | FeSubGroup>
}

export default defineComponent({
  name: 'FilterEditor',
  components: { FeSubGroup },
  props: {
    modelValue: {
      type: Array as PropType<FeGroup[]>,
      required: true
    },
    dimensions: {
      type: Array as PropType<any[]>,
      default: () => []
    },
    depth: {
      type: Number,
      default: 0
    }
  },
  emits: ['update:modelValue'],
  data() {
    return {
      rootOperator: 'AND' as 'AND' | 'OR'
    }
  },
  methods: {
    addGroup() {
      this.modelValue.push({
        operator: 'AND' as const,
        items: [{ type: 'condition', field: '', op: '=', value: '' }]
      })
    },
    removeGroup(idx: number) {
      this.modelValue.splice(idx, 1)
    },
    removeItem(group: FeGroup, idx: number) {
      group.items.splice(idx, 1)
    },
    getRootOperator(): 'AND' | 'OR' {
      return this.rootOperator
    }
  }
})
</script>

<style scoped>
.fe-editor { display: flex; flex-direction: column; gap: 10px; }
.fe-group { border: 1px solid var(--color-border-2); border-radius: 6px; padding: 10px 12px; background: var(--color-fill-1); }
.fe-group-header { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.fe-group-label { font-size: 12px; font-weight: 600; color: var(--color-text-2); }
.fe-tag { font-size: 11px; color: var(--color-text-3); background: var(--color-fill-2); padding: 1px 6px; border-radius: 4px; }
.fe-item { margin-bottom: 4px; }
.fe-row { display: flex; gap: 6px; align-items: center; margin-bottom: 4px; }
.fe-subgroup { border: 1px dashed var(--color-border-3); border-radius: 4px; padding: 8px 10px; margin-bottom: 6px; background: var(--color-bg-2); }
.fe-subgroup-deep { background: var(--color-fill-1); }
.fe-subgroup-header { display: flex; align-items: center; gap: 6px; margin-bottom: 6px; }
.fe-subgroup-actions { display: flex; gap: 8px; padding-top: 4px; }
.fe-group-actions { display: flex; gap: 8px; padding-top: 4px; }
.fe-connector { display: flex; align-items: center; gap: 8px; padding: 0 4px; }
.fe-connector-label { font-size: 12px; color: var(--color-text-3); }
</style>
