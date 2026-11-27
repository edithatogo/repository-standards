function sanitizeContext(value: string): string { return value; }

async function unsafeSend(req: { body: string }) {
  await fetch("https://invalid.example", { method: "POST", body: sanitizeContext(req.body) });
}
