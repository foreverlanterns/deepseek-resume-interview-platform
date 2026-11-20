# 智能简历诊断与面试模拟平台

毕业设计课题：**基于DeepSeek的智能简历诊断与面试模拟平台设计与实现**。

代码仓库：<https://github.com/foreverlanterns/deepseek-resume-interview-platform>

## 当前状态

- 阶段 0：需求分析、项目计划书、开题报告已完成。
- 阶段 1：工程骨架已完成。后端具备 FastAPI 应用工厂、环境变量配置、PostgreSQL 连接、Alembic、健康检查与测试；前端具备 Vue 3 + TypeScript + Vite、路由、Pinia、Element Plus 与 Axios 请求封装。
- 阶段 2：用户注册 / 登录已完成。Argon2 密码哈希、JWT、`/auth/me`、前端登录注册页与路由守卫均已跑通；数据库已建库并执行迁移。
- 阶段 3a：简历上传与文本提取已完成。支持 PDF/DOCX 校验、UUID 隔离存储、PyMuPDF / python-docx 文本提取、用户级列表与删除；图片与 OCR 留待后续阶段。
- 阶段 3b：结构化抽取与人工校正已完成。DeepSeek Provider（JSON mode、thinking disabled、重试）、`resume_versions` 版本表、解析/校正接口、前端分区编辑页；真实 API 解析与校正已验证。
- 阶段 4：JD 管理与四维诊断已完成。JD CRUD、格式/完整度/关键词规则评分、DeepSeek JD 匹配证据、事实约束修改示例、ECharts 雷达图与诊断历史；真实诊断链路已跑通。
- 阶段 5：模拟面试已完成。简历与岗位驱动出题、题目来源核实、五维逐题评价、两级追问、提前结束、复盘报告与面试历史；真实面试链路已跑通。
- 阶段 6：成长分析已完成。按简历、岗位、面试类型与 `rubric_version` 分组聚合诊断与面试趋势，输出平均/最高/首末变化、缺失关键词、未满足要求与五维弱项。
- 阶段 7：容器化部署已完成并实机验证。`db` / `api` / `web` 三容器健康，迁移、上传卷与经 Nginx 的注册/上传链路通过；部署说明、测试报告、架构图、演示脚本与关键页面截图已完成。
- 代码按功能模块逐个推进，**进度、验收结果与待确认事项统一记录在 [`docs/开发同步记录.md`](docs/开发同步记录.md)**。

## 目录

```text
backend/           FastAPI 后端
  app/
    api/           路由与依赖
    core/          配置、日志
    db/            SQLAlchemy 基类与会话
    models/        ORM 模型（随功能加入）
    schemas/       Pydantic 模型
    services/      业务服务
  alembic/         数据库迁移
  tests/           Pytest 测试
frontend/          Vue 3 + TypeScript 前端
  src/
    api/           Axios 封装与接口
    router/        Vue Router 与路由守卫
    stores/        Pinia（健康状态、认证）
    utils/         Token 存储等工具
    views/         页面（工作台、登录 / 注册）
    types/         接口类型
docs/              项目文档与开发同步记录
reference/         只读参考源码（不纳入版本库）
```

## 快速开始

### 1. 后端

```bash
cd backend
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements-dev.txt
# 若 backend/.env 不存在，从 .env.example 复制，并把 DATABASE_URL 中的 CHANGE_ME 换成真实密码
.venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8000
```

> 当前 `backend/.env` 已配置本地数据库与随机 `SECRET_KEY`；换机器时按 `docs/开发同步记录.md` 第 9 节创建数据库并修改连接串。

