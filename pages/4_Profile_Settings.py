"""User profile and settings page."""

import streamlit as st
from datetime import datetime, timedelta
from coach.auth import require_authentication
from coach.navigation import display_page_footer
from coach.page_setup import setup_authenticated_page
from coach.config import config


@require_authentication
def show_profile_settings():
    """Protected function to show the profile and settings page."""
    # Set up authenticated page with navigation
    user_context = setup_authenticated_page("Profile & Settings", "⚙️")
    if not user_context:
        return
    
    # Page content
    st.markdown(f"""
    **Welcome, {user_context.name}!**
    
    Manage your account settings and preferences here.
    """)
    
    # User profile section
    show_user_profile(user_context)
    
    # Privacy and security settings
    show_privacy_settings()
    
    # App preferences
    show_app_preferences()
    
    # Session management
    show_session_management()
    
    # Display footer
    display_page_footer()


def show_user_profile(user_context):
    """Display user profile information."""
    st.markdown("---")
    st.subheader("👤 User Profile")
    
    with st.container(border=True):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"**Full Name:** {user_context.name}")
            st.markdown(f"**Email:** {user_context.email}")
            st.markdown(f"**User ID:** {user_context.user_id}")
            
        with col2:
            # Account type
            account_type = "Developer" if user_context.name == "Developer" else "Google OAuth"
            st.markdown(f"**Account Type:** {account_type}")
            
            # Session info
            if 'session_created' in st.session_state:
                session_created = st.session_state['session_created']
                st.markdown(f"**Session Started:** {session_created.strftime('%Y-%m-%d %H:%M:%S')}")
                
                # Session duration
                session_duration = datetime.now() - session_created
                hours = int(session_duration.total_seconds() // 3600)
                minutes = int((session_duration.total_seconds() % 3600) // 60)
                st.markdown(f"**Session Duration:** {hours}h {minutes}m")


def show_privacy_settings():
    """Display privacy and security settings."""
    st.markdown("---")
    st.subheader("🔒 Privacy & Security")
    
    with st.container(border=True):
        st.markdown("**Data Security:**")
        st.success("✅ Your data is encrypted and stored securely")
        st.success("✅ No personal data is shared with third parties")
        st.success("✅ Sessions are automatically secured with timeout")
        
        st.markdown("**Privacy Controls:**")
        
        # Session timeout settings
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Session Timeout:** {config.SESSION_TIMEOUT_HOURS} hours")
            st.caption("Sessions automatically expire for security")
            
        with col2:
            # Session actions
            if st.button("🔄 Refresh Session"):
                st.cache_data.clear()
                st.success("Session refreshed!")
                st.rerun()
        
        # Data management
        st.markdown("**Data Management:**")
        st.info("Your health data is stored privately and can only be accessed by you")
        
        # Show warning for data deletion
        with st.expander("⚠️ Data Deletion (Advanced)"):
            st.warning("""
            **Warning:** This action cannot be undone!
            
            If you need to delete your data, please:
            1. Download any important information first
            2. Contact support if you need assistance
            3. Use the logout button to clear your session
            """)


def show_app_preferences():
    """Display application preferences."""
    st.markdown("---")
    st.subheader("🎛️ App Preferences")
    
    with st.container(border=True):
        st.markdown("**Interface Settings:**")
        
        # Theme preference (note: Streamlit doesn't support custom themes easily)
        st.markdown("**Theme:** Auto (follows system preference)")
        
        # Default model preference
        st.markdown("**Default Model Preferences:**")
        st.info("You can change the AI model on the main chat page")
        
        # Feature preferences
        st.markdown("**Features:**")
        st.success("✅ Personalized insights enabled")
        st.success("✅ Document upload enabled")
        st.success("✅ Guided data entry enabled")
        st.success("✅ Knowledge base management enabled")


def show_session_management():
    """Display session management tools."""
    st.markdown("---")
    st.subheader("🔧 Session Management")
    
    with st.container(border=True):
        # Session info
        if 'session_created' in st.session_state:
            session_age = datetime.now() - st.session_state['session_created']
            remaining_time = timedelta(hours=config.SESSION_TIMEOUT_HOURS) - session_age
            
            if remaining_time.total_seconds() > 0:
                hours = int(remaining_time.total_seconds() // 3600)
                minutes = int((remaining_time.total_seconds() % 3600) // 60)
                st.success(f"⏱️ Session expires in: {hours}h {minutes}m")
            else:
                st.error("⚠️ Session has expired. Please refresh the page.")
        
        # Session actions
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔄 Refresh Session", use_container_width=True):
                st.cache_data.clear()
                st.success("Session refreshed!")
                st.rerun()
        
        with col2:
            if st.button("🧹 Clear Cache", use_container_width=True):
                st.cache_resource.clear()
                st.cache_data.clear()
                st.success("Cache cleared!")
                st.rerun()
        
        with col3:
            if st.button("🚪 Logout", type="secondary", use_container_width=True):
                from coach.auth import auth_manager
                auth_manager.logout()
        
        # Debug info (only in development mode)
        if 'user_context' in st.session_state:
            user_data = st.session_state['user_context']
            if user_data.get('name') == 'Developer':
                with st.expander("🔧 Debug Information"):
                    st.json({
                        "session_state_keys": list(st.session_state.keys()),
                        "user_context": user_data,
                        "session_created": str(st.session_state.get('session_created', 'Not set'))
                    })


# --- Main execution ---
if __name__ == "__main__":
    show_profile_settings()