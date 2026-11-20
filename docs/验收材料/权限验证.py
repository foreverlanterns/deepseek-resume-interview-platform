"""权限与数据隔离自动验证（针对已部署的容器环境）。

用法：
    backend/.venv/Scripts/python.exe docs/验收材料/权限验证.py
    backend/.venv/Scripts/python.exe docs/验收材料/权限验证.py http://127.0.0.1:8080/api/v1

脚本会创建两个临时账号（permcheck.*），上传简历、创建岗位、诊断和面试，
然后用 B 账号尝试访问 A 账号的资源，逐项输出 PASS / FAIL。
"""

from __future__ import annotations

import sys
import time
import uuid
from io import BytesIO

import httpx
import pymupdf
from docx import Document

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8080/api/v1"
ORIGIN = BASE.split("/api/v1")[0]
PASSWORD = "VerifyPass123"
STAMP = f"{int(time.time())}-{uuid.uuid4().hex[:6]}"
EMAIL_A = f"permcheck.a.{STAMP}@example.com"
EMAIL_B = f"permcheck.b.{STAMP}@example.com"

RESULTS: list[tuple[str, str, bool, str]] = []
START = time.time()


def check(item: str, desc: str, passed: bool, detail: str = "") -> None:
    RESULTS.append((item, desc, passed, detail))
    print(f"[{'PASS' if passed else 'FAIL'}] {item} {desc}" + (f" | {detail}" if detail else ""))


def build_docx() -> bytes:
    doc = Document()
    doc.add_heading("权限验证简历", level=0)
    doc.add_paragraph("后端开发工程师")
    doc.add_paragraph("邮箱：permcheck@example.com")
    doc.add_heading("工作经历", level=1)
    doc.add_paragraph("某科技公司 | 后端开发工程师 | 2023.01 - 至今")
    doc.add_paragraph("使用 Python 与 FastAPI 开发业务接口，使用 PostgreSQL 存储数据。")
    doc.add_heading("专业技能", level=1)
    doc.add_paragraph("Python、FastAPI、PostgreSQL")
    buffer = BytesIO()
    doc.save(buffer)
    return buffer.getvalue()


def build_pdf() -> bytes:
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Access check resume")
    page.insert_text((72, 96), "Python FastAPI PostgreSQL")
    data = doc.tobytes()
    doc.close()
    return data


def register(client: httpx.Client, email: str) -> httpx.Response:
    return client.post(
        "/auth/register",
        json={"email": email, "password": PASSWORD, "display_name": "权限验证"},
    )


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


