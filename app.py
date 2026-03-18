from flask import Flask, request, jsonify, render_template, send_file, abort
from datetime import datetime
import json
import io

from models import init_db, get_conn, row_to_dict, get_flags
from utils import (
    generate_resume_id, generate_password, utc_now, expiry_from_now,
    is_expired, simulate_email, whatsapp_link, validate_email,
    validate_phone, auto_capitalize, format_display_time,
)

session_state = {"start": datetime.utcnow()}
SESSION_LIMIT_MINUTES = 20

app = Flask(__name__)
init_db()



def session_expired():
    return (datetime.utcnow() - session_state["start"]).total_seconds() > SESSION_LIMIT_MINUTES * 60


def log_action(conn, resume_id, action, detail=None):
    conn.execute(
        "INSERT INTO activity_log (resume_id, action, detail, timestamp) VALUES (?, ?, ?, ?)",
        (resume_id, action, detail, utc_now()),
    )



@app.route("/")
def index():
    return render_template("index.html")


@app.route("/admin")
def admin():
    with get_conn() as conn:
        resumes = [dict(r) for r in conn.execute(
            "SELECT id, name, email, phone, download_count, created_at, updated_at, expires_at "
            "FROM resumes ORDER BY created_at DESC"
        ).fetchall()]
        logs = [dict(r) for r in conn.execute(
            "SELECT * FROM activity_log ORDER BY timestamp DESC LIMIT 200"
        ).fetchall()]
        shares = [dict(r) for r in conn.execute(
            "SELECT * FROM share_history ORDER BY timestamp DESC LIMIT 200"
        ).fetchall()]
        flags = get_flags(conn)
    return render_template("admin.html", resumes=resumes, logs=logs,
                           shares=shares, flags=flags)



@app.route("/admin/flags", methods=["POST"])
def update_flags():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data"}), 400
    with get_conn() as conn:
        for key, val in data.items():
            conn.execute(
                "UPDATE feature_flags SET enabled = ? WHERE key = ?",
                (1 if val else 0, key),
            )
        conn.commit()
    return jsonify({"ok": True})


@app.route("/flags")
def get_feature_flags():
    with get_conn() as conn:
        return jsonify(get_flags(conn))



@app.route("/resume", methods=["POST"])
def create_resume():
    if session_expired():
        return jsonify({"error": "Resume submission time has expired."}), 403

    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided."}), 400

    errors = {}
    if not data.get("name"):
        errors["name"] = "Name is required."
    if not data.get("email"):
        errors["email"] = "Email is required."
    elif not validate_email(data["email"]):
        errors["email"] = "Invalid email format."
    if data.get("phone") and not validate_phone(data["phone"]):
        errors["phone"] = "Invalid phone format."
    skills = data.get("skills", [])
    if len(json.dumps(data)) > 100_000:
        errors["size"] = "Content exceeds size limit."
    if errors:
        return jsonify({"errors": errors}), 400

    resume_id = generate_resume_id()
    dob = data.get("dob", "00-00-0000")
    password = generate_password(data["name"], dob)
    now = utc_now()
    expires = expiry_from_now(24)

    with get_conn() as conn:
        conn.execute(
            """INSERT INTO resumes
               (id, name, email, phone, dob, summary, skills, experience,
                education, certifications, languages, password,
                download_count, created_at, updated_at, expires_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,0,?,?,?)""",
            (
                resume_id, data["name"], data["email"],
                data.get("phone", ""), dob,
                data.get("summary", ""),
                json.dumps(data.get("skills", [])),
                json.dumps(data.get("experience", [])),
                json.dumps(data.get("education", [])),
                json.dumps(data.get("certifications", [])),
                json.dumps(data.get("languages", [])),
                password, now, now, expires,
            ),
        )
        log_action(conn, resume_id, "resume_created", data["name"])
        conn.commit()

    with get_conn() as conn:
        flags = get_flags(conn)

    if flags.get("email"):
        simulate_email(data["email"], resume_id, password)

    return jsonify({
        "id": resume_id,
        "password": password if flags.get("password_protection") else None,
        "expires_at": expires,
        "whatsapp": whatsapp_link(resume_id, password, request.host_url.rstrip("/")),
        "flags": flags,
    }), 201


