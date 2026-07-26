import type {
  ActivationAuditEvent,
  ActivationAuditSink,
  ActivationLock,
  ActivationRecord,
  ActivationRepository,
  RandomBytesSource,
  Sha256Hash,
} from "./contracts";

function cloneRecord(record: ActivationRecord): ActivationRecord {
  return {
    ...record,
    binding: { ...record.binding },
    permissionProfile: {
      ...record.permissionProfile,
      permissions: [...record.permissionProfile.permissions],
    },
  };
}

export class InMemoryActivationRepository implements ActivationRepository {
  private readonly records = new Map<string, ActivationRecord>();

  constructor(seed: ActivationRecord[] = []) {
    for (const record of seed) this.insert(record);
  }

  findById(activationCodeId: string): ActivationRecord | null {
    const record = this.records.get(activationCodeId);
    return record ? cloneRecord(record) : null;
  }

  findByVerifierHash(verifierHash: Sha256Hash): ActivationRecord | null {
    const record = [...this.records.values()].find(
      (candidate) => candidate.verifierHash === verifierHash,
    );
    return record ? cloneRecord(record) : null;
  }

  insert(record: ActivationRecord): void {
    if (this.records.has(record.activationCodeId)) {
      throw new Error("ACTIVATION_ID_COLLISION");
    }
    if (this.findByVerifierHash(record.verifierHash)) {
      throw new Error("ACTIVATION_VERIFIER_COLLISION");
    }
    this.records.set(record.activationCodeId, cloneRecord(record));
  }

  save(record: ActivationRecord): void {
    if (!this.records.has(record.activationCodeId)) {
      throw new Error("ACTIVATION_RECORD_NOT_FOUND");
    }
    this.records.set(record.activationCodeId, cloneRecord(record));
  }

  snapshot(): ActivationRecord[] {
    return [...this.records.values()].map(cloneRecord);
  }
}

export class InMemoryActivationLock implements ActivationLock {
  readonly keys: string[] = [];

  runExclusive<T>(key: string, operation: () => T): T {
    this.keys.push(key);
    return operation();
  }
}

export class MemoryActivationAuditSink implements ActivationAuditSink {
  readonly events: ActivationAuditEvent[] = [];

  record(event: ActivationAuditEvent): void {
    this.events.push({ ...event });
  }
}

export class SequenceRandomSource implements RandomBytesSource {
  private offset = 0;

  constructor(private readonly sequence: readonly number[]) {}

  bytes(length: number): Uint8Array {
    if (this.sequence.length === 0) {
      throw new Error("DETERMINISTIC_RANDOM_SEQUENCE_EMPTY");
    }
    const output = new Uint8Array(length);
    for (let index = 0; index < length; index += 1) {
      output[index] = this.sequence[this.offset % this.sequence.length] ?? 0;
      this.offset += 1;
    }
    return output;
  }
}