- 健康检查：<http://127.0.0.1:8000/api/v1/health>
- 接口文档：<http://127.0.0.1:8000/docs>
- 认证接口：`POST /api/v1/auth/register`、`POST /api/v1/auth/login`、`GET /api/v1/auth/me`
- 简历接口：`POST /api/v1/resumes/upload`、`GET /api/v1/resumes`、`GET /api/v1/resumes/{id}`、`DELETE /api/v1/resumes/{id}`
- 结构化接口：`POST /api/v1/resumes/{id}/parse`、`GET /api/v1/resumes/{id}/versions`、`POST /api/v1/resumes/{id}/versions/{version_no}/corrections`
- JD 与诊断：`GET/POST /api/v1/jds`、`PUT/DELETE /api/v1/jds/{id}`、`POST /api/v1/diagnoses`、`GET /api/v1/diagnoses`、`GET /api/v1/diagnoses/{id}`
- 模拟面试：`POST/GET /api/v1/interviews`、`GET /api/v1/interviews/{id}`、`POST /api/v1/interviews/{id}/questions/{question_id}/answer`、`POST /api/v1/interviews/{id}/finish`、`POST /api/v1/interviews/{id}/report`
- 成长分析：`GET /api/v1/analytics/overview`、`GET /api/v1/analytics/diagnoses`、`GET /api/v1/analytics/interviews`、`GET /api/v1/analytics/weaknesses`
- 使用结构化解析、诊断或模拟面试前，需要在 `backend/.env` 配置 `DEEPSEEK_API_KEY`；模型默认 `deepseek-flash`

### 2. 前端

```bash
cd frontend
npm install
npm run dev
```

访问 <http://localhost:5173>，未登录会自动进入登录页；注册入口为 <http://localhost:5173/auth?mode=register>，登录后可在“我的简历”上传 PDF/DOCX，并在简历列表点击“结构化”进入字段校正页，再点击“开始诊断”生成四维报告，或点击“模拟面试”开始逐题训练；目标岗位在“岗位”页维护，“成长”页查看同口径趋势与弱项。开发服务器已将 `/api` 代理到 `http://127.0.0.1:8000`。

### 3. 测试与构建

```bash
cd backend && .venv/Scripts/python.exe -m pytest
cd frontend && npm run test && npm run build
```

## 容器部署

```bash
cp .env.docker.example .env.docker
# 填写 DB_PASSWORD 与 SECRET_KEY（至少 32 位随机字符串）
docker compose --env-file .env.docker up -d --build
```

访问 <http://localhost:8080>。数据库迁移在 api 容器启动时自动执行；详细步骤、备份恢复与排查见 [`docs/部署说明.md`](docs/部署说明.md)。

## 技术栈

- 前端：Vue 3 + TypeScript + Vite + Element Plus + Pinia + ECharts。
- 后端：Python 3.13 + FastAPI + Pydantic v2 + SQLAlchemy 2 + Alembic。
- 数据库：PostgreSQL 17（不使用 SQLite）。
- AI：DeepSeek API，独立 Provider，密钥与模型名全部通过环境变量配置；默认 `deepseek-flash`。
- 部署：Docker Compose + Nginx（后续阶段）。

## 核心业务闭环

简历版本 → 四维诊断（格式 15% / 完整度 20% / 关键词 25% / JD 匹配 40%）→ 事实约束修改示例 → 简历与 JD 驱动面试 → 同岗位、同 `rubric_version` 的成长分析。

## 参考项目

| 目录 | 用途 | 许可证约束 |
|---|---|---|
| `reference/Resume-Matcher` | 参考确定性评分、PDF 解析检查、事实保全、关键词边界匹配 | Apache-2.0；复制代码需保留许可证和 NOTICE，并标注修改 |
| `reference/intelligent-job-assistant` | 可运行原型；参考解析、DeepSeek 客户端、面试会话与报告 | MIT；需重构为 PostgreSQL + Alembic + Vue 3 TS |
| `reference/interview` | 参考面试状态、逐题评价、报告和成长轨迹的业务设计 | 未检测到 LICENSE，只读设计参考，禁止复制代码 |

## 文档

- `docs/智能简历诊断与面试模拟平台_项目计划书.docx`
- `docs/智能简历诊断与面试模拟平台_开题报告.docx`
- `docs/开发同步记录.md`
- `docs/部署说明.md`
- `docs/测试报告.md`
- `docs/架构说明.md`
- `docs/演示脚本.md`
- `docs/验收清单.md`
- `docs/验收材料/`
- `docs/assets/architecture.png`

文档内学生信息、学院和指导教师为待填写项，需按学校模板替换封面。
