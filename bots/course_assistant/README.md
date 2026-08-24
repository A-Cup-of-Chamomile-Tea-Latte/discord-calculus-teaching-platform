# Course assistant

> **Fixture／歷史相容層，不是目前 production candidate。** 現行 Bot runtime 位於
> `runtime/discord-course-bots/`；本目錄保留 Task 22–25 的 pure domain、fake adapters 與舊契約回歸測試，
> 不應作為新功能或 production 設定的來源。

負責互動與寫入型操作，例如表單、回覆轉貼與一般案件協調。它不執行批次歷史匯出或自動教學分析。

唯一user-facing command owner。它可依核准流程使用`SEND_MESSAGES`、`SEND_MESSAGES_IN_THREADS`、`MANAGE_NICKNAMES`與allowlisted `MANAGE_ROLES`；不得使用`ADMINISTRATOR`或把email/Discord OAuth自行解讀為選課證明。Runtime只讀`COURSE_ASSISTANT_DISCORD_TOKEN`。

Task 22提供：

- `CourseAssistantDiscordApp`：discord.py `/health` command tree與不連線fixture/dry-run lifecycle；live start明確拒絕。
- `CourseAssistantService`：create case post、staff-only membership nickname/roles、staff-onlycase status/tag及Private Support hook delegation。
- Pure `generate_course_alias`與atomic repository port；fixture repository對同user/course/class重送相同joining order。
- `InteractionHookRegistry`：button/modal names與 Task 25 Private Support creation hook。

Task 24 新增：

- `AnonymousReplyView`/`AnonymousReplyModal`：綁定案件的 Discord button 會開啟 1–1800 字的私密 modal；不接收或刪除一般訊息。
- `CourseAssistantService.post_anonymous_reply()`：在開啟與送出階段都驗證 case owner，並清楚區分五位課程代號與完全匿名顯示。
- 公開 repost 只含安全顯示 label 與內容，mention parsing 必須關閉；submitter 只收到 ephemeral confirmation。
- Private audit sink 只保留 operation/case/internal actor/public message/display mode/timestamp，不保留 raw body或公開 Discord identity。

Task 25 新增：

- `PrivateSupportService`：獨立 case type/policy，支援 Portal 與 bot modal creation、owner/顯式 participants、teaching-team escalation、OPEN/ESCALATED/CLOSED status、retention review 與 closure hooks。
- `BACKEND_ONLY` 是唯一預設 representation；`PRIVATE_THREAD` 與 `RESTRICTED_CHANNEL` 只是可替換 port 的 enum，沒有被宣稱為已驗證的權限機制。
- Private record 沒有 public case number，固定 `TEACHING_STAFF` + `EXCLUDED`；central data policy 對 public lookup、analysis 與 content export 全部 deny。
- `PrivateSupportView`/`PrivateSupportModal` 只對已映射的 internal actor 開啟，成功只回 ephemeral confirmation，永不呼叫一般 Discord writer。
- `PRIVATE_SUPPORT_SPIKE.md` 列出 private thread/restricted channel 必做 test-guild 權限、失敗、可見性與清理測試；通過前不切換 representation。

所有Discord writes都透過`DiscordCourseWriter` narrow port；測試只使用`FakeDiscordClient`。沒有archive fetch、moderation或live adapter。
