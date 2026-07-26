import {
  FixtureCaseRepository,
  FixtureFollowUpProvider,
  FixtureRefreshProvider,
  NoopCaseAuditSink,
  SystemClock,
} from "./fixture-providers";
import { CaseService } from "./service";

export const fixtureCaseService = new CaseService({
  repository: new FixtureCaseRepository(),
  refreshProvider: new FixtureRefreshProvider(),
  followUpProvider: new FixtureFollowUpProvider(),
  auditSink: new NoopCaseAuditSink(),
  clock: new SystemClock(),
});
