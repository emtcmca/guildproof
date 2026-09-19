type RetryableError = Error & {
  status?: number;
  code?: string;
  headers?: Record<string, string | string[]>;
};

interface RetryOptions {
  maxRetries?: number;
  baseDelayMs?: number;
  maxDelayMs?: number;
  backoffMultiplier?: number;
}

export function withRetry<T extends (...args: any[]) => Promise<any>>(
  fn: T,
  options: RetryOptions = {}
): T {
  const {
    maxRetries = 3,
    baseDelayMs = 100,
    maxDelayMs = 5000,
    backoffMultiplier = 2,
  } = options;

  return (async (...args: any[]) => {
    let lastError: RetryableError | null = null;

    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        return await fn(...args);
      } catch (err) {
        const error = err as RetryableError;
        lastError = error;

        if (attempt === maxRetries) break;

        // Determine if error is retryable
        const isRetryable = isTransientError(error.status, error.code);
        if (!isRetryable) throw error;

        // Calculate delay with exponential backoff
        let delayMs = baseDelayMs * Math.pow(backoffMultiplier, attempt);
        delayMs = Math.min(delayMs, maxDelayMs);

        // Respect Retry-After header if present
        if (error.headers) {
          const retryAfter = error.headers['retry-after'];
          if (retryAfter) {
            const seconds = parseInt(retryAfter as string, 10);
            if (!isNaN(seconds)) delayMs = seconds * 1000;
          }
        }

        await new Promise(resolve => setTimeout(resolve, delayMs));
      }
    }

    throw lastError;
  }) as T;
}

function isTransientError(status?: number, code?: string): boolean {
  const transientCodes = [
    'ECONNRESET',
    'ECONNREFUSED',
    'ETIMEDOUT',
    'EHOSTUNREACH',
    'ENETUNREACH',
    'ENOTFOUND',
  ];

  if (code && transientCodes.includes(code)) return true;

  // 5xx, 429 (rate limit), 408 (timeout)
  if (status && (status >= 500 || status === 429 || status === 408))
    return true;

  return false;
}