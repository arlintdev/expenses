/**
 * Custom error class for fetch timeout errors
 */
export class FetchTimeoutError extends Error {
  constructor(message, timeout) {
    super(message);
    this.name = 'FetchTimeoutError';
    this.timeout = timeout;
  }
}

/**
 * Fetch with timeout support using AbortController
 *
 * @param {string} url - The URL to fetch
 * @param {object} options - Standard fetch options
 * @param {number} timeoutMs - Timeout in milliseconds (default: 15000)
 * @returns {Promise<Response>} - Fetch response
 * @throws {FetchTimeoutError} - If request times out
 */
export async function fetchWithTimeout(url, options = {}, timeoutMs = 15000) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal
    });
    clearTimeout(timeoutId);
    return response;
  } catch (error) {
    clearTimeout(timeoutId);
    if (error.name === 'AbortError') {
      throw new FetchTimeoutError(`Request timeout after ${timeoutMs}ms`, timeoutMs);
    }
    throw error;
  }
}
