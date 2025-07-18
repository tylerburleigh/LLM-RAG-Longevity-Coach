"""Common page setup utilities for consistent navigation and styling."""

import streamlit as st


def setup_page_config(page_title: str, page_icon: str = "🧬", layout: str = "wide"):
    """Set up page configuration with consistent styling and navigation hiding."""
    st.set_page_config(
        page_title=f"{page_title} - Longevity Coach",
        page_icon=page_icon,
        layout=layout,
        initial_sidebar_state="expanded"
    )
    
    # Hide Streamlit's default navigation and styling
    hide_streamlit_style = """
    <style>
    /* Hide the default Streamlit navigation */
    [data-testid="stSidebarNav"] {display: none;}
    [data-testid="stSidebarHeader"] {display: none;}
    </style>
    """
    st.markdown(hide_streamlit_style, unsafe_allow_html=True)


def setup_authenticated_page(page_title: str, page_icon: str = "🧬", layout: str = "wide"):
    """Set up an authenticated page with navigation and user context."""
    from coach.navigation import ensure_authenticated_access, display_page_footer
    
    # Set up page configuration
    setup_page_config(page_title, page_icon, layout)
    
    # Ensure authentication and display navigation
    user_context = ensure_authenticated_access(page_title, page_icon)
    
    if not user_context:
        st.stop()  # Stop execution if not authenticated
    
    return user_context


def setup_main_page():
    """Set up the main application page with specific styling."""
    setup_page_config("Longevity Coach - Personalized Health Insights", "🧬")