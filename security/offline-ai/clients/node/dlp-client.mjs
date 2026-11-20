/** Offline Unix-domain-socket DLP client: no HTTP, DNS or cloud API calls. */
import { createConnection } from "node:net";
import { Buffer } from "node:buffer";

const ERROR = "DLP_REJECTED";
const MAX_BYTES = 1024 * 1024;

export function sanitizeViaSocket(payload, { socketPath = "/run/offline-dlp/dlp.sock", timeoutMs = 5000 } = {}) {
  if (typeof socketPath !== "string" || !socketPath.startsWith("/") || !Number.isFinite(timeoutMs) || timeoutMs <= 0) {
    return Promise.reject(new Error(ERROR));
  }
  let message;
  try {
    message = JSON.stringify({ payload }, (_, value) => {
      if (typeof value === "function" || typeof value === "undefined" ||
          (typeof value === "number" && !Number.isFinite(value))) throw new Error(ERROR);
      return value;
    });
    if (!message || Buffer.byteLength(message) + 1 > MAX_BYTES) throw new Error(ERROR);
  } catch {
    return Promise.reject(new Error(ERROR));
  }
  return new Promise((resolve, reject) => {
    const conn = createConnection({ path: socketPath });
    let completed = false;
    let buffer = Buffer.alloc(0);
    const fail = () => {
      if (completed) return;
      completed = true;
      conn.destroy();
      reject(new Error(ERROR));
    };
    conn.setTimeout(timeoutMs);
    conn.on("error", fail);
    conn.on("timeout", fail);
    conn.on("end", fail);
    conn.on("connect", () => conn.write(message + "\n"));
    conn.on("data", part => {
      if (completed) return;
      buffer = Buffer.concat([buffer, part]);
      if (buffer.length > MAX_BYTES) return fail();
      const nl = buffer.indexOf(10);
      if (nl === -1) return;
      try {
        if (nl !== buffer.length - 1) throw new Error(ERROR);
        const reply = JSON.parse(buffer.subarray(0, nl).toString("utf8"));
        if (!reply || reply.ok !== true || !Object.hasOwn(reply, "payload")) throw new Error(ERROR);
        completed = true;
        conn.destroy();
        resolve(reply.payload);
      } catch { fail(); }
    });
  });
}