with httpx.Client(base_url=BASE, timeout=240) as client:
    # P-08 邮箱规范化与唯一性
    response_a = register(client, EMAIL_A)
    response_b = register(client, EMAIL_B)
    check("P-02", "注册新账号返回 201", response_a.status_code == 201, str(response_a.status_code))
    check("P-03", "第二个账号注册成功", response_b.status_code == 201, str(response_b.status_code))

    duplicate = register(client, EMAIL_A.upper())
    check(
        "P-04",
        "同一邮箱大写形式重复注册被拒（409）",
        duplicate.status_code == 409,
        f"{duplicate.status_code} {duplicate.text[:80]}",
    )

    # P-09 登录失败不泄露账号是否存在
    wrong_password = client.post("/auth/login", json={"email": EMAIL_A, "password": "WrongPass123"})
    unknown_account = client.post(
        "/auth/login",
        json={"email": f"nobody.{STAMP}@example.com", "password": "WrongPass123"},
    )
    same_detail = wrong_password.json().get("detail") == unknown_account.json().get("detail")
    check(
        "P-05",
        "错误密码与不存在账号返回一致的 401 提示",
        wrong_password.status_code == 401 and unknown_account.status_code == 401 and same_detail,
        f"{wrong_password.status_code}/{unknown_account.status_code}",
    )

    login_a = client.post("/auth/login", json={"email": EMAIL_A, "password": PASSWORD})
    login_b = client.post("/auth/login", json={"email": EMAIL_B, "password": PASSWORD})
    token_a = login_a.json()["access_token"]
    token_b = login_b.json()["access_token"]
    headers_a = auth(token_a)
    headers_b = auth(token_b)

    # P-01 未认证访问
    anonymous = client.get("/resumes")
    www_auth = anonymous.headers.get("www-authenticate", "")
    check(
        "P-01",
        "未携带 Token 访问接口返回 401 且带 WWW-Authenticate",
        anonymous.status_code == 401 and "bearer" in www_auth.lower(),
        f"{anonymous.status_code} header={www_auth}",
    )

    # P-10 篡改 Token
    tampered = token_a[:-3] + ("aaa" if not token_a.endswith("aaa") else "bbb")
    tampered_response = client.get("/resumes", headers=auth(tampered))
    check("P-06", "篡改签名后的 Token 返回 401", tampered_response.status_code == 401, str(tampered_response.status_code))

    # A 账号准备数据
    upload = client.post(
        "/resumes/upload",
        headers=headers_a,
        files={
            "file": (
                "permcheck.docx",
                build_docx(),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )
    check("DATA-01", "A 上传 DOCX 成功", upload.status_code == 201, str(upload.status_code))
    resume_a = upload.json()
    resume_id = resume_a["id"]

    parsed = client.post(f"/resumes/{resume_id}/parse", headers=headers_a)
    check("DATA-02", "A 结构化解析成功", parsed.status_code == 201, f"{parsed.status_code} {parsed.text[:100]}")
    version_no = parsed.json().get("version_no", 1) if parsed.status_code == 201 else None

    jd = client.post(
        "/jds",
        headers=headers_a,
        json={
            "title": "后端开发工程师",
            "company": "验证公司",
            "raw_text": "负责后端接口开发，要求 Python、FastAPI、PostgreSQL。",
            "required_skills": ["Python", "PostgreSQL"],
            "preferred_skills": ["FastAPI"],
            "keywords": ["Docker"],
            "responsibilities": ["负责后端接口设计与实现"],
            "qualifications": ["本科及以上"],
        },
    )
    check("DATA-03", "A 创建岗位成功", jd.status_code == 201, str(jd.status_code))
    jd_id = jd.json()["id"]

    diagnosis_id = None
    if version_no is not None:
        diagnosis = client.post(
            "/diagnoses",
            headers=headers_a,
            json={"resume_id": resume_id, "resume_version_no": version_no, "jd_id": jd_id},
        )
        check("DATA-04", "A 创建诊断成功", diagnosis.status_code == 201, f"{diagnosis.status_code} {diagnosis.text[:100]}")
        if diagnosis.status_code == 201:
            diagnosis_id = diagnosis.json()["id"]

    interview = client.post(
        "/interviews",
        headers=headers_a,
        json={
            "resume_id": resume_id,
            "resume_version_no": version_no or 1,
            "jd_id": jd_id,
            "interview_type": "mixed",
            "question_count": 3,
        },
    )
    check("DATA-05", "A 创建面试成功", interview.status_code == 201, f"{interview.status_code} {interview.text[:100]}")
    interview_id = interview.json()["id"] if interview.status_code == 201 else None
    question_id = interview.json()["questions"][0]["id"] if interview.status_code == 201 else None

    # P-03 / P-04 简历隔离
    read_resume = client.get(f"/resumes/{resume_id}", headers=headers_b)
    check("P-07", "B 读取 A 的简历返回 404", read_resume.status_code == 404, str(read_resume.status_code))

    read_versions = client.get(f"/resumes/{resume_id}/versions", headers=headers_b)
    check("P-08", "B 读取 A 的简历版本返回 404", read_versions.status_code == 404, str(read_versions.status_code))

    delete_resume = client.delete(f"/resumes/{resume_id}", headers=headers_b)
    still_there = client.get(f"/resumes/{resume_id}", headers=headers_a)
    check(
        "P-09",
        "B 删除 A 的简历返回 404 且 A 的数据仍在",
        delete_resume.status_code == 404 and still_there.status_code == 200,
        f"delete={delete_resume.status_code} read={still_there.status_code}",
    )

    # P-06 / P-07 诊断与面试隔离
    if diagnosis_id:
        read_diagnosis = client.get(f"/diagnoses/{diagnosis_id}", headers=headers_b)
        check("P-10", "B 读取 A 的诊断返回 404", read_diagnosis.status_code == 404, str(read_diagnosis.status_code))

    if interview_id:
        read_interview = client.get(f"/interviews/{interview_id}", headers=headers_b)
        check("P-11", "B 读取 A 的面试返回 404", read_interview.status_code == 404, str(read_interview.status_code))

        if question_id:
            answer_other = client.post(
                f"/interviews/{interview_id}/questions/{question_id}/answer",
                headers=headers_b,
                json={"answer": "越权尝试作答"},
            )
            check("P-12", "B 给 A 的面试题目作答返回 404", answer_other.status_code == 404, str(answer_other.status_code))

        report_other = client.post(f"/interviews/{interview_id}/report", headers=headers_b)
        check("P-13", "B 生成 A 的面试报告返回 404", report_other.status_code == 404, str(report_other.status_code))

    # P-10 用他人简历创建诊断/面试
    if version_no is not None:
        cross_diagnosis = client.post(
            "/diagnoses",
            headers=headers_b,
            json={"resume_id": resume_id, "resume_version_no": version_no, "jd_id": jd_id},
        )
        check("P-14", "B 用 A 的简历创建诊断返回 404", cross_diagnosis.status_code == 404, str(cross_diagnosis.status_code))

    cross_interview = client.post(
        "/interviews",
        headers=headers_b,
        json={
            "resume_id": resume_id,
            "resume_version_no": version_no or 1,
            "jd_id": jd_id,
            "interview_type": "mixed",
            "question_count": 3,
        },
    )
    check("P-15", "B 用 A 的简历创建面试返回 404", cross_interview.status_code == 404, str(cross_interview.status_code))

    # P-12 列表与统计隔离
    list_b = client.get("/resumes", headers=headers_b)
    b_ids = {item["id"] for item in list_b.json()} if list_b.status_code == 200 else set()
    check("P-16", "B 的简历列表不含 A 的简历", resume_id not in b_ids, f"count={len(b_ids)}")

    overview_b = client.get("/analytics/overview", headers=headers_b)
    overview = overview_b.json() if overview_b.status_code == 200 else {}
    check(
        "P-17",
        "B 的成长概览为 0 条记录",
        overview.get("resume_count") == 0
        and overview.get("diagnosis_count") == 0
        and overview.get("interview_count") == 0,
        f"{overview.get('resume_count')}/{overview.get('diagnosis_count')}/{overview.get('interview_count')}",
    )

    # P-14 文件名路径穿越
    traversal = client.post(
        "/resumes/upload",
        headers=headers_a,
        files={"file": ("../../evil.pdf", build_pdf(), "application/pdf")},
    )
    filename = traversal.json().get("original_filename", "") if traversal.status_code == 201 else ""
    check(
        "P-18",
        "上传文件名中的路径被清洗",
        traversal.status_code == 201 and "/" not in filename and ".." not in filename,
        f"{traversal.status_code} filename={filename!r}",
    )

    # P-15 上传目录未静态暴露
    probe = client.get(f"{ORIGIN}/uploads/probe.pdf")
    body_start = probe.content[:4]
    exposed = body_start == b"%PDF"
    check(
        "P-19",
        "上传目录不能直接下载文件",
        not exposed,
        f"status={probe.status_code} type={probe.headers.get('content-type', '')[:30]}",
    )

passed = sum(1 for _, _, ok, _ in RESULTS if ok)
failed = len(RESULTS) - passed
print("-" * 68)
print(f"合计 {len(RESULTS)} 项：PASS {passed}，FAIL {failed}，耗时 {time.time() - START:.1f}s")
print(f"临时账号：{EMAIL_A} / {EMAIL_B}（密码 {PASSWORD}）")
sys.exit(0 if failed == 0 else 1)
