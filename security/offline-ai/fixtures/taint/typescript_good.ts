async function benignSend() {
  await fetch("https://invalid.example", { method: "POST", body: "nonsensitive" });
}
