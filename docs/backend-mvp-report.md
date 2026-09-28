# 本地后端 MVP 验证报告

日期：2026-09-25。遵循用户选择，只构建本地后端与浏览器试用入口，未安装 Flutter / Android 工具。

## 分阶段结果

| 阶段 | 结果 |
|---|---|
| Patient + SQLite 持久化、BMI、输入校验 | 5 passed |
| Disease Engine + 四种疾病接口 | 8 passed |
| Nutrition 单/双/三疾病合并与冲突来源 | 13 passed |
| Medication CRUD、状态、日期范围、历史快照 | 16 passed |
| Interaction 六类规则、别名与覆盖范围 | 22 passed |
| Observation 13 类指标、时区和 Care Plan | 26 passed |
| 本地文档、演示数据与幂等种子脚本 | 28 passed |

每阶段数字为该阶段全部累计测试数，均实际运行 pytest，通过后才进入下一阶段。存在一条第三方 Starlette TestClient 对 httpx 的弃用提示；未隐藏提示，不影响已验证的锁定依赖组合。

## 真实运行验证

- pip check：No broken requirements found。
- 实际启动 Uvicorn，仅监听 127.0.0.1:8000。
- GET /health：HTTP 200，{"status":"ok"}。
- 虚拟患者 ID：1。
- GET /patients/1/care-plan?foods=grapefruit&foods=high_sodium_food：4 个用药时刻、5 项营养约束、9 个时间线项；提醒覆盖全部 6 类。
- GET /docs：HTTP 200，使用本地 JS/CSS。
- 独立 scripts/smoke-test.ps1：临时 18765 端口，GET /health 通过并停止临时服务。
- Chrome 无头浏览器：试用首页加载成功、显示已连接和患者 ID；从首页进入 Swagger，点击 Try it out / Execute 执行 /health，返回 200。
- 浏览器测试阻止所有非本机网页请求，实际外部请求数 0，页面 JS 错误数 0。
- 已查看首页截图，无内容截断；截图保存于本目录 home-preview.png、swagger-preview.png。
- stop-backend.ps1 已实际停止本项目服务，确认 8000 不再监听，随后恢复服务供试用。

## 本地文件与持久化

数据库 data/health.db；规则 data/rules/*.json；药物/食物字典 data/drugs 和 data/foods；当前后台日志 .run/backend.stdout.log 与 .run/backend.stderr.log；进程信息 .run/backend.pid。数据库与日志不会进入版本控制。

本地运行不需要外部服务器，不调用 LLM 或云端数据库。首次安装 Python 依赖和下载 Swagger 开源资源需要网络；运行及浏览文档不需要。规则证据链接保留在 architecture.md 和 JSON 文件中。

## 限制和下一步

这是后端 MVP，不是完成的移动端。当前无登录系统、系统推送、完整药物知识库或临床验证；仅使用虚拟数据试用。用药计划是用户录入的每日固定时刻，规则不会自行改药。已记录饮食输入仅用于当次检查，不是饮食日记。数据库表结构变更尚未引入迁移工具。

下一阶段可在用户准备好 Flutter 环境后连接本后端，实现 Home / Diseases / Medications / Nutrition / Safety 页面。无需为开发立即购买云服务器。