@app.route("/resume/<resume_id>", methods=["GET"])
def get_resume(resume_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM resumes WHERE id = ?", (resume_id,)).fetchone()
    resume = row_to_dict(row)
    if not resume:
        return jsonify({"error": "Not found."}), 404
    if is_expired(resume["expires_at"]):
        return jsonify({"error": "This resume link has expired. Please generate again."}), 410
    return jsonify(resume)


@app.route("/resume/<resume_id>", methods=["PUT"])
def update_resume(resume_id):
    if session_expired():
        return jsonify({"error": "Session expired."}), 403
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data."}), 400

    errors = {}
    if data.get("email") and not validate_email(data["email"]):
        errors["email"] = "Invalid email format."
    if data.get("phone") and not validate_phone(data["phone"]):
        errors["phone"] = "Invalid phone format."
    if errors:
        return jsonify({"errors": errors}), 400

    with get_conn() as conn:
        row = conn.execute("SELECT id FROM resumes WHERE id = ?", (resume_id,)).fetchone()
        if not row:
            return jsonify({"error": "Not found."}), 404
        conn.execute(
            """UPDATE resumes SET name=?, email=?, phone=?, dob=?, summary=?,
               skills=?, experience=?, education=?, certifications=?,
               languages=?, updated_at=? WHERE id=?""",
            (
                data.get("name"), data.get("email"), data.get("phone", ""),
                data.get("dob", ""), data.get("summary", ""),
                json.dumps(data.get("skills", [])),
                json.dumps(data.get("experience", [])),
                json.dumps(data.get("education", [])),
                json.dumps(data.get("certifications", [])),
                json.dumps(data.get("languages", [])),
                utc_now(), resume_id,
            ),
        )
        log_action(conn, resume_id, "resume_updated")
        conn.commit()
    return jsonify({"message": "Updated."})


@app.route("/resume/<resume_id>", methods=["DELETE"])
def delete_resume(resume_id):
    with get_conn() as conn:
        row = conn.execute("SELECT id FROM resumes WHERE id = ?", (resume_id,)).fetchone()
        if not row:
            return jsonify({"error": "Not found."}), 404
        conn.execute("DELETE FROM resumes WHERE id = ?", (resume_id,))
        conn.execute("DELETE FROM share_history WHERE resume_id = ?", (resume_id,))
        log_action(conn, resume_id, "resume_deleted")
        conn.commit()
    return jsonify({"message": "Deleted."})



@app.route("/resume/<resume_id>/download")
def download_resume(resume_id):
    with get_conn() as conn:
        flags = get_flags(conn)
        if not flags.get("download"):
            return jsonify({"error": "Downloads are currently disabled."}), 403
        row = conn.execute("SELECT * FROM resumes WHERE id = ?", (resume_id,)).fetchone()
        resume = row_to_dict(row)
        if not resume:
            abort(404)
        if is_expired(resume["expires_at"]):
            return jsonify({"error": "This resume link has expired. Please generate again."}), 410
        conn.execute(
            "UPDATE resumes SET download_count = download_count + 1 WHERE id = ?",
            (resume_id,),
        )
        log_action(conn, resume_id, "downloaded",
                   f"download #{resume['download_count'] + 1}")
        conn.commit()

    use_password = flags.get("password_protection")
    pdf_bytes = generate_pdf(resume, password=resume["password"] if use_password else None)
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"{resume_id}.pdf",
    )



@app.route("/resume/<resume_id>/share/email", methods=["POST"])
def share_email(resume_id):
    with get_conn() as conn:
        flags = get_flags(conn)
        if not flags.get("email"):
            return jsonify({"error": "Email sharing is disabled."}), 403
        row = conn.execute("SELECT * FROM resumes WHERE id = ?", (resume_id,)).fetchone()
        resume = row_to_dict(row)
        if not resume:
            return jsonify({"error": "Not found."}), 404

        data = request.get_json() or {}
        recipient = data.get("email", resume["email"])
        if not validate_email(recipient):
            return jsonify({"error": "Invalid email."}), 400

        pdf_bytes = generate_pdf(resume, password=resume["password"] if flags.get("password_protection") else None)
        simulate_email(recipient, resume_id, resume["password"], pdf_bytes)

        conn.execute(
            "INSERT INTO share_history (resume_id, method, recipient, timestamp) VALUES (?,?,?,?)",
            (resume_id, "email", recipient, utc_now()),
        )
        log_action(conn, resume_id, "shared_email", recipient)
        conn.commit()
    return jsonify({"message": f"Resume sent to {recipient}."})



