/**
 * Tests for Issue #27 chat feedback helpers —
 * toast copy, retry policy (submit re-enabled / blocked) and RTT label.
 */

import { describe, it } from 'node:test'
import assert from 'node:assert/strict'

import {
  COOLDOWN_MS,
  GATEWAY_FAILURE_NOTICE,
  RATE_LIMIT_NOTICE,
  classifyChatFailure,
  feedbackForFailure,
  formatRttLabel,
} from './chatFeedback.ts'

describe('Issue #27 toast copy', () => {
  it('uses the exact HTTP 429 rate limit message', () => {
    assert.equal(
      RATE_LIMIT_NOTICE,
      'Rate limit active: Please wait 3 seconds before resubmitting'
    )
  })

  it('uses the exact HTTP 502 / network gateway message', () => {
    assert.equal(
      GATEWAY_FAILURE_NOTICE,
      'Inference gateway timeout. Your prompt score has not been penalized. Please retry.'
    )
  })

  it('returns that exact copy for both failure kinds', () => {
    assert.equal(
      feedbackForFailure({ status: 429 }).notice,
      'Rate limit active: Please wait 3 seconds before resubmitting'
    )
    assert.equal(
      feedbackForFailure({ status: 502 }).notice,
      'Inference gateway timeout. Your prompt score has not been penalized. Please retry.'
    )
  })
})

describe('classifyChatFailure', () => {
  it('classifies status 429 errors as rate_limit', () => {
    assert.equal(classifyChatFailure({ status: 429 }), 'rate_limit')
  })

  it('classifies errors tagged kind=rate_limit as rate_limit', () => {
    assert.equal(
      classifyChatFailure({ kind: 'rate_limit', status: 429 }),
      'rate_limit'
    )
  })

  it('classifies HTTP 502 errors as gateway', () => {
    assert.equal(classifyChatFailure({ status: 502 }), 'gateway')
  })

  it('classifies network/transport failures as gateway', () => {
    assert.equal(classifyChatFailure(new TypeError('fetch failed')), 'gateway')
    assert.equal(classifyChatFailure(new Error('socket hang up')), 'gateway')
    assert.equal(classifyChatFailure(undefined), 'gateway')
  })
})

describe('submission retry policy', () => {
  it('keeps submission disabled while the request is rate limited', () => {
    const feedback = feedbackForFailure({ status: 429 })
    assert.equal(feedback.kind, 'rate_limit')
    assert.equal(feedback.reenableSubmission, false)
  })

  it('re-enables submission after a 502 gateway failure', () => {
    const feedback = feedbackForFailure({ status: 502 })
    assert.equal(feedback.kind, 'gateway')
    assert.equal(feedback.reenableSubmission, true)
  })

  it('re-enables submission after a network failure', () => {
    const feedback = feedbackForFailure(new TypeError('fetch failed'))
    assert.equal(feedback.kind, 'gateway')
    assert.equal(feedback.reenableSubmission, true)
  })

  it('preserves the existing 3-second cooldown window', () => {
    assert.equal(COOLDOWN_MS, 3000)
  })
})

describe('formatRttLabel', () => {
  it('formats measured latency for the terminal footer', () => {
    assert.equal(formatRttLabel(420), 'RTT 420ms')
    assert.equal(formatRttLabel(420.6), 'RTT 421ms')
    assert.equal(formatRttLabel(0), 'RTT 0ms')
  })

  it('never fabricates a latency value', () => {
    assert.equal(formatRttLabel(null), null)
    assert.equal(formatRttLabel(undefined), null)
    assert.equal(formatRttLabel(NaN), null)
    assert.equal(formatRttLabel(Number.POSITIVE_INFINITY), null)
  })
})
