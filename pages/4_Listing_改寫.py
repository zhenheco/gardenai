from __future__ import annotations

import json

import streamlit as st
from sqlmodel import Session, select

from core.memory import ASIN, ChangeRequest, current_versions, get_db, seed_demo
from core.styles import inject_global_css, render_diff


st.set_page_config(page_title="Listing 改寫", page_icon="📝", layout="wide")
inject_global_css()
seed_demo()
if not st.session_state.get("authenticated"):
    st.warning("請先登入。")
    st.page_link("app.py", label="回登入頁")
    st.stop()

partner_slug = st.session_state.get("partner_slug", "demo")
engine = get_db(partner_slug)

with Session(engine) as session:
    asins = session.exec(select(ASIN)).all()
    versions = current_versions(session)
    rewrite_requests = session.exec(
        select(ChangeRequest).where(
            ChangeRequest.change_type == "listing_rewrite",
            ChangeRequest.status == "pending",
        )
    ).all()
    request_by_asin = {request.asin_id: request for request in rewrite_requests}

    st.title("Listing 優化建議")
    
    col_sel, col_btn = st.columns([3, 1])
    with col_sel:
        selected_label = st.selectbox("選擇 ASIN", [f"{asin.asin} · {asin.title[:60]}" for asin in asins], label_visibility="collapsed")
    with col_btn:
        st.button("重新生成 AI 建議", use_container_width=True)

    selected = asins[[f"{asin.asin} · {asin.title[:60]}" for asin in asins].index(selected_label)]
    version = versions.get(selected.id)
    request = request_by_asin.get(selected.id)
    proposed = json.loads(request.proposed_json) if request else {}

    original = {
        "title": version.title if version else selected.title,
        "bullets": version.bullets if version else [],
        "description": version.description if version else "",
    }
    new_listing = {
        "title": proposed.get("title") or proposed.get("new_title") or original["title"],
        "bullets": proposed.get("bullets") or proposed.get("new_bullets") or original["bullets"],
        "description": proposed.get("description") or proposed.get("new_description") or original["description"],
    }

    t1, t2, t3 = st.tabs(["標題 (Title)", "五點描述 (Bullets)", "產品描述 (Description)"])
    with t1:
        render_diff(original["title"], new_listing["title"])
    with t2:
        render_diff(original["bullets"], new_listing["bullets"])
    with t3:
        render_diff(original["description"], new_listing["description"])

    st.markdown("---")
    with st.expander("🤖 AI 改寫邏輯與預估影響", expanded=True):
        st.write(request.rationale if request else "目前沒有待審核的 AI 改寫建議。")
        if request and request.impact_estimate:
            st.success(f"**預估影響：** {request.impact_estimate}")

    st.markdown("### 審核動作")
    edit_text = st.text_area("編輯 Proposed JSON (進階使用)", value=json.dumps(new_listing, indent=2, ensure_ascii=False), height=150)
    
    col1, col2, col3, _ = st.columns([1, 1, 1, 2])
    if request and col1.button("Approve All", type="primary", use_container_width=True):
        try:
            request.proposed_json = edit_text
            request.approve(session)
            st.success("已 approve 並更新 Listing。")
            st.rerun()
        except json.JSONDecodeError:
            st.error("JSON 格式錯誤。")
    if request and col2.button("Reject", use_container_width=True):
        request.reject(session)
        st.info("已 reject 建議。")
        st.rerun()
    if request and col3.button("僅儲存編輯", use_container_width=True):
        request.proposed_json = edit_text
        request.audit_log = f"{request.audit_log}\nadmin edited proposed JSON".strip()
        session.add(request)
        session.commit()
        st.toast("編輯已儲存")
