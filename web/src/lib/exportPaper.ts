export const DRAFT_DISCLAIMER =
  'AI-generated draft. Requires human review. Citations must match your uploaded sources. This is not a factual-accuracy score.'

export type ExportPaperInput = {
  title: string
  content: string
  version?: number
}

export const exportFileStem = (title: string): string => {
  const stem = title
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 60)
  return stem || 'paper'
}

export const exportFileName = (title: string, version: number | undefined, ext: 'md' | 'docx'): string => {
  const ver = typeof version === 'number' && version > 0 ? `-v${version}` : ''
  return `${exportFileStem(title)}${ver}.${ext}`
}

export const paperToMarkdown = (
  paper: ExportPaperInput,
  extras?: { checks?: string; disclaimer?: string },
): string => {
  const title = paper.title.trim() || 'Untitled paper'
  const parts = [`# ${title}`, (paper.content ?? '').trim()]
  if (extras?.checks?.trim()) parts.push(extras.checks.trim())
  parts.push('---', extras?.disclaimer?.trim() || DRAFT_DISCLAIMER)
  return `${parts.filter((part) => part.length > 0).join('\n\n')}\n`
}

export const paperToDocxText = (
  paper: ExportPaperInput,
  extras?: { checks?: string; disclaimer?: string },
): string => paperToMarkdown(paper, extras)

export const downloadTextFile = (text: string, fileName: string, mime: string): void => {
  const blob = new Blob([text], { type: mime })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = fileName
  link.click()
  URL.revokeObjectURL(url)
}

export const checksExportBlock = (warnings: Array<{ message: string }>): string => {
  if (warnings.length === 0) return 'Checks: no citation, format, or uncited warnings.'
  return `Checks:\n${warnings.map((warning) => `- ${warning.message}`).join('\n')}`
}
