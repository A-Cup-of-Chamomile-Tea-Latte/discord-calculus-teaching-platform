# Case ID tool

本工具建立人類可操作、但不由姓名、學號、Email、Discord ID 或內部 UUID
推導的案件編號：

```text
C12-7K4M2Q-0907-2007
C12-7K4M2Q-0907-2007-P
C99-R8N6WX-0907-2007
Guest-R8N6WX-0907-2007
```

- `C01`～`C98` 是兩位班級代碼；Guest 公開案件使用 `Guest` 前綴，不使用 `C00`；`C99…-P` 保留給 Private Support。
- 六字元 token 使用 `secrets` 與排除 `0/O/1/I` 的字母表。
- 月日、時分以明確的課程時區 `Asia/Taipei` 產生，呼叫端必須傳入含時區時間。
- `-P` 只表示 Private Support；它不授予存取權，也不改變 Private 的權限政策。
- `CaseIdIssuer` 會對 public number 與 internal UUID 的碰撞作有上限的重試。
- `CaseIdMapping` 只應保存於受保護的 working store；public projection 不得輸出 internal UUID。

Production repository 的 `save` 必須以 transaction／unique constraint 原子保證
`caseNumber` 與 `internalCaseId` 唯一。現在提供的 in-memory repository 只供 fixture 與測試。
