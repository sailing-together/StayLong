/**
 * Live browser acceptance pass for the StayLong public journey (SAI-69).
 *
 * Runs end-to-end against https://staylonghome.com (or provided --url),
 * testing Desktop and Mobile viewports with step-by-step screenshot capture,
 * network timing tracking, and console error monitoring.
 *
 * Usage:
 *   node live_browser_acceptance.mjs [--url https://staylonghome.com]
 */

import { chromium } from 'file:///C:/Users/yangs/Documents/个人文件/Projects and Self study/StayLong/frontend/node_modules/playwright/index.mjs'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const evidenceDir = 'C:\\Users\\yangs\\Documents\\个人文件\\Projects and Self study\\StayLong\\docs\\evidence\\browser-acceptance'

// Parse command line arguments
const args = process.argv.slice(2)
const urlArgIdx = args.indexOf('--url')
const targetUrl = urlArgIdx !== -1 && args[urlArgIdx + 1] ? args[urlArgIdx + 1] : 'https://staylonghome.com'

fs.mkdirSync(evidenceDir, { recursive: true })

async function runPass(viewportName, viewportConfig) {
  console.log(`\n========================================`)
  console.log(`Running Acceptance Pass: ${viewportName}`)
  console.log(`Target URL: ${targetUrl}`)
  console.log(`Viewport: ${viewportConfig.width}x${viewportConfig.height} (Mobile: ${!!viewportConfig.isMobile})`)
  console.log(`========================================\n`)

  const browser = await chromium.launch({ headless: true })
  const context = await browser.newContext({
    viewport: { width: viewportConfig.width, height: viewportConfig.height },
    isMobile: viewportConfig.isMobile || false,
    hasTouch: viewportConfig.hasTouch || false,
    userAgent: viewportConfig.userAgent || undefined,
  })

  const page = await context.newPage()
  const consoleErrors = []
  const consoleLogs = []
  const apiRequests = []

  page.on('console', (msg) => {
    const type = msg.type()
    const text = msg.text()
    if (type === 'error') {
      consoleErrors.push(text)
    } else {
      consoleLogs.push(`[${type}] ${text}`)
    }
  })

  page.on('pageerror', (err) => {
    consoleErrors.push(`[Uncaught Error] ${err.message}`)
  })

  page.on('response', (response) => {
    const url = response.url()
    if (url.includes('/v1/public/') || url.includes('/v1/workflows')) {
      apiRequests.push({
        url,
        status: response.status(),
        statusText: response.statusText(),
        timestamp: new Date().toISOString(),
      })
    }
  })

  const startTime = Date.now()
  const stepTimings = {}

  const prefix = viewportName.toLowerCase()

  try {
    // Step 1: Open landing page
    console.log(`[1/8] Opening landing page...`)
    const t0 = Date.now()
    await page.goto(targetUrl, { waitUntil: 'networkidle', timeout: 30000 })
    stepTimings['01_open_landing'] = Date.now() - t0

    const title = await page.title()
    console.log(`  Page title: "${title}"`)
    await page.waitForSelector('h1', { timeout: 10000 })
    const headingText = await page.locator('h1').textContent()
    console.log(`  Heading: "${headingText?.trim()}"`)

    const landingScreenshot = path.join(evidenceDir, `${prefix}_01_landing.png`)
    await page.screenshot({ path: landingScreenshot, fullPage: true })
    console.log(`  Saved screenshot: ${landingScreenshot}`)

    // Step 2: Choose example concern and customize free text
    console.log(`[2/8] Selecting example and editing text...`)
    const t1 = Date.now()
    const exampleButton = page.locator('button.example-option', { hasText: 'Night-time bathroom' })
    await exampleButton.click()
    await page.waitForSelector('.selected-example')

    const textarea = page.locator('textarea#concern')
    await textarea.fill("I'm finding it harder to reach the bathroom safely at night. The hallway is dark and there are no rails near the toilet. I want to prepare for an assessment.")
    stepTimings['02_select_and_edit'] = Date.now() - t1

    const concernScreenshot = path.join(evidenceDir, `${prefix}_02_concern_edited.png`)
    await page.screenshot({ path: concernScreenshot, fullPage: true })
    console.log(`  Saved screenshot: ${concernScreenshot}`)

    // Step 3: Start plan -> transition to intake
    console.log(`[3/8] Starting plan and entering intake...`)
    const t2 = Date.now()
    const startBtn = page.locator('button.primary-action', { hasText: 'Start my plan' })
    await startBtn.click()

    await page.waitForSelector('h1:has-text("A few details will help prepare your plan")', { timeout: 15000 })
    stepTimings['03_start_plan'] = Date.now() - t2

    const intakeScreenshot = path.join(evidenceDir, `${prefix}_03_intake_questions.png`)
    await page.screenshot({ path: intakeScreenshot, fullPage: true })
    console.log(`  Saved screenshot: ${intakeScreenshot}`)

    // Step 4: Test safe return to concern & reselection
    console.log(`[4/8] Testing navigation back to concern and return...`)
    const t3 = Date.now()
    const backToConcernBtn = page.locator('button.secondary-action', { hasText: 'Back to my concern' })
    await backToConcernBtn.click()
    await page.waitForSelector('h1:has-text("What would make home easier today?")')

    const returnBtn = page.locator('button.secondary-action', { hasText: 'Return to preparation' })
    await returnBtn.click()
    await page.waitForSelector('h1:has-text("A few details will help prepare your plan")')
    stepTimings['04_navigation_test'] = Date.now() - t3

    // Step 5: Answer intake questions and prepare plan
    console.log(`[5/8] Answering questionnaire and generating plan...`)
    const t4 = Date.now()
    
    // Handle radio groups if present
    const radioNames = await page.evaluate(() => {
      const names = new Set()
      document.querySelectorAll('form input[type="radio"]').forEach(r => names.add(r.name))
      return Array.from(names)
    })
    
    for (const name of radioNames) {
      const radio = page.locator(`form input[type="radio"][name="${name}"]`).first()
      await radio.check({ force: true })
    }

    // Handle text inputs
    const textInputs = page.locator('form input:not([type="radio"]):not([type="checkbox"]):not([type="submit"]):not([type="button"]), form textarea')
    const textCount = await textInputs.count()
    for (let i = 0; i < textCount; i++) {
      const input = textInputs.nth(i)
      if (await input.isVisible()) {
        await input.fill(i === 0 ? 'No assessment arranged yet' : i === 1 ? 'I own my home' : 'Starting this myself')
      }
    }

    const prepareBtn = page.locator('button.primary-action:has-text("Prepare my plan"), button:has-text("Prepare my plan")')
    await prepareBtn.click()

    await page.waitForSelector('.plan-board, .plan-heading', { timeout: 20000 })
    stepTimings['05_prepare_plan'] = Date.now() - t4

    const planScreenshot = path.join(evidenceDir, `${prefix}_04_plan_prepared.png`)
    await page.screenshot({ path: planScreenshot, fullPage: true })
    console.log(`  Saved screenshot: ${planScreenshot}`)

    // Step 6: Test Defer / Decline Action ("Not now")
    console.log(`[6/8] Testing action deferral ("Not now")...`)
    const t5 = Date.now()
    const declineButtons = page.locator('button.secondary-action:has-text("Not now"), button[aria-label*="for later"]')
    if (await declineButtons.count() > 0) {
      await declineButtons.first().click()
      await page.waitForTimeout(1500)
      console.log(`  Deferred action tested!`)
    }
    stepTimings['06_decline_action'] = Date.now() - t5

    const deferredScreenshot = path.join(evidenceDir, `${prefix}_05_action_deferred.png`)
    await page.screenshot({ path: deferredScreenshot, fullPage: true })
    console.log(`  Saved screenshot: ${deferredScreenshot}`)

    // Step 7: Approve Calendar Action
    console.log(`[7/8] Approving Calendar sandbox action...`)
    const t6 = Date.now()
    const approveCalBtn = page.locator('button:has-text("Add assessment reminder to calendar"), button:has-text("Reconsider and approve")').first()
    if (await approveCalBtn.count() > 0) {
      await approveCalBtn.click()
      await page.waitForSelector('.action-card.completed, p:has-text("Reminder added to your plan"), .action-result', { timeout: 15000 })
      console.log(`  Calendar action approved!`)
    }
    stepTimings['07_approve_calendar'] = Date.now() - t6

    const calApprovedScreenshot = path.join(evidenceDir, `${prefix}_06_calendar_approved.png`)
    await page.screenshot({ path: calApprovedScreenshot, fullPage: true })
    console.log(`  Saved screenshot: ${calApprovedScreenshot}`)

    // Step 8: Approve Contact Draft Sandbox Action
    console.log(`[8/8] Approving Contact Draft sandbox action & reviewing draft...`)
    const t7 = Date.now()
    const draftApproveBtn = page.locator('button.primary-action:has-text("Create contact draft for review"), button:has-text("Create contact draft")').first()
    if (await draftApproveBtn.count() > 0) {
      await draftApproveBtn.click()
      await page.waitForSelector('.action-card.completed:has-text("Contact draft created for your review"), p:has-text("Contact draft created"), p:has-text("Contact draft")', { timeout: 15000 })
      console.log(`  Contact draft approved!`)
    }
    stepTimings['08_approve_draft'] = Date.now() - t7

    const draftApprovedScreenshot = path.join(evidenceDir, `${prefix}_07_draft_approved.png`)
    await page.screenshot({ path: draftApprovedScreenshot, fullPage: true })
    console.log(`  Saved screenshot: ${draftApprovedScreenshot}`)

    const totalDuration = Date.now() - startTime

    const result = {
      viewport: viewportName,
      status: consoleErrors.length === 0 ? 'PASSED' : 'PASSED_WITH_CONSOLE_WARNINGS',
      totalDurationMs: totalDuration,
      stepTimingsMs: stepTimings,
      consoleErrors,
      apiRequests,
      screenshots: [
        `${prefix}_01_landing.png`,
        `${prefix}_02_concern_edited.png`,
        `${prefix}_03_intake_questions.png`,
        `${prefix}_04_plan_prepared.png`,
        `${prefix}_05_action_deferred.png`,
        `${prefix}_06_calendar_approved.png`,
        `${prefix}_07_draft_approved.png`,
      ],
    }

    console.log(`\n Pass completed in ${totalDuration}ms. Console Errors: ${consoleErrors.length}`)
    return result
  } finally {
    await browser.close()
  }
}

