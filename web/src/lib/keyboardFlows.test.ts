import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import {
  GENERATE_BUTTON_ID,
  GENERATE_OUTLINE_BUTTON_ID,
  GENERATE_PROMPT_ID,
  LOGIN_FIELD_IDS,
  MAIN_CONTENT_ID,
  PAPER_OUTLINE_ID,
  SKIP_TO_CONTENT_HREF,
  UPLOAD_ZONE_ROLE,
  isActivateKey,
} from './keyboardFlows'

const readSrc = (relative: string): string =>
  readFileSync(join(__dirname, relative), 'utf8')

describe('keyboard primary flows (NFR-6)', () => {
  it('treats Enter and Space as activate keys for the upload zone', () => {
    expect(isActivateKey('Enter')).toBe(true)
    expect(isActivateKey(' ')).toBe(true)
    expect(isActivateKey('Tab')).toBe(false)
    expect(UPLOAD_ZONE_ROLE).toBe('button')
  })

  it('names labeled login fields and generate controls', () => {
    expect(LOGIN_FIELD_IDS).toEqual(['email', 'password'])
    expect(GENERATE_PROMPT_ID).toBe('research-prompt')
    expect(PAPER_OUTLINE_ID).toBe('paper-outline')
    expect(GENERATE_OUTLINE_BUTTON_ID).toBe('generate-outline')
    expect(GENERATE_BUTTON_ID).toBe('generate-paper')
    expect(SKIP_TO_CONTENT_HREF).toBe(`#${MAIN_CONTENT_ID}`)
  })

  it('wires those controls in login, upload, and generate UI', () => {
    const login = readSrc('../pages/Login.tsx')
    expect(login).toContain('htmlFor="email"')
    expect(login).toContain('htmlFor="password"')
    expect(login).toContain('type="submit"')

    const upload = readSrc('../components/UploadZone.tsx')
    expect(upload).toContain('isActivateKey')
    expect(upload).toContain('tabIndex={busy ? -1 : 0}')
    expect(upload).toContain('role={UPLOAD_ZONE_ROLE}')

    const generate = readSrc('../pages/Generate.tsx')
    expect(generate).toContain('htmlFor={GENERATE_PROMPT_ID}')
    expect(generate).toContain('id={PAPER_OUTLINE_ID}')
    expect(generate).toContain('id={GENERATE_OUTLINE_BUTTON_ID}')
    expect(generate).toContain('id={GENERATE_BUTTON_ID}')
    expect(generate).toContain('type="button"')

    const layout = readSrc('../components/Layout.tsx')
    expect(layout).toContain('Skip to main content')
    expect(layout).toContain('id={MAIN_CONTENT_ID}')
  })
})
