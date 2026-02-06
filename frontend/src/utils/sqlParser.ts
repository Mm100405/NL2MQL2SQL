/**
 * 简单的SQL解析器,用于将SQL转换为可视化画布
 */

export interface ParsedTable {
  name: string
  alias: string
  position?: { x: number; y: number }
}

export interface ParsedJoin {
  leftTable: string
  rightTable: string
  joinType: string
  conditions: Array<{
    left_column: string
    operator: string
    right_column: string
  }>
}

export interface ParsedSQL {
  tables: ParsedTable[]
  joins: ParsedJoin[]
  columns: string[]
  whereConditions?: Array<{
    column: string
    operator: string
    value: string
  }>
}

/**
 * 解析SQL语句
 */
export function parseSQL(sql: string): ParsedSQL | null {
  try {
    // 清理SQL
    const cleanSQL = sql
      .replace(/\n/g, ' ')
      .replace(/\s+/g, ' ')
      .trim()

    // 解析SELECT子句
    const selectMatch = cleanSQL.match(/SELECT\s+(.*?)\s+FROM/i)
    const columns = selectMatch 
      ? selectMatch[1].split(',').map(c => c.trim())
      : []

    // 解析FROM子句
    const fromMatch = cleanSQL.match(/FROM\s+(.*?)(?:\s+WHERE|\s+GROUP|\s+ORDER|\s+LIMIT|$)/i)
    if (!fromMatch) return null

    const fromClause = fromMatch[1]
    const tables: ParsedTable[] = []
    const joins: ParsedJoin[] = []

    // 解析第一个表
    const firstTableMatch = fromClause.match(/^(\w+)(?:\s+AS\s+)?(\w+)?/i)
    if (firstTableMatch) {
      tables.push({
        name: firstTableMatch[1],
        alias: firstTableMatch[2] || firstTableMatch[1],
        position: { x: 100, y: 100 }
      })
    }

    // 解析JOIN
    const joinRegex = /(INNER|LEFT|RIGHT|FULL|CROSS)?\s*JOIN\s+(\w+)(?:\s+AS\s+)?(\w+)?\s+ON\s+(.*?)(?=\s+(?:INNER|LEFT|RIGHT|FULL|CROSS)?\s*JOIN|\s+WHERE|\s+GROUP|\s+ORDER|\s+LIMIT|$)/gi
    let joinMatch

    let joinIndex = 0
    while ((joinMatch = joinRegex.exec(fromClause)) !== null) {
      const joinType = joinMatch[1]?.toUpperCase() || 'INNER'
      const tableName = joinMatch[2]
      const tableAlias = joinMatch[3] || tableName
      const onClause = joinMatch[4]

      tables.push({
        name: tableName,
        alias: tableAlias,
        position: { x: 100 + (joinIndex + 1) * 300, y: 100 }
      })

      // 解析ON条件
      const conditions: ParsedJoin['conditions'] = []
      const condParts = onClause.split(/\s+AND\s+/i)
      
      for (const part of condParts) {
        const condMatch = part.trim().match(/(\S+)\s*(=|!=|>|<|>=|<=)\s*(\S+)/)
        if (condMatch) {
          conditions.push({
            left_column: condMatch[1],
            operator: condMatch[2],
            right_column: condMatch[3]
          })
        }
      }

      joins.push({
        leftTable: tables[joinIndex].alias,
        rightTable: tableAlias,
        joinType,
        conditions
      })

      joinIndex++
    }

    // 解析WHERE条件
    const whereConditions: ParsedSQL['whereConditions'] = []
    const whereMatch = cleanSQL.match(/WHERE\s+(.*?)(?:\s+GROUP|\s+ORDER|\s+LIMIT|$)/i)
    if (whereMatch) {
      const whereParts = whereMatch[1].split(/\s+AND\s+/i)
      for (const part of whereParts) {
        // 处理 IS NULL / IS NOT NULL
        let condMatch = part.trim().match(/(\S+)\s+IS\s+(NOT\s+)?NULL/i)
        if (condMatch) {
          whereConditions.push({
            column: condMatch[1],
            operator: condMatch[2] ? 'IS NOT NULL' : 'IS NULL',
            value: ''
          })
          continue
        }

        // 处理其他操作符
        condMatch = part.trim().match(/(\S+)\s*(=|!=|>|<|>=|<=|LIKE|IN)\s*'?([^']*)'?/)
        if (condMatch) {
          whereConditions.push({
            column: condMatch[1],
            operator: condMatch[2],
            value: condMatch[3]
          })
        }
      }
    }

    return {
      tables,
      joins,
      columns,
      whereConditions
    }
  } catch (error) {
    console.error('Failed to parse SQL:', error)
    return null
  }
}

/**
 * 生成SQL语句
 */
export function generateSQL(
  tables: ParsedTable[],
  joins: ParsedJoin[],
  columns: string[],
  whereConditions?: Array<{ column: string; operator: string; value: string }>
): string {
  if (tables.length === 0) {
    return '-- 请添加表'
  }

  // SELECT子句
  const selectClause = columns.length > 0 ? columns.join(', ') : '*'

  // FROM子句
  let fromClause = `${tables[0].name} AS ${tables[0].alias}`

  // JOIN子句
  for (const join of joins) {
    const table = tables.find(t => t.alias === join.rightTable)
    if (table) {
      const onClause = join.conditions
        .map(c => `${c.left_column} ${c.operator} ${c.right_column}`)
        .join(' AND ')
      fromClause += `\n${join.joinType} JOIN ${table.name} AS ${table.alias} ON ${onClause}`
    }
  }

  let sql = `SELECT ${selectClause}\nFROM ${fromClause}`

  // WHERE子句
  if (whereConditions && whereConditions.length > 0) {
    const whereClause = whereConditions
      .map(w => {
        if (['IS NULL', 'IS NOT NULL'].includes(w.operator)) {
          return `${w.column} ${w.operator}`
        }
        return `${w.column} ${w.operator} '${w.value}'`
      })
      .join(' AND ')
    sql += `\nWHERE ${whereClause}`
  }

  return sql
}