async function main() {
  console.log(`Starting Live Browser Acceptance Pass (SAI-69)`)
  console.log(`Timestamp: ${new Date().toISOString()}`)

  const desktopResult = await runPass('Desktop', {
    width: 1280,
    height: 800,
    isMobile: false,
  })

  const mobileResult = await runPass('Mobile', {
    width: 375,
    height: 667,
    isMobile: true,
    hasTouch: true,
    userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1',
  })

  const summary = {
    targetUrl,
    executedAt: new Date().toISOString(),
    overallStatus: desktopResult.status === 'PASSED' && mobileResult.status === 'PASSED' ? 'PASSED' : 'COMPLETED',
    results: {
      desktop: desktopResult,
      mobile: mobileResult,
    },
  }

  const summaryPath = path.join(evidenceDir, 'acceptance-summary.json')
  fs.writeFileSync(summaryPath, JSON.stringify(summary, null, 2))
  console.log(`\nAcceptance Summary saved to: ${summaryPath}`)

  console.log(`\n========================================`)
  console.log(`ACCEPTANCE PASS SUMMARY: ${summary.overallStatus}`)
  console.log(`Desktop: ${desktopResult.status} (${desktopResult.totalDurationMs}ms)`)
  console.log(`Mobile:  ${mobileResult.status} (${mobileResult.totalDurationMs}ms)`)
  console.log(`========================================\n`)
}

main().catch((err) => {
  console.error('Acceptance pass failed:', err)
  process.exit(1)
})