@app.route("/resume/<resume_id>/share/whatsapp", methods=["POST"])
def share_whatsapp(resume_id):
    with get_conn() as conn:
        flags = get_flags(conn)
        if not flags.get("whatsapp"):
            return jsonify({"error": "WhatsApp sharing is disabled."}), 403
        row = conn.execute("SELECT * FROM resumes WHERE id = ?", (resume_id,)).fetchone()
        resume = row_to_dict(row)
        if not resume:
            return jsonify({"error": "Not found."}), 404

        existing = conn.execute(
            "SELECT id FROM share_history WHERE resume_id=? AND method='whatsapp' AND whatsapp_sent=1",
            (resume_id,),
        ).fetchone()
        if existing:
            return jsonify({"error": "WhatsApp already sent. Resend is disabled."}), 409

        data = request.get_json() or {}
        recipient = data.get("phone", "")
        link = whatsapp_link(resume_id, resume["password"], request.host_url.rstrip("/"))

        conn.execute(
            "INSERT INTO share_history (resume_id, method, recipient, timestamp, whatsapp_sent) VALUES (?,?,?,?,1)",
            (resume_id, "whatsapp", recipient, utc_now()),
        )
        log_action(conn, resume_id, "shared_whatsapp", recipient)
        conn.commit()

    return jsonify({"link": link, "message": "WhatsApp link generated."})



@app.route("/session-status")
def session_status():
    elapsed = (datetime.utcnow() - session_state["start"]).total_seconds()
    remaining = max(0, SESSION_LIMIT_MINUTES * 60 - elapsed)
    return jsonify({"expired": session_expired(), "remaining_seconds": int(remaining)})


@app.route("/admin/session/reset", methods=["POST"])
def reset_session():
    session_state["start"] = datetime.utcnow()
    with get_conn() as conn:
        log_action(conn, None, "session_reset", "Admin reset session timer")
        conn.commit()
    return jsonify({"message": "Session timer reset. 20 minutes restarted."})

@app.route("/resume/<resume_id>/stats")
def resume_stats(resume_id):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, name, download_count, created_at, expires_at FROM resumes WHERE id=?",
            (resume_id,),
        ).fetchone()
        if not row:
            return jsonify({"error": "Not found."}), 404
        shares = conn.execute(
            "SELECT method, recipient, timestamp FROM share_history WHERE resume_id=?",
            (resume_id,),
        ).fetchall()
        logs = conn.execute(
            "SELECT action, detail, timestamp FROM activity_log WHERE resume_id=? ORDER BY timestamp DESC",
            (resume_id,),
        ).fetchall()
    return jsonify({
        "id": row["id"],
        "name": row["name"],
        "download_count": row["download_count"],
        "created_at": row["created_at"],
        "expires_at": row["expires_at"],
        "share_history": [dict(s) for s in shares],
        "activity_log": [dict(l) for l in logs],
    })


@app.route("/utils/capitalize", methods=["POST"])
def capitalize_text():
    data = request.get_json() or {}
    text = data.get("text", "")
    return jsonify({"result": auto_capitalize(text)})



