import test from "node:test";
import assert from "node:assert/strict";
import net from "node:net";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { sanitizeViaSocket } from "./dlp-client.mjs";

async function withServer(reply, testFn) {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "dlp-node-"));
  const sock = path.join(tmp, "dlp.sock");
  const server = net.createServer(conn => conn.on("data", () => conn.end(reply)));
  await new Promise(resolve => server.listen(sock, resolve));
  try { await testFn(sock); }
  finally {
    await new Promise(resolve => server.close(resolve));
    fs.rmSync(tmp, { recursive: true, force: true });
  }
}

test("returns only sanitized broker result", async () => {
  await withServer('{"ok":true,"payload":"[REDACTED]"}\n', async sock => {
    assert.equal(await sanitizeViaSocket("CANARY-ABCDEFGH", { socketPath: sock }), "[REDACTED]");
  });
});

test("broker rejection is generic", async () => {
  await withServer('{"ok":false,"error":"secret"}\n', async sock => {
    await assert.rejects(sanitizeViaSocket("CANARY-ABCDEFGH", { socketPath: sock }), /DLP_REJECTED/);
  });
});

test("missing broker rejects without raw payload", async () => {
  await assert.rejects(sanitizeViaSocket("CANARY-ABCDEFGH", { socketPath: "/tmp/uninstalled-dlp-test.sock" }),
    error => error.message === "DLP_REJECTED");
});

test("invalid JSON payload rejected", async () => {
  await assert.rejects(sanitizeViaSocket({ unsafe: NaN }), /DLP_REJECTED/);
});

test("socket route must be local path", async () => {
  await assert.rejects(sanitizeViaSocket("x", { socketPath: "https://invalid.example" }), /DLP_REJECTED/);
});
