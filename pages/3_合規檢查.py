from __future__ import annotations

import json

import streamlit as st
from sqlmodel import Session, select

from core.compliance import check, generate_rp_statement, risk_badge
from core.memory import ASIN, current_versions, get_db, seed_demo
from core.styles import inject_global_css, render_badge


st.set_page_config(page_title="合規檢查", page_icon="⚖️", layout="wide")
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
    listings = {}
    for asin in asins:
        version = versions.get(asin.id)
        listings[asin.id] = {
            "title": version.title if version else asin.title,
            "bullets": version.bullets if version else [],
            "description": version.description if version else "",
            "category": asin.category or "",
            "images": version.images if version else [],
        }

    st.title("GPSR 風險檢查")
    left, right = st.columns([1, 2])
    with left:
        st.subheader("ASIN 列表")
        labels = []
        for asin in asins:
            findings = check(listings[asin.id])
            risk = risk_badge(findings)
            labels.append(f"{risk} {asin.asin} · {asin.title[:34]}")
        choice = st.radio("ASIN", labels, label_visibility="collapsed")
        selected = asins[labels.index(choice)]

    with right:
        listing = listings[selected.id]
        findings = check(listing)
        st.subheader(selected.title)
        st.caption(f"{selected.asin} · {selected.category or '-'}")
        
        if not findings:
            st.success("目前 deterministic rule set 未發現高風險缺口。")
        
        for finding in findings:
            kind = "destructive" if finding.severity == "high" else "warning" if finding.severity == "medium" else "success"
            with st.container(border=True):
                col_f, col_b = st.columns([4, 1])
                with col_f:
                    st.markdown(f"**{finding.type}**")
                with col_b:
                    render_badge(finding.severity.upper(), kind)
                
                st.write(finding.description)
                st.info(f"💡 **建議修正：** {finding.suggested_fix}")
                if finding.fix_text_de:
                    st.code(finding.fix_text_de, language="text")

        st.markdown("---")
        st.subheader("一鍵生成 EU RP 聲明")
        if st.button("Generate EU RP statement", type="primary", use_container_width=True):
            statement = generate_rp_statement(listing, st.session_state.get("partner_name", "Demo Garden GmbH"))
            st.code(statement, language="text")
            st.caption("請將此文字貼入 Amazon Backend 的 'Safety & Compliance' 區塊。")
            
        with st.expander("Listing 原始資料 (Payload)"):
            st.json(json.dumps(listing, ensure_ascii=False))
