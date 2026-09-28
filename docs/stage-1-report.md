# 第一阶段验证报告

## 环境检查

- python：D:\python.exe，Python 3.14.6；本阶段安装与运行验证通过。
- py：C:\windows\py.exe，Python 3.14.6。
- git：2.55.0.windows.3；满足当前版本管理需求。
- flutter：未在 PATH 中发现；Android/Flutter 阶段尚不具备已验证的开发环境。
- dart：未在 PATH 中发现。
- 未安装大型 SDK，未使用 WSL。Android SDK 本阶段未检查。
- 项目使用 .venv 独立环境；FastAPI 0.141.1、Uvicorn 0.53.0、Pydantic 2.13.5、pytest 9.1.1、httpx 0.28.1。完整依赖见 requirements-lock.txt。

## 验证结果

- pip check：No broken requirements found。
- scripts/test.ps1：2 passed，验证 /health 的状态码与 JSON，以及 OpenAPI 中存在 GET /health。
- 测试产生 1 条非阻断弃用提示：当前 Starlette TestClient 提示其 httpx 适配将弃用并建议 httpx2。现有已锁定组合测试通过，后续升级测试依赖时处理。
- scripts/smoke-test.ps1：启动真实 Uvicorn，GET http://127.0.0.1:18765/health 返回 HTTP 200，响应 {"status":"ok"}。
- smoke test 已停止其创建的临时服务器；目前没有保留运行服务。启动方式见 README。

## 创建内容

- README.md、.gitignore、requirements.txt、requirements-dev.txt、requirements-lock.txt、pytest.ini。
- backend/__init__.py、backend/app/__init__.py、backend/app/main.py。
- tests/test_health.py。
- scripts/start-backend.ps1、scripts/test.ps1、scripts/smoke-test.ps1。
- docs/architecture.md、docs/stage-1-report.md。
- mobile、core 的五个模块及 data 的四个目录均创建 .gitkeep 占位。
- .venv 为本地虚拟环境，已加入忽略列表。

## 下一阶段

建立 SQLAlchemy + SQLite 会话和 Patient 模型，补充 Pydantic 校验、创建和查询患者 API，并测试持久化、无效输入和不存在的患者。测试通过后再进入 Disease Engine。本阶段未提前实现业务模型、医学规则或 Flutter UI。
