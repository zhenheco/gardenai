from __future__ import annotations

import streamlit as st
from sqlmodel import Session, select

from core.memory import ASIN, ChangeRequest, get_db, get_partner, seed_demo
from core.styles import inject_global_css, render_hero_header, render_kpi_card, render_badge


st.set_page_config(page_title="GardenAI Dashboard", page_icon="🌱", layout="wide")
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
    asins = session.exec(select(ASIN)).all()
    pending = session.exec(select(ChangeRequest).where(ChangeRequest.status == "pending")).all()
    asin_by_id = {asin.id: asin for asin in asins}

    render_hero_header(
        f"Hallo, {partner.name} 👋", 
        f"本週你有 {len(pending)} 件事待決定 | Dein KI-Operations-Manager für Amazon DE"
    )

    compliance = round(sum(a.compliance_score for a in asins) / max(len(asins), 1))
    listing = round(sum(a.listing_score for a in asins) / max(len(asins), 1))
    rufus = round(sum(a.rufus_score for a in asins) / max(len(asins), 1))
    
    col1, col2, col3 = st.columns(3)
    with col1:
        render_kpi_card("⚖️ 合規健康分", f"{compliance}/100", "+5", icon="⚖️")
    with col2:
        render_kpi_card("📝 Listing 健康分", f"{listing}/100", "-3", icon="📝")
    with col3:
        render_kpi_card("🤖 Rufus 健康分", f"{rufus}/100", "+12", icon="🤖")

    st.markdown("### 待你決定")
    if not pending:
        st.success("目前沒有待決定事項。")

    for request in pending:
        asin = asin_by_id.get(request.asin_id)
        with st.container(border=True):
            head_col, risk_col = st.columns([4, 1])
            with head_col:
                st.markdown(f"**{asin.asin if asin else 'ASIN'}** · {request.summary}")
            with risk_col:
                # Assign risk levels based on summary content or type
                risk_level = "warning"
                if "合規" in request.summary or "GPSR" in request.summary:
                    risk_level = "destructive"
                render_badge(risk_level.upper(), risk_level)
            
            if request.rationale:
                st.caption(request.rationale)
            if request.impact_estimate:
                st.caption(f"預估影響：{request.impact_estimate}")
            
            view_col, approve_col, reject_col, _ = st.columns([1, 1, 1, 3])
            if view_col.button("檢視", key=f"view-{request.id}", use_container_width=True):
                if request.change_type == "listing_rewrite":
                    st.switch_page("pages/4_Listing_改寫.py")
                else:
                    st.switch_page("pages/3_合規檢查.py")
            if approve_col.button("Approve", key=f"approve-{request.id}", type="primary", use_container_width=True):
                request.approve(session)
                st.toast("已 approve")
                st.rerun()
            if reject_col.button("Reject", key=f"reject-{request.id}", use_container_width=True):
                request.reject(session)
                st.toast("已 reject")
                st.rerun()

    st.markdown("---")
    st.markdown("#### 過去 7 天活動軌跡")
    # Placeholder timeline
    st.caption("🕒 2026-05-14 · AI 生成了 5 個 Listing 優化建議")
    st.caption("🕒 2026-05-12 · 完成 GPSR 自動掃描")
