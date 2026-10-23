// Teaching fixture: a route with no caller, body, quota or lifecycle boundary.
// The tests inject a local stub; no real SDK or provider is used.
export async function handleChat(request, { client }) {
  const { prompt } = await request.json();
  const result = await client.chat.completions.create({
    model: "fixture-model",
    messages: [{ role: "user", content: prompt }],
  });
  // Parseable JSON is not a validated result shape.
  return Response.json(JSON.parse(result.choices[0].message.content));
}
