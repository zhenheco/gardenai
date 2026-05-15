from __future__ import annotations

from datetime import timedelta

import streamlit as st
from sqlmodel import Session, select

from core.memory import ASIN, ChangeRequest, WeeklyReport, get_db, get_partner, now_utc, seed_demo
from core.styles import inject_global_css, render_hero_header, render_kpi_card


st.set_page_config(page_title="週報", page_icon="📅", layout="wide")
inject_global_css()
seed_demo()
if not st.session_state.get("authenticated"):
    st.warning("請先登入。")
    st.page_link("app.py", label="回登入頁")
    st.stop()

partner_slug = st.session_state.get("partner_slug", "demo")
engine = get_db(partner_slug)

with Session(engine) as session:
    partner = get_partner(session, partner_slug)
    since = now_utc() - timedelta(days=7)
    asins = session.exec(select(ASIN)).all()
    changes = session.exec(select(ChangeRequest).where(ChangeRequest.created_at >= since).order_by(ChangeRequest.created_at.desc())).all()
    latest_report = session.exec(select(WeeklyReport).order_by(WeeklyReport.created_at.desc())).first()

    kw_number = now_utc().isocalendar()[1]
    render_hero_header(
        f"Wochenbericht KW {kw_number}", 
        f"{since.strftime('%d.%m')} - {now_utc().strftime('%d.%m.%Y')} | {partner.name}"
    )

    approved = sum(1 for change in changes if change.status == "approved")
    rejected = sum(1 for change in changes if change.status == "rejected")
    pending = sum(1 for change in changes if change.status == "pending")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_kpi_card("追蹤 ASIN", str(len(asins)), icon="📦")
    with col2:
        render_kpi_card("已 Approve", str(approved), icon="✅")
    with col3:
        render_kpi_card("已 Reject", str(rejected), icon="❌")
    with col4:
        render_kpi_card("待決定", str(pending), icon="⏳")

    st.markdown("### 本週摘要")
    with st.container(border=True):
        if latest_report:
            st.markdown(latest_report.markdown)
        else:
            st.markdown(
                f"🌱 **{partner.name} 本週 GardenAI 摘要**\n\n"
                f"- 目前追蹤 {len(asins)} 個 ASIN。\n"
                f"- 過去 7 天有 {len(changes)} 筆建議，其中 {pending} 筆仍待決定。\n"
                "- 下週優先補齊高風險 SKU 的 EU RP、CE 與安全文字，再處理 Rufus 可回答度。"
            )

    st.markdown("### 過去 7 天活動軌跡")
    if not changes:
        st.info("尚無變更紀錄。")
    for change in changes:
        icon = "✅" if change.status == "approved" else "❌" if change.status == "rejected" else "⏳"
        st.markdown(
            f"**{icon} {change.created_at.strftime('%m-%d %H:%M')}** | "
            f"`{change.change_type}` · {change.summary}"
        )

    st.markdown("---")
    if st.button("📥 下載 PDF 報告", type="primary", use_container_width=True):
        st.info("PDF 匯出功能開發中，預計 v0.2 上線。")
