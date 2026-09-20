import { DRAFT_DISCLAIMER, exportFileName, paperToMarkdown } from './exportPaper'

describe('exportPaper', () => {
  it('names files with a version suffix', () => {
    expect(exportFileName('My Review!', 2, 'md')).toBe('my-review-v2.md')
  })

  it('appends the human-review disclaimer', () => {
    const md = paperToMarkdown({ title: 'T', content: 'Hello' })
    expect(md).toContain('# T')
    expect(md).toContain('Hello')
    expect(md.trim().endsWith(DRAFT_DISCLAIMER)).toBe(true)
  })
})
