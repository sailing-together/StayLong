import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const appStyles = () => readFileSync(resolve(process.cwd(), 'src', 'App.css'), 'utf8')
const baseStyles = () => readFileSync(resolve(process.cwd(), 'src', 'index.css'), 'utf8')

describe('StayLong cinnamon theme', () => {
  it('makes cinnamon pink the dominant panel colour while retaining ivory space', () => {
    const source = appStyles()

    expect(source).toContain('--sand: #f5f2eb')
    expect(source).toContain('--sage: #d19895')
    expect(source).toContain('--clay: #d19895')
    expect(baseStyles()).toContain('background: #f5f2eb')
  })
})
