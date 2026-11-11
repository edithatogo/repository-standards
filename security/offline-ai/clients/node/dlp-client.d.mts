export declare function sanitizeViaSocket<T = unknown>(
  payload: unknown,
  options?: { socketPath?: string; timeoutMs?: number }
): Promise<T>;
