import rawRecords from "../../fixtures/case-api-records.json";

import type {
  CaseAuditEvent,
  CaseAuditSink,
  CaseRecord,
  CaseRepository,
  Clock,
  FollowUpProvider,
  FollowUpRequest,
  RefreshRequestProvider,
} from "./contracts";

export class FixtureCaseRepository implements CaseRepository {
  private readonly records: CaseRecord[];

  constructor(records: CaseRecord[] = rawRecords as CaseRecord[]) {
    this.records = records.map((record) => ({ ...record }));
  }

  findByCaseNumber(caseNumber: string): CaseRecord | null {
    const found = this.records.find(
      (record) => record.caseNumber === caseNumber,
    );
    return found ? { ...found } : null;
  }

  list(): CaseRecord[] {
    return this.records.map((record) => ({ ...record }));
  }
}

export class FixtureRefreshProvider implements RefreshRequestProvider {
  request(_caseNumber: string): "NO_OP" {
    return "NO_OP";
  }
}

export class FixtureFollowUpProvider implements FollowUpProvider {
  submit(_request: FollowUpRequest): "NOT_CONFIGURED" {
    return "NOT_CONFIGURED";
  }
}

export class MemoryCaseAuditSink implements CaseAuditSink {
  readonly events: CaseAuditEvent[] = [];

  record(event: CaseAuditEvent): void {
    this.events.push({ ...event });
  }
}

export class NoopCaseAuditSink implements CaseAuditSink {
  record(_event: CaseAuditEvent): void {}
}

export class SystemClock implements Clock {
  now(): string {
    return new Date().toISOString();
  }
}
