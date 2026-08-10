# 有效權限矩陣

> 由 `python -m tools.config_proposal generate` 自動產生。請修改 `config/proposed/`，不要直接編輯本檔。
> 只顯示 proposed fixture 的合併結果。

| 區域 | Student | Guest | Staff | course_assistant | dump_bot |
| --- | --- | --- | --- | --- | --- | --- |
| Math Questions | 允：VIEW、POST、REPLY<br>拒：MANAGE | 允：VIEW、POST、REPLY<br>拒：MANAGE | 允：VIEW、POST、REPLY、MANAGE<br>拒：— | 允：VIEW、POST、REPLY、MANAGE<br>拒：— | 允：VIEW、EXPORT<br>拒：POST、REPLY、MANAGE |
| Coursework / Systems | 允：VIEW、POST、REPLY<br>拒：MANAGE | 允：VIEW、POST、REPLY<br>拒：MANAGE | 允：VIEW、POST、REPLY、MANAGE<br>拒：— | 允：VIEW、POST、REPLY、MANAGE<br>拒：— | 允：VIEW、EXPORT<br>拒：POST、REPLY、MANAGE |
| Other Problem / Free Talk | 允：VIEW、POST、REPLY<br>拒：MANAGE | 允：VIEW、POST、REPLY<br>拒：MANAGE | 允：VIEW、POST、REPLY、MANAGE<br>拒：— | 允：VIEW、POST、REPLY、MANAGE<br>拒：— | 允：VIEW、EXPORT<br>拒：POST、REPLY、MANAGE |
| course-materials | 允：VIEW、POST、REPLY<br>拒：MANAGE | 允：VIEW、POST、REPLY<br>拒：MANAGE | 允：VIEW、POST、REPLY、MANAGE<br>拒：— | 允：VIEW、POST、REPLY、MANAGE<br>拒：— | 允：VIEW、EXPORT<br>拒：POST、REPLY、MANAGE |
| 中文聊天 | 允：VIEW、POST、REPLY、CREATE_THREAD<br>拒：MANAGE | 允：VIEW、POST、REPLY、CREATE_THREAD<br>拒：MANAGE | 允：VIEW、POST、REPLY、CREATE_THREAD、MANAGE<br>拒：— | 允：VIEW、POST、REPLY、CREATE_THREAD、MANAGE<br>拒：— | 繼承／未指定 |
| English Chat | 允：VIEW、POST、REPLY、CREATE_THREAD<br>拒：MANAGE | 允：VIEW、POST、REPLY、CREATE_THREAD<br>拒：MANAGE | 允：VIEW、POST、REPLY、CREATE_THREAD、MANAGE<br>拒：— | 允：VIEW、POST、REPLY、CREATE_THREAD、MANAGE<br>拒：— | 繼承／未指定 |
| private-case-template | 允：—<br>拒：VIEW、POST、REPLY、MANAGE | 允：—<br>拒：VIEW、POST、REPLY、MANAGE | 允：VIEW、POST、REPLY、MANAGE<br>拒：— | 允：VIEW、POST、REPLY、MANAGE<br>拒：— | 允：VIEW、EXPORT、MANAGE<br>拒：POST |
| 中文自習室 | 允：VIEW、CONNECT、SPEAK<br>拒：MANAGE | 允：VIEW、CONNECT、SPEAK<br>拒：MANAGE | 允：VIEW、CONNECT、SPEAK、MANAGE<br>拒：— | 繼承／未指定 | 繼承／未指定 |
| English Study Room | 允：VIEW、CONNECT、SPEAK<br>拒：MANAGE | 允：VIEW、CONNECT、SPEAK<br>拒：MANAGE | 允：VIEW、CONNECT、SPEAK、MANAGE<br>拒：— | 繼承／未指定 | 繼承／未指定 |
| system-log | 允：—<br>拒：VIEW、POST、REPLY、MANAGE | 允：—<br>拒：VIEW、POST、REPLY、MANAGE | 允：VIEW、POST、REPLY、MANAGE<br>拒：— | 允：VIEW、POST<br>拒：MANAGE | 允：VIEW、POST、EXPORT<br>拒：MANAGE |

`Administrator` 不得出現在任何 Bot 權限中。
