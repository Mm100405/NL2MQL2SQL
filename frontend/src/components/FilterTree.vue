<template>
  <span v-if="isLeaf" class="filter-tree">
    <a-tag size="small" color="arcoblue">{{ formatField(node.field) }}</a-tag>
    <span class="filter-op">{{ node.op }}</span>
    <a-tag size="small" color="orangered">{{ String(node.value) }}</a-tag>
  </span>
  <span v-else-if="conditions.length > 0 && depth < 10" class="filter-tree">
    <span v-if="!isRoot" class="filter-bracket">(</span>
    <template v-for="(child, idx) in conditions" :key="idx">
      <FilterTree
        :node="child"
        :format-field="formatField"
        :is-root="false"
        :depth="depth + 1"
      />
      <span v-if="idx < conditions.length - 1" class="filter-connector" :class="connectorClass">
        {{ (node as MQLFilterGroup).operator || 'AND' }}
      </span>
    </template>
    <span v-if="!isRoot" class="filter-bracket">)</span>
  </span>
</template>

<script lang="ts">
import { defineComponent, type PropType } from 'vue'
import type { MQLFilterCondition, MQLFilterGroup } from '@/api/types'

export default defineComponent({
  name: 'FilterTree',
  props: {
    node: { type: Object as PropType<MQLFilterCondition | MQLFilterGroup>, required: true },
    formatField: { type: Function as PropType<(field: string) => string>, required: true },
    isRoot: { type: Boolean, default: true },
    depth: { type: Number, default: 0 }
  },
  computed: {
    isLeaf(): boolean {
      return 'field' in this.node && !Array.isArray((this.node as MQLFilterGroup).conditions)
    },
    conditions(): any[] {
      return (this.node as MQLFilterGroup).conditions || []
    },
    connectorClass(): string {
      return `filter-connector-${((this.node as MQLFilterGroup).operator || 'and').toLowerCase()}`
    }
  }
})
</script>

<style scoped>
.filter-tree {
  display: inline-flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 2px;
}
.filter-op {
  margin: 0 2px;
  font-size: 12px;
  color: var(--color-text-2);
  font-family: monospace;
}
.filter-bracket {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-3);
  margin: 0 1px;
}
.filter-connector {
  margin: 0 6px;
  font-size: 11px;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: 4px;
  letter-spacing: 0.5px;
}
.filter-connector-and {
  color: rgb(var(--green-6));
  background: rgb(var(--green-1));
}
.filter-connector-or {
  color: rgb(var(--orange-6));
  background: rgb(var(--orange-1));
}
</style>
