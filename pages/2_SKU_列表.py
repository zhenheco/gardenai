from __future__ import annotations

import json

import streamlit as st
from sqlmodel import Session, select

from core.memory import ASIN, ListingVersion, current_versions, get_db, get_partner, now_utc, seed_demo
from core.scraper import scrape_asin
from core.styles import inject_global_css


st.set_page_config(page_title="SKU 列表", page_icon="🌱", layout="wide")
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
    asins = session.exec(select(ASIN).where(ASIN.partner_id == partner.id)).all()
    versions = current_versions(session)

    st.title("SKU 列表")
    
    # Toolbar
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        search = st.text_input("搜尋 ASIN 或標題", placeholder="Suche...", label_visibility="collapsed")
    with col2:
        st.selectbox("Marketplace", ["Amazon.de", "Amazon.fr", "Amazon.it"], label_visibility="collapsed")
    with col3:
        st.button("+ 新增 ASIN", type="primary", use_container_width=True)

    rows = [
        {
            "圖": asin.image_url,
            "ASIN": asin.asin,
            "標題": asin.title,
            "BSR": asin.bsr or "-",
            "健康分": asin.health_score,
            "最後檢查": asin.last_checked_at.strftime("%Y-%m-%d"),
        }
        for asin in asins
        if not search or search.lower() in asin.asin.lower() or search.lower() in asin.title.lower()
    ]
    
    event = st.dataframe(
        rows,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        column_config={
            "圖": st.column_config.ImageColumn(width="small"),
            "健康分": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%d"),
            "ASIN": st.column_config.TextColumn(width="small"),
        },
    )

    selected_rows = event.selection.rows if event and event.selection else []
    if selected_rows:
        asin = [a for a in asins if not search or search.lower() in a.asin.lower() or search.lower() in a.title.lower()][selected_rows[0]]
        version = versions.get(asin.id)
        with st.expander(f"{asin.asin} 詳細資料", expanded=True):
            st.write(asin.title)
            st.caption(f"Category: {asin.category or '-'} · Rating: {asin.rating or '-'}")
            if version:
                t1, t2 = st.tabs(["目前 Bullets", "Description"])
                with t1:
                    for bullet in version.bullets:
                        st.write(f"- {bullet}")
                with t2:
                    st.write(version.description)

    st.divider()
    with st.expander("新增 ASIN", expanded=False):
        with st.form("add-asin"):
            asin_input = st.text_input("ASIN", placeholder="B0...")
            submitted = st.form_submit_button("抓取並儲存", type="primary")
        if submitted and asin_input:
            with st.spinner("正在抓取 Amazon 資料..."):
                listing = scrape_asin(asin_input.strip().upper())
                if not listing:
                    st.error("Amazon.de 目前阻擋抓取或找不到 listing，請稍後再試。")
                else:
                    existing = session.exec(select(ASIN).where(ASIN.asin == listing["asin"])).first()
                    if existing:
                        st.warning("這個 ASIN 已存在。")
                    else:
                        asin = ASIN(
                            partner_id=partner.id,
                            asin=listing["asin"],
                            title=listing["title"],
                            image_url=(listing.get("images") or [None])[0],
                            category=listing.get("category"),
                            bsr=listing.get("bsr"),
                            rating=listing.get("rating"),
                            raw_json=json.dumps(listing, ensure_ascii=False),
                            last_checked_at=now_utc(),
                        )
                        session.add(asin)
                        session.commit()
                        session.refresh(asin)
                        session.add(
                            ListingVersion(
                                asin_id=asin.id,
                                title=listing["title"],
                                bullets_json=json.dumps(listing.get("bullets", []), ensure_ascii=False),
                                description=listing.get("description", ""),
                                images_json=json.dumps(listing.get("images", []), ensure_ascii=False),
                                source="scraper",
                            )
                        )
                        session.commit()
                        st.success("已新增 ASIN。")
                        st.rerun()