def generate_pdf(resume: dict, password: str = None) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle
    )

    W, H = A4
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=22*mm, rightMargin=22*mm,
        topMargin=18*mm, bottomMargin=18*mm,
    )

    DARK    = colors.HexColor("#1a1a2e")
    ACCENT  = colors.HexColor("#2563eb")
    MUTED   = colors.HexColor("#6b7280")
    RULE    = colors.HexColor("#e5e7eb")

    def S(name, **kw):
        defaults = dict(fontName="Helvetica", fontSize=10,
                        textColor=DARK, leading=14, spaceAfter=0)
        defaults.update(kw)
        return ParagraphStyle(name, **defaults)

    styles = {
        "name":    S("name", fontName="Helvetica-Bold", fontSize=22, leading=26, spaceAfter=3, textColor=DARK),
        "contact": S("contact", fontSize=9, textColor=MUTED, spaceAfter=10),
        "summary": S("summary", fontSize=10, leading=15, spaceAfter=6, textColor=colors.HexColor("#374151")),
        "section": S("section", fontName="Helvetica-Bold", fontSize=10,
                     textColor=ACCENT, spaceBefore=14, spaceAfter=4,
                     letterSpacing=1.2),
        "body":    S("body", fontSize=10, leading=14, spaceAfter=3),
        "bold":    S("bold", fontName="Helvetica-Bold", fontSize=10, leading=14),
        "small":   S("small", fontSize=8.5, textColor=MUTED, leading=12, spaceAfter=2),
        "footer":  S("footer", fontSize=7.5, textColor=MUTED),
    }

    def hr():
        return HRFlowable(width="100%", thickness=0.6, color=RULE, spaceAfter=6, spaceBefore=2)

    def section(title):
        return [Paragraph(title.upper(), styles["section"]), hr()]

    story = []

    story.append(Paragraph(resume["name"], styles["name"]))
    contact_parts = [p for p in [resume.get("email"), resume.get("phone")] if p]
    story.append(Paragraph("  ·  ".join(contact_parts), styles["contact"]))
    story.append(HRFlowable(width="100%", thickness=1.5, color=ACCENT, spaceAfter=10))

    if resume.get("summary"):
        story += section("Summary")
        story.append(Paragraph(resume["summary"], styles["summary"]))

    if resume.get("experience"):
        story += section("Experience")
        for exp in resume["experience"]:
            role    = exp.get("role", "")
            company = exp.get("company", "")
            dur     = exp.get("duration", "")
            desc    = exp.get("description", "")
            header  = f"<b>{role}</b>"
            if company:
                header += f" — {company}"
            story.append(Paragraph(header, styles["bold"]))
            if dur:
                story.append(Paragraph(dur, styles["small"]))
            if desc:
                story.append(Paragraph(desc, styles["body"]))
            story.append(Spacer(1, 5))

    if resume.get("education"):
        story += section("Education")
        for edu in resume["education"]:
            deg    = edu.get("degree", "")
            school = edu.get("institution", "")
            yr     = edu.get("year", "")
            story.append(Paragraph(f"<b>{deg}</b> — {school}", styles["bold"]))
            if yr:
                story.append(Paragraph(yr, styles["small"]))
            story.append(Spacer(1, 4))

    if resume.get("skills"):
        story += section("Skills")
        story.append(Paragraph(", ".join(resume["skills"]), styles["body"]))

    if resume.get("certifications"):
        story += section("Certifications")
        for cert in resume["certifications"]:
            story.append(Paragraph(f"• {cert}", styles["body"]))

    if resume.get("languages"):
        story += section("Languages")
        story.append(Paragraph("  ·  ".join(resume["languages"]), styles["body"]))

    story.append(Spacer(1, 16))
    story.append(HRFlowable(width="100%", thickness=0.4, color=RULE))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        f"Resume ID: {resume['id']}  ·  Generated: {resume['created_at'][:10]}",
        styles["footer"],
    ))

    if password:
        from reportlab.pdfgen import canvas as pdfcanvas
        from reportlab.lib.pagesizes import A4 as _A4
        doc.build(story)
        raw = buffer.getvalue()
        try:
            from pypdf import PdfReader, PdfWriter
            reader = PdfReader(io.BytesIO(raw))
            writer = PdfWriter()
            for page in reader.pages:
                writer.add_page(page)
            writer.encrypt(password)
            out = io.BytesIO()
            writer.write(out)
            return out.getvalue()
        except Exception:
            return raw
    else:
        doc.build(story)
        return buffer.getvalue()

if __name__ == "__main__":
    import os
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
