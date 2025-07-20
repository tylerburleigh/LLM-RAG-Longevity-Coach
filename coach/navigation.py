"""Navigation utilities for user context and page management."""

import streamlit as st
from datetime import datetime, timedelta
from typing import Optional

from coach.auth import auth_manager
from coach.models import UserContext
from coach.config import config


def display_user_context_sidebar():
    """Display user context information in the sidebar."""
    user_context = auth_manager.get_user_context()
    
    if not user_context:
        with st.sidebar:
            st.markdown("---")
            st.error("❌ Not authenticated")
            st.info("Please log in to continue")
            if st.button("Go to Main Page"):
                st.switch_page("app.py")
        return None
    
    with st.sidebar:
        
        # Main pages
        if st.button("💬 Chat", use_container_width=True):
            st.switch_page("app.py")
        
        # Data management pages
        st.markdown("**Data Management:**")
        if st.button("📚 Knowledge Base", use_container_width=True):
            st.switch_page("pages/1_Knowledge_Base.py")
        if st.button("📄 Upload Documents", use_container_width=True):
            st.switch_page("pages/2_Upload_Documents.py")
        if st.button("🗣️ Guided Entry", use_container_width=True):
            st.switch_page("pages/3_Guided_Entry.py")
        if st.button("⚙️ Profile & Settings", use_container_width=True):
            st.switch_page("pages/4_Profile_Settings.py")
        
        # Chat actions (only show on main page)
        if st.session_state.get('current_page') == 'main' or 'messages' in st.session_state:
            st.markdown("---")
            st.subheader("💬 Chat Control")
            if st.button("🔄 Start New Conversation", use_container_width=True):
                # Clear conversation state
                keys_to_clear = ['app_state', 'messages', 'initial_query', 'clarifying_questions', 'feedback']
                for key in keys_to_clear:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()
        
        # Account actions
        st.markdown("---")
        st.subheader("🔧 Account")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Refresh", use_container_width=True):
                st.cache_data.clear()
                st.rerun()
        with col2:
            if st.button("🚪 Logout", use_container_width=True):
                auth_manager.logout()
    
    return user_context


def display_page_header(page_title: str, page_icon: str = "📋", show_breadcrumb: bool = True):
    """Display consistent page header with navigation breadcrumb."""
    st.set_page_config(
        page_title=f"{page_title} - Longevity Coach",
        page_icon=page_icon,
        layout="wide"
    )
    
    # Page title
    st.title(f"{page_icon} {page_title}")
    
    # Breadcrumb navigation
    if show_breadcrumb:
        # Get current page name from the title
        current_page = page_title
        
        # Create breadcrumb
        breadcrumb_items = ["🏠 Home"]
        
        # Add current page if not home
        if current_page != "Longevity Coach":
            breadcrumb_items.append(f"📍 {current_page}")
        
        # Display breadcrumb
        breadcrumb = " > ".join(breadcrumb_items)
        st.markdown(f"*{breadcrumb}*")
        st.markdown("---")


def show_authentication_error(message: str = "Authentication required"):
    """Display authentication error with helpful guidance."""
    st.error(f"🔐 {message}")
    
    with st.container(border=True):
        st.markdown("### 🚨 Access Denied")
        st.markdown("""
        You need to be logged in to access this page.
        
        **Next Steps:**
        1. Click the "Go to Login" button below
        2. Log in with your Google account
        3. Return to this page
        """)
        
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button("🔐 Go to Login", type="primary", use_container_width=True):
                st.switch_page("app.py")
    
    # Show helpful tips
    with st.expander("💡 Tips"):
        st.markdown("""
        **Common Issues:**
        - **Pop-ups blocked:** Allow pop-ups for this site
        - **Cookies disabled:** Enable cookies in your browser
        - **Session expired:** Sessions expire after 24 hours
        
        **Still having trouble?**
        Try refreshing the page or clearing your browser cache.
        """)


def show_loading_state(message: str = "Loading..."):
    """Display loading state with user context."""
    with st.spinner(message):
        user_context = display_user_context_sidebar()
        if not user_context:
            show_authentication_error()
            return None
        return user_context


def ensure_authenticated_access(page_title: str, page_icon: str = "📋") -> Optional[UserContext]:
    """Ensure user is authenticated and display page header and navigation."""
    # Display page header
    display_page_header(page_title, page_icon)
    
    # Display user context and check authentication
    user_context = display_user_context_sidebar()
    
    if not user_context:
        show_authentication_error()
        return None
    
    return user_context


def display_page_footer():
    """Display consistent page footer."""
    st.markdown("")