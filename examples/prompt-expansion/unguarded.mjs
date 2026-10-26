// Minimal reproduction of PromptCanary's renderer at db53b8ecf071a8a16ef70b3f7b10fe17bf53be13.
// Source: https://github.com/mioyui20/prompt-canary/blob/db53b8ecf071a8a16ef70b3f7b10fe17bf53be13/public/core.js#L132-L135
// MIT, Copyright (c) 2026 mioyui20; see the repository LICENSE.
// Deliberately unguarded teaching fixture. Never connect this to a real provider.
export function renderPrompt(template, input) {
  return template.replaceAll("{{input}}", () => input);
}
