#!/usr/bin/env node
/**
 * Literature-review UAT against nginx :8082 (not webpack :3001).
 * Waits: upload ceil(n/10)*120s+60s; generate 1260s; outline 180s.
 */
import { chromium } from 'playwright'
import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const ROOT = path.resolve(__dirname, '..')
const REPORTS = path.join(__dirname, 'reports')
const KEY_FILE = path.join(__dirname, '.uat-grok-key')
const PAPERS = path.join(__dirname, 'papers')
const BASE = process.env.UAT_BASE_URL || 'http://localhost:8082'
const MAILPIT = process.env.UAT_MAILPIT_URL || 'http://localhost:8026'
const PROMPT =
  'Synthesize a literature review of the gut-brain axis in Alzheimer’s disease from the uploaded papers only. Cover microbiome, inflammation, omega-3 fatty acids, and clinical-trial evidence. Cite only retrieved [S#] ids. Do not invent studies, n, or outcomes.'
const TITLE = 'Gut-brain axis in Alzheimer’s disease: a literature review'
const UAT_UPLOAD_WAIT_MS = (n) => Math.ceil(n / 10) * 120000 + 60000
const UAT_GENERATE_WAIT_MS = 1260000
const UAT_OUTLINE_WAIT_MS = 180000

fs.mkdirSync(REPORTS, { recursive: true })

function pdfs() {
  if (!fs.existsSync(PAPERS)) return []
  return fs.readdirSync(PAPERS).filter((f) => f.toLowerCase().endsWith('.pdf'))
}

function readKey() {
  if (!fs.existsSync(KEY_FILE)) return ''
  return fs.readFileSync(KEY_FILE, 'utf8').trim()
}

function looksLikePath(value) {
  const t = String(value || '').trim()
  return t.startsWith('/') || t.startsWith('./') || t.startsWith('../') || t.includes('\\')
}

async function confirmFromMailpit(email) {
  for (let i = 0; i < 30; i++) {
    const list = await fetch(`${MAILPIT}/api/v1/messages`).then((r) => r.json())
    const messages = list.messages || []
    for (const msg of messages) {
      const blob = JSON.stringify(msg)
      if (!blob.includes(email.split('@')[0])) continue
      const full = await fetch(`${MAILPIT}/api/v1/message/${msg.ID}`).then((r) => r.json())
      const text = JSON.stringify(full)
      const m = text.match(/http:\/\/localhost:8082\/api\/auth\/confirm\?token=[^"\\\s]+/)
      if (m) {
        await fetch(m[0])
        return
      }
    }
    await new Promise((r) => setTimeout(r, 500))
  }
  throw new Error('no confirm link in Mailpit')
}

const files = pdfs()
if (files.length < 1) {
  console.error('UAT BLOCKED: put literature PDFs in UAT/papers/')
  process.exit(1)
}
const key = readKey()
if (!key.startsWith('xai-') || looksLikePath(key)) {
  console.error('UAT FAIL: UAT/.uat-grok-key must be a live xai- secret, not a path')
  process.exit(1)
}

const browser = await chromium.launch({ headless: process.env.UAT_HEADED !== '1' })
const page = await browser.newPage()
const email = `uat-${Date.now()}@example.com`

try {
  await page.goto(BASE + '/login')
  await page.getByRole('button', { name: /create an account/i }).click()
  await page.locator('input').nth(0).fill('UAT Operator')
  await page.locator('input[type="email"]').fill(email)
  await page.locator('input[type="password"]').first().fill('correct-horse')
  await page.locator('input[type="password"]').nth(1).fill('correct-horse')
  await page.getByRole('button', { name: /sign up/i }).click()
  await page.waitForURL(/verify-email/)
  await confirmFromMailpit(email)
  await page.goto(BASE + '/login')
  await page.locator('input[type="email"]').fill(email)
  await page.locator('input[type="password"]').fill('correct-horse')
  await page.getByRole('button', { name: /sign in/i }).click()
  await page.waitForURL(/dashboard/)

  await page.goto(BASE + '/profile')
  await page.getByPlaceholder(/paste api key/i).nth(1).fill(key)
  await page.getByRole('button', { name: /save keys/i }).click()
  await page.getByText(/saved/i).first().waitFor({ timeout: 15000 })

  await page.goto(BASE + '/dashboard')
  const abs = files.map((f) => path.join(PAPERS, f))
  for (let i = 0; i < abs.length; i += 10) {
    const wave = abs.slice(i, i + 10)
    const input = page.locator('input[type="file"]').first()
    await input.setInputFiles(wave)
    await page.getByText(/indexed/i).first().waitFor({ timeout: UAT_UPLOAD_WAIT_MS(wave.length) })
  }

  await page.getByPlaceholder('Title').fill(TITLE)
  await page.locator('select').first().selectOption('Literature Review')
  await page.getByRole('button', { name: /start paper/i }).click()
  await page.waitForURL(/\/generate\//)
  await page.getByText('Literature Review', { exact: true }).waitFor()

  const prompt = page.locator('textarea')
  await prompt.fill(PROMPT)
  await page.getByRole('button', { name: /query sources/i }).click()
  await page.getByText(/retrieved passages/i).waitFor({ timeout: 120000 })
  const pin = page.getByRole('button', { name: /^pin$/i }).first()
  if (await pin.count()) await pin.click()

  await page.getByRole('link', { name: /interrogate/i }).click()
  await page.locator('textarea').fill('What evidence do these papers report about omega-3 and cognition?')
  await page.getByRole('button', { name: /^ask$/i }).click()
  await page.getByText(/^assistant$/i).waitFor({ timeout: 180000 })

  await page.getByRole('link', { name: /^prompt$/i }).click()
  await page.getByRole('button', { name: /generate outline/i }).click()
  await page.getByRole('heading', { name: /outline/i }).waitFor({ timeout: UAT_OUTLINE_WAIT_MS })
  await page.getByRole('button', { name: /generate draft/i }).click()
  await page.getByRole('heading', { name: /^draft$/i }).waitFor({ timeout: UAT_GENERATE_WAIT_MS })
  const draft = await page.locator('pre').last().innerText()
  if (!/AI-generated draft/i.test(await page.content())) {
    throw new Error('missing disclaimer')
  }
  if (/## References/i.test(draft) && /\.pdf/i.test(draft.split('References')[1] || '')) {
    console.warn('References may still contain filenames — inspect report')
  }

  const url = page.url()
  const id = url.split('/generate/')[1]?.split('/')[0]
  await page.goto(BASE + '/library')
  await page.getByRole('link', { name: /continue/i }).first().click()
  await page.waitForURL(/\/generate\//)
  const typeValue = await page.locator('select').first().inputValue()
  if (typeValue !== 'Literature Review') {
    throw new Error(`Continue restored ${typeValue}`)
  }
  console.log('UAT PASS', { files: files.length, paper: id })
} catch (err) {
  fs.writeFileSync(path.join(REPORTS, 'crash.log'), String(err && err.stack || err))
  console.error('UAT FAIL', err)
  process.exit(1)
} finally {
  await browser.close()
}
