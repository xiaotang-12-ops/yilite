export const PROJECT_CATEGORY_PENDING = 'pending'
export const PROJECT_CATEGORY_PUBLISHED = 'published'
export const PROJECT_CATEGORY_ARCHIVED = 'archived'

export const PROJECT_CATEGORY_VALUES = [
  PROJECT_CATEGORY_PENDING,
  PROJECT_CATEGORY_PUBLISHED,
  PROJECT_CATEGORY_ARCHIVED
] as const

export type ProjectCategory = (typeof PROJECT_CATEGORY_VALUES)[number]

export const DEFAULT_PROJECT_CATEGORY: ProjectCategory = PROJECT_CATEGORY_PENDING

export const PROJECT_CATEGORY_LABELS: Record<ProjectCategory, string> = {
  [PROJECT_CATEGORY_PENDING]: '待调整',
  [PROJECT_CATEGORY_PUBLISHED]: '已完成',
  [PROJECT_CATEGORY_ARCHIVED]: '旧版本'
}

export const PROJECT_CATEGORY_TAG_TYPES: Record<ProjectCategory, '' | 'success' | 'info' | 'warning'> = {
  [PROJECT_CATEGORY_PENDING]: 'warning',
  [PROJECT_CATEGORY_PUBLISHED]: 'success',
  [PROJECT_CATEGORY_ARCHIVED]: 'info'
}
