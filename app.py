from __future__ import annotations

import hmac
import os

from dotenv import load_dotenv


load_dotenv()


def verify_password(candidate: str | None) -> bool:
    expected = os.getenv("ADMIN_PASSWORD", "changeme-on-first-run")
    if not candidate:
        return False
    return hmac.compare_digest(candidate, expected)


def main() -> None:
    import streamlit as st
    from sqlmodel import Session

    from core.memory import get_db, get_partner, list_partner_slugs, seed_demo
    from core.styles import inject_global_css

    st.set_page_config(page_title="GardenAI", page_icon="🌱", layout="wide")
    inject_global_css()
    seed_demo()

    slugs = list_partner_slugs()
    selected = st.sidebar.selectbox("Design partner", slugs, index=slugs.index("demo") if "demo" in slugs else 0)
    st.session_state["partner_slug"] = selected
    with Session(get_db(selected)) as session:
        partner = get_partner(session, selected)
    st.session_state["partner_name"] = partner.name

    st.sidebar.caption(f"目前賣家：{partner.name}")

    if not st.session_state.get("authenticated"):
        _, center, _ = st.columns([1, 2, 1])
        with center:
            st.markdown(
                """
                <div style="text-align: center; margin-top: 5rem; margin-bottom: 2rem;">
                    <h1 style="font-size: 3rem;">🌱 GardenAI</h1>
                    <p style="color: #64748B; font-size: 1.1rem;">Dein KI-Operations-Manager für Amazon DE</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            with st.container(border=True):
                st.subheader("Partner Login")
                password = st.text_input("管理密碼", type="password")
                if st.button("登入", type="primary", use_container_width=True):
                    if verify_password(password):
                        st.session_state["authenticated"] = True
                        st.rerun()
                    st.error("密碼錯誤")
                
                st.markdown(
                    """
                    <div style="text-align: center; margin-top: 2rem; color: #64748B; font-size: 0.8rem;">
                        Beta v0.1 · 3 design partner 共創中
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        st.stop()

    st.sidebar.success("已登入")
    st.switch_page("pages/1_Dashboard.py")


if __name__ == "__main__":
    main()
