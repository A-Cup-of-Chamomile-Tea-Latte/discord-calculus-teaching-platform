export type LocalRole = "staff" | "admin";

export interface LocalAccount {
  accountHash: string;
  role: LocalRole;
  passwordSalt: string;
  passwordVerifier: string;
  iterations: number;
  mustChangePassword: boolean;
}

export interface LocalAccessStore {
  version: 1;
  accountLookupSalt: string;
  accounts: LocalAccount[];
}

export interface LocalAccessSession {
  accountHash: string;
  role: LocalRole;
  expiresAt: number;
}

export const LOCAL_ACCESS_STORE_KEY = "calculus-local-access-v1";
export const LOCAL_ACCESS_SESSION_KEY = "calculus-local-session-v1";
export const PBKDF2_ITERATIONS = 600_000;
export const SESSION_DURATION_MS = 8 * 60 * 60 * 1000;

const encoder = new TextEncoder();

function bytesToBase64(bytes: Uint8Array): string {
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary);
}

function base64ToBytes(value: string): Uint8Array<ArrayBuffer> {
  const binary = atob(value);
  const bytes = new Uint8Array(new ArrayBuffer(binary.length));
  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }
  return bytes;
}

function randomBase64(length: number): string {
  return bytesToBase64(crypto.getRandomValues(new Uint8Array(length)));
}

function equalBytes(left: Uint8Array, right: Uint8Array): boolean {
  if (left.length !== right.length) return false;
  let difference = 0;
  for (let index = 0; index < left.length; index += 1) {
    difference |= left[index]! ^ right[index]!;
  }
  return difference === 0;
}

export function normalizeAccountId(accountId: string): string {
  return accountId.trim().toLowerCase();
}

export function createEmptyAccessStore(): LocalAccessStore {
  return {
    version: 1,
    accountLookupSalt: randomBase64(16),
    accounts: [],
  };
}

export async function hashAccountId(
  accountId: string,
  lookupSalt: string,
): Promise<string> {
  const digest = await crypto.subtle.digest(
    "SHA-256",
    encoder.encode(`${lookupSalt}:${normalizeAccountId(accountId)}`),
  );
  return bytesToBase64(new Uint8Array(digest));
}

async function derivePasswordVerifier(
  password: string,
  salt: string,
  iterations: number,
): Promise<string> {
  const material = await crypto.subtle.importKey(
    "raw",
    encoder.encode(password),
    "PBKDF2",
    false,
    ["deriveBits"],
  );
  const derived = await crypto.subtle.deriveBits(
    {
      name: "PBKDF2",
      hash: "SHA-256",
      salt: base64ToBytes(salt),
      iterations,
    },
    material,
    256,
  );
  return bytesToBase64(new Uint8Array(derived));
}

export function passwordPolicyError(
  password: string,
  accountId: string,
): string | null {
  if (password.length < 6) return "密碼至少需要 6 個字元。";
  if (password.length > 128) return "新密碼不可超過 128 個字元。";
  if (password === accountId || password === normalizeAccountId(accountId)) {
    return "新密碼不可與帳號相同。";
  }
  return null;
}

export async function createLocalAccount(
  accountId: string,
  role: LocalRole,
  lookupSalt: string,
  options: {
    password?: string;
    mustChangePassword?: boolean;
    iterations?: number;
  } = {},
): Promise<LocalAccount> {
  const normalized = normalizeAccountId(accountId);
  if (!normalized) throw new Error("ACCOUNT_ID_REQUIRED");
  const password = options.password ?? normalized;
  const passwordSalt = randomBase64(16);
  const iterations = options.iterations ?? PBKDF2_ITERATIONS;
  return {
    accountHash: await hashAccountId(normalized, lookupSalt),
    role,
    passwordSalt,
    passwordVerifier: await derivePasswordVerifier(
      password,
      passwordSalt,
      iterations,
    ),
    iterations,
    mustChangePassword: options.mustChangePassword ?? true,
  };
}

export async function verifyLocalAccount(
  account: LocalAccount,
  password: string,
): Promise<boolean> {
  const candidate = await derivePasswordVerifier(
    password,
    account.passwordSalt,
    account.iterations,
  );
  return equalBytes(
    base64ToBytes(candidate),
    base64ToBytes(account.passwordVerifier),
  );
}

export async function replaceLocalPassword(
  account: LocalAccount,
  password: string,
  iterations = PBKDF2_ITERATIONS,
): Promise<LocalAccount> {
  const passwordSalt = randomBase64(16);
  return {
    ...account,
    passwordSalt,
    passwordVerifier: await derivePasswordVerifier(
      password,
      passwordSalt,
      iterations,
    ),
    iterations,
    mustChangePassword: false,
  };
}

export function validSession(
  value: unknown,
  now = Date.now(),
): value is LocalAccessSession {
  if (!value || typeof value !== "object") return false;
  const session = value as Partial<LocalAccessSession>;
  return (
    typeof session.accountHash === "string" &&
    (session.role === "staff" || session.role === "admin") &&
    typeof session.expiresAt === "number" &&
    session.expiresAt > now
  );
}

export function roleAllows(
  role: LocalRole | "guest",
  requiredRole: LocalRole,
): boolean {
  return role === "admin" || role === requiredRole;
}
