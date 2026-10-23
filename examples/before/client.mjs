// Deliberately flawed teaching fixture. Never use provider secrets in a browser.
export function createBrowserOptions(env) {
  return {
    apiKey: env.NEXT_PUBLIC_LLM_API_KEY,
    dangerouslyAllowBrowser: true,
  };
}
