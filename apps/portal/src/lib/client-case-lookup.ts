import type { LookupResult, PublicCaseView } from "./case-adapter";
import { isCaseNumberWellFormed, normalizeCaseNumber } from "./case-adapter";

export function lookupPublicCase(
  cases: PublicCaseView[],
  value: string,
): LookupResult {
  const normalizedCaseNumber = normalizeCaseNumber(value);
  if (!isCaseNumberWellFormed(normalizedCaseNumber)) {
    return { outcome: "INVALID", normalizedCaseNumber, case: null };
  }
  const found = cases.find((item) => item.caseNumber === normalizedCaseNumber);
  if (!found) return { outcome: "NOT_FOUND", normalizedCaseNumber, case: null };
  return { outcome: "FOUND", normalizedCaseNumber, case: found };
}
