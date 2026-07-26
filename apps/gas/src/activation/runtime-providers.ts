import type {
  ActivationLock,
  RandomBytesSource,
  Sha256Hash,
  Sha256Hasher,
} from "./contracts";

export class WebCryptoRandomSource implements RandomBytesSource {
  bytes(length: number): Uint8Array {
    if (!globalThis.crypto?.getRandomValues) {
      throw new Error("CRYPTOGRAPHIC_RANDOM_SOURCE_UNAVAILABLE");
    }
    const output = new Uint8Array(length);
    globalThis.crypto.getRandomValues(output);
    return output;
  }
}

export class GasSha256Hasher implements Sha256Hasher {
  hash(value: string): Sha256Hash {
    const digest = Utilities.computeDigest(
      Utilities.DigestAlgorithm.SHA_256,
      value,
      Utilities.Charset.UTF_8,
    );
    const hex = digest
      .map((byte) => ((byte + 256) % 256).toString(16).padStart(2, "0"))
      .join("");
    return `sha256:${hex}`;
  }
}

export class GasScriptLock implements ActivationLock {
  constructor(private readonly timeoutMilliseconds = 5000) {}

  runExclusive<T>(_key: string, operation: () => T): T {
    const lock = LockService.getScriptLock();
    if (!lock.tryLock(this.timeoutMilliseconds)) {
      throw new Error("ACTIVATION_LOCK_TIMEOUT");
    }
    try {
      return operation();
    } finally {
      lock.releaseLock();
    }
  }
}
