import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const brandAsset = (name: string) =>
  readFileSync(resolve(process.cwd(), 'public', 'brand', name), 'utf8')

const parseSvg = (source: string) =>
  new DOMParser().parseFromString(source, 'image/svg+xml').documentElement

describe('StayLong brand assets', () => {
  it.each([
    ['staylong-mark.svg', 'StayLong continuous home path mark'],
    ['staylong-lockup.svg', 'StayLong logo'],
    ['staylong-app-icon.svg', 'StayLong app icon'],
  ])('%s is an accessible, scalable SVG', (filename, title) => {
    const source = brandAsset(filename)
    const svg = parseSvg(source)

    expect(svg.tagName).toBe('svg')
    expect(svg.getAttribute('viewBox')).toBeTruthy()
    expect(svg.getAttribute('role')).toBe('img')
    expect(svg.querySelector('title')?.textContent).toBe(title)
  })

  it('uses the approved flat brand palette without visual effects', () => {
    const source = [
      brandAsset('staylong-mark.svg'),
      brandAsset('staylong-lockup.svg'),
      brandAsset('staylong-app-icon.svg'),
    ].join('\n')

    expect(source).toContain('#283018')
    expect(source).toContain('#71311D')
    expect(source).toContain('#E8DCC7')
    expect(source).not.toMatch(/<(filter|linearGradient|radialGradient|image)\b/)
  })

  it('keeps the exact product name in the horizontal lockup', () => {
    const lockup = parseSvg(brandAsset('staylong-lockup.svg'))

    expect(lockup.querySelector('text')?.textContent).toBe('StayLong')
  })
})
