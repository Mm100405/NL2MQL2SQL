/**
 * 安全工具函数 - 防止XSS攻击
 * 
 * 提供输入净化、验证和安全处理功能
 */

/**
 * 净化文本内容（移除所有HTML标签）
 * 用于处理API响应、用户输入等不可信数据
 */
export function sanitizeText(input: unknown): string {
  if (typeof input !== 'string') return ''
  
  // 移除HTML标签和危险字符
  return input
    .replace(/<[^>]*>/g, '') // 移除HTML标签
    .replace(/[<>]/g, '') // 移除尖括号
    .trim()
}

/**
 * 净化HTML内容（允许安全的HTML标签）
 * 用于需要显示HTML内容的场景
 */
export function sanitizeHTML(input: unknown): string {
  if (typeof input !== 'string') return ''
  
  // 使用白名单机制，只允许安全的标签
  const allowedTags = ['b', 'i', 'em', 'strong', 'a', 'p', 'br', 'ul', 'ol', 'li']
  const allowedAttrs = ['href', 'title']
  
  // 移除脚本标签和事件处理器
  let cleaned = input
    .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '')
    .replace(/on\w+\s*=\s*["'][^"']*["']/gi, '')
    .replace(/javascript:/gi, '')
  
  return cleaned
}

/**
 * 验证并净化URL
 * 只允许 http/https 协议
 */
export function sanitizeUrl(url: string): string {
  if (!url || typeof url !== 'string') return ''
  
  try {
    const parsed = new URL(url)
    if (['http:', 'https:'].includes(parsed.protocol)) {
      return parsed.href
    }
  } catch {
    // URL解析失败，返回空
  }
  
  return ''
}

/**
 * 验证颜色值格式
 * 支持十六进制颜色和命名颜色
 */
export function isValidColor(color: string): boolean {
  if (!color || typeof color !== 'string') return false
  
  // 十六进制颜色: #fff, #ffffff
  const hexPattern = /^#[0-9a-fA-F]{3,6}$/
  
  // 命名颜色: red, blue, etc.
  const namedColorPattern = /^[a-zA-Z]{3,20}$/
  
  // RGB/RGBA: rgb(255,0,0), rgba(255,0,0,0.5)
  const rgbaPattern = /^rgba?\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*(,\s*[\d.]+\s*)?\)$/
  
  return hexPattern.test(color) || 
         namedColorPattern.test(color) || 
         rgbaPattern.test(color)
}

/**
 * 净化CSS自定义属性值
 * 防止CSS注入攻击
 */
export function sanitizeCSSValue(value: string): string {
  if (!value || typeof value !== 'string') return ''
  
  // 移除危险字符和表达式
  return value
    .replace(/[<>]/g, '')
    .replace(/expression\(/gi, '')
    .replace(/javascript:/gi, '')
    .replace(/url\(/gi, '')
    .trim()
}

/**
 * 净化查询参数
 * 移除潜在危险字符
 */
export function sanitizeQueryParam(param: string, maxLength: number = 1000): string {
  if (!param || typeof param !== 'string') return ''
  
  return param
    .slice(0, maxLength) // 限制长度
    .replace(/[<>]/g, '') // 移除危险字符
    .replace(/[\r\n]/g, ' ') // 移除换行符
    .trim()
}

/**
 * 验证对象属性是否为安全字符串
 */
export function safeString(value: unknown, defaultValue: string = ''): string {
  if (typeof value === 'string') {
    return sanitizeText(value)
  }
  return defaultValue
}

/**
 * 批量净化对象中的字符串属性
 */
export function sanitizeObject<T extends Record<string, any>>(
  obj: T, 
  keys: (keyof T)[]
): T {
  const result = { ...obj }
  for (const key of keys) {
    if (result[key] !== undefined && result[key] !== null) {
      result[key] = sanitizeText(result[key]) as any
    }
  }
  return result
}
