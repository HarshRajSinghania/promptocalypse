/**
 * Chat Failure Feedback & Latency Formatting — Issue #27:
 * Frontend UI Network Error & Latency Toast Banner.
 *
 * Pure helpers shared by ChatTerminal so the toast copy, retry policy and
 * RTT label stay deterministic and unit-testable.
 */

/** Exact toast copy for HTTP 429 responses. */
export const RATE_LIMIT_NOTICE =
  'Rate limit active: Please wait 3 seconds before resubmitting'

/** Exact toast copy for HTTP 502 / network / inference gateway failures. */
export const GATEWAY_FAILURE_NOTICE =
  'Inference gateway timeout. Your prompt score has not been penalized. Please retry.'

/** Existing 3-second submission cooldown (preserved Issue #7 behaviour). */
export const COOLDOWN_MS = 3000

/** How long a toast banner stays visible before auto-dismissing. */
export const NOTICE_DISMISS_MS = 5000

export type ChatFailureKind = 'rate_limit' | 'gateway'

export interface ChatFailureFeedback {
  kind: ChatFailureKind
  /** Exact toast/banner copy to display. */
  notice: string
  /**
   * true  → re-enable submission immediately so the user can retry (502/network).
   * false → keep submission disabled while rate limited (429, full 3s window).
   */
  reenableSubmission: boolean
}

/**
 * Classifies a failure raised while sending a prompt:
 * HTTP 429 (or any error tagged `rate_limit`) → 'rate_limit',
 * everything else (HTTP 502, network/transport failures) → 'gateway'.
 */
export function classifyChatFailure(error: unknown): ChatFailureKind {
  if (error && typeof error === 'object') {
    const candidate = error as { kind?: unknown; status?: unknown }
    if (candidate.kind === 'rate_limit' || candidate.status === 429) {
      return 'rate_limit'
    }
  }
  return 'gateway'
}

/** Resolves the exact toast copy and retry policy for a failed prompt send. */
export function feedbackForFailure(error: unknown): ChatFailureFeedback {
  const kind = classifyChatFailure(error)
  if (kind === 'rate_limit') {
    return { kind, notice: RATE_LIMIT_NOTICE, reenableSubmission: false }
  }
  return { kind, notice: GATEWAY_FAILURE_NOTICE, reenableSubmission: true }
}

/**
 * Formats a measured round-trip time for the terminal footer ("RTT 420ms").
 * Returns null when no latency was measured — never fabricates a value.
 */
export function formatRttLabel(
  latencyMs: number | null | undefined
): string | null {
  if (typeof latencyMs !== 'number' || !Number.isFinite(latencyMs)) {
    return null
  }
  return `RTT ${Math.round(latencyMs)}ms`
}
