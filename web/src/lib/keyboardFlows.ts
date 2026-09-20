/** NFR-6: login, upload, and generate must be reachable from the keyboard. */

export const isActivateKey = (key: string): boolean => key === 'Enter' || key === ' '

export const LOGIN_FIELD_IDS = ['email', 'password'] as const
export const GENERATE_PROMPT_ID = 'research-prompt'
export const PAPER_OUTLINE_ID = 'paper-outline'
export const GENERATE_OUTLINE_BUTTON_ID = 'generate-outline'
export const GENERATE_PAPER_TYPE_ID = 'paper-type'
export const GENERATE_CITATION_STYLE_ID = 'citation-style'
export const GENERATE_OUTPUT_FORMAT_ID = 'output-format'
export const QUERY_SOURCES_BUTTON_ID = 'query-sources'
export const GENERATE_BUTTON_ID = 'generate-paper'
export const UPLOAD_ZONE_ROLE = 'button'
export const MAIN_CONTENT_ID = 'main-content'
export const SKIP_TO_CONTENT_HREF = `#${MAIN_CONTENT_ID}`
