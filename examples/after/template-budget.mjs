// A raw HTTP body limit does not cap template expansion. Budget before joining.
export function renderBudgeted(template, input, maxBytes = 32768) {
  if (typeof template !== "string" || typeof input !== "string" ||
      !Number.isSafeInteger(maxBytes) || maxBytes < 1) throw new TypeError("Invalid render budget");
  const parts = template.split("{{input}}");
  const bytes = parts.reduce((sum, part) => sum + Buffer.byteLength(part, "utf8"), 0)
    + (parts.length - 1) * Buffer.byteLength(input, "utf8");
  if (bytes > maxBytes) throw new RangeError("Rendered prompt exceeds byte budget");
  return parts.join(input);
}
