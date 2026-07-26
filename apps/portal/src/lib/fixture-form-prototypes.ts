export type FixtureFormKind = "join" | "question" | "private-support";

export type FixtureFormValues = Record<string, string>;

export interface FixtureConfirmation {
  reference: string;
  title: string;
  publicLookup: boolean;
  persisted: false;
  summary: Array<{ label: string; value: string }>;
}

const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

const visibilityLabels: Record<string, string> = {
  CLASS: "班級可見",
  COURSE: "全課程可見",
  TEACHING_STAFF: "僅教學團隊可見",
};

const authorLabels: Record<string, string> = {
  REAL_NAME: "真實姓名",
  COURSE_ALIAS: "course alias",
  ANONYMOUS: "對一般成員匿名",
};

const analysisLabels: Record<string, string> = {
  INCLUDED: "Yes — 允許 AI 輔助教學分析",
  EXCLUDED: "No — 排除 AI 輔助教學分析",
};

function trimmed(values: FixtureFormValues, name: string): string {
  return (values[name] ?? "").trim();
}

function validateLength(
  errors: Record<string, string>,
  name: string,
  value: string,
  minimum: number,
  maximum: number,
  label: string,
): void {
  if (value.length < minimum) {
    errors[name] = `${label}可以再多寫一點（至少 ${minimum} 個字元）。`;
  } else if (value.length > maximum) {
    errors[name] = `${label}稍微太長了（最多 ${maximum} 個字元）。`;
  }
}

export function createAliasPreview(
  classCode: string,
  fixtureOrder = 42,
): string {
  if (!/^\d{2}$/.test(classCode) || fixtureOrder < 0 || fixtureOrder > 999) {
    return "尚未選擇班別";
  }
  return `${classCode}${String(fixtureOrder).padStart(3, "0")}`;
}

export function validateFixtureSubmission(
  kind: FixtureFormKind,
  values: FixtureFormValues,
): Record<string, string> {
  const errors: Record<string, string> = {};

  if (kind === "join") {
    const ntuEmail = trimmed(values, "ntuEmail").toLowerCase();
    const contactGmail = trimmed(values, "contactGmail").toLowerCase();
    if (!emailPattern.test(ntuEmail) || !ntuEmail.endsWith("@ntu.edu.tw")) {
      errors.ntuEmail = "請使用格式完整的 NTU email（結尾為 @ntu.edu.tw）。";
    }
    if (
      contactGmail &&
      (!emailPattern.test(contactGmail) || !contactGmail.endsWith("@gmail.com"))
    ) {
      errors.contactGmail =
        "若要填寫聯絡 Gmail，請使用結尾為 @gmail.com 的地址。";
    }
    if (!/^(01|02)$/.test(trimmed(values, "classCode"))) {
      errors.classCode = "請選擇 01 或 02 班；這只會產生 fixture alias 預覽。";
    }
    if (!/^(INCLUDED|EXCLUDED)$/.test(trimmed(values, "analysisPermission"))) {
      errors.analysisPermission = "請選擇是否允許教學分析；之後仍可更改。";
    }
    if (trimmed(values, "rulesPrivacy") !== "yes") {
      errors.rulesPrivacy =
        "請先確認已閱讀規則與隱私說明，再建立 fixture 預覽。";
    }
    return errors;
  }

  const title = trimmed(values, "title");
  const content = trimmed(values, "content");
  validateLength(errors, "title", title, 5, 160, "標題");
  validateLength(errors, "content", content, 20, 5000, "內容");

  if (kind === "question") {
    if (!(trimmed(values, "visibility") in visibilityLabels)) {
      errors.visibility = "請選擇班級、全課程或僅教學團隊可見。";
    }
    if (!(trimmed(values, "authorDisplayMode") in authorLabels)) {
      errors.authorDisplayMode = "請選擇姓名、course alias 或匿名顯示。";
    }
    if (!(trimmed(values, "analysisPermission") in analysisLabels)) {
      errors.analysisPermission =
        "請明確選擇 Yes 或 No；兩者都不影響是否獲得回覆。";
    }
    if (trimmed(values, "coolAcknowledgement") !== "yes") {
      errors.coolAcknowledgement =
        "請確認正式課務仍以 NTU COOL 為準；這不會限制你提出問題。";
    }
    if (trimmed(values, "attachmentName").length > 160) {
      errors.attachmentName = "附件名稱最多 160 個字元；此原型不會上傳檔案。";
    }
    return errors;
  }

  if (trimmed(values, "privacyAcknowledgement") !== "yes") {
    errors.privacyAcknowledgement =
      "請確認了解 Private Support 不會進入公開查詢，才能建立 fixture confirmation。";
  }
  if (trimmed(values, "analysisPermission") !== "EXCLUDED") {
    errors.analysisPermission = "Private Support 必須預設排除教學分析。";
  }
  return errors;
}

export function createFixtureConfirmation(
  kind: FixtureFormKind,
  values: FixtureFormValues,
): FixtureConfirmation {
  if (kind === "join") {
    return {
      reference: "FIXTURE-JOIN-001",
      title: "加入與設定 fixture 已建立",
      publicLookup: false,
      persisted: false,
      summary: [
        { label: "NTU email", value: trimmed(values, "ntuEmail") },
        {
          label: "聯絡 Gmail",
          value: trimmed(values, "contactGmail") || "未提供",
        },
        { label: "班別", value: trimmed(values, "classCode") },
        {
          label: "course alias 預覽",
          value: createAliasPreview(trimmed(values, "classCode")),
        },
        {
          label: "教學分析預設",
          value: analysisLabels[trimmed(values, "analysisPermission")],
        },
      ],
    };
  }

  if (kind === "question") {
    return {
      reference: "C01-N4Y7D2-0723-1030",
      title: "一般問題 fixture 已建立（未送出）",
      publicLookup: false,
      persisted: false,
      summary: [
        { label: "標題", value: trimmed(values, "title") },
        {
          label: "可見範圍",
          value: visibilityLabels[trimmed(values, "visibility")],
        },
        {
          label: "作者顯示",
          value: authorLabels[trimmed(values, "authorDisplayMode")],
        },
        {
          label: "OP 的 AI 分析決定（database fixture）",
          value: analysisLabels[trimmed(values, "analysisPermission")],
        },
        {
          label: "附件 metadata",
          value: trimmed(values, "attachmentName") || "未提供",
        },
      ],
    };
  }

  return {
    reference: "C99-F6Q2S8-0723-1031-P",
    title: "Private Support fixture 已建立（未送出）",
    publicLookup: false,
    persisted: false,
    summary: [
      { label: "主旨", value: trimmed(values, "title") },
      { label: "可見範圍", value: "僅授權教學團隊" },
      {
        label: "Private 案號",
        value: "C99-F6Q2S8-0723-1031-P（不可公開查詢）",
      },
      { label: "教學分析", value: "預設排除" },
    ],
  };
}
