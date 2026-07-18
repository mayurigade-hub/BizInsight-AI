import re
import streamlit as st
from database import get_user_by_username, verify_password, create_user


def is_logged_in():
    return "current_user" in st.session_state and st.session_state["current_user"] is not None


def get_current_user():
    return st.session_state.get("current_user", None)


def logout():
    st.session_state.pop("current_user", None)
    st.session_state.pop("last_upload_hash", None)


def login(username, password):
    user = get_user_by_username(username)
    if not user:
        return None, "No account found with that username."
    if not verify_password(password, user["password_hash"]):
        return None, "Incorrect password."
    return user, None

def register(username, email, password, confirm_password):

    if not username.strip():
        return False, "Username cannot be empty."

    if not email.strip():
        return False, "Email address cannot be empty."

    email_pattern = r"^[^@]+@[^@]+\.[^@]+$"

    if not re.match(email_pattern, email):
        return False, "Please enter a valid email address."

    if len(password) < 6:
        return False, "Password must be at least 6 characters."

    if password != confirm_password:
        return False, "Passwords do not match."

    result = create_user(username, email, password)

    if result == "USERNAME_EXISTS":
        return False, "Username already exists."

    if result == "EMAIL_EXISTS":
        return False, "Email already registered."

    if not result:
        return False, "Registration failed."

    return True, None


def show_auth_page():
    # Inject auth-specific glass card style
    st.markdown("""
    <style>
    /* Styling login/signup tab containers specifically as centered glass cards */
    div[data-testid="stVerticalBlock"] > div:has(.stTabs) {
        background: rgba(15, 23, 42, 0.7) !important;
        backdrop-filter: blur(25px) saturate(1.2) !important;
        -webkit-backdrop-filter: blur(25px) saturate(1.2) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 18px !important;
        padding: 30px !important;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4) !important;
        margin-top: 20px;
    }
    .auth-title-container {
        text-align: center;
        margin-bottom: 25px;
    }
    .auth-title-container img {
        margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.3, 1])

    with col2:
        st.markdown(
            """
            <div class="auth-title-container">
                <h1 style="margin-bottom: 0px;">📊 BizInsight AI</h1>
                <p style="color: #94A3B8; font-size: 0.95rem;">AI-powered customer intelligence platform for business growth</p>
            </div>
            """, 
            unsafe_allow_html=True
        )

        tab_login, tab_register = st.tabs(["Login", "Register"])

        with tab_login:
            st.markdown("<br>", unsafe_allow_html=True)
            username = st.text_input(
                "Username", placeholder="Enter your username", key="login_username")
            password = st.text_input(
                "Password", type="password", placeholder="Enter your password", key="login_password")
            st.markdown("<br>", unsafe_allow_html=True)

            if st.button("Login", use_container_width=True, type="primary"):
                if not username or not password:
                    st.error("Please fill in all fields.")
                else:
                    user, error = login(username, password)
                    if error:
                        st.error(error)
                    else:
                        st.session_state["current_user"] = user
                        st.rerun()

        with tab_register:
            new_username = st.text_input(
                "Username",
                placeholder="Choose a username",
                key="reg_username"
            )

            email = st.text_input(
                "Email Address",
                placeholder="Enter your email",
                key="reg_email"
            )

            new_password = st.text_input(
                "Password",
                type="password",
                placeholder="Minimum 6 characters",
                key="reg_password"
            )

            confirm_password = st.text_input(
                "Confirm Password",
                type="password",
                placeholder="Re-enter password",
                key="reg_confirm"
            )

            st.markdown("<br>", unsafe_allow_html=True)

            if st.button("Create Account", use_container_width=True, type="primary"):
                success, error = register(
                    new_username,
                    email,
                    new_password,
                    confirm_password
                )

                if error:
                    st.error(error)
                else:
                    st.success("Account created successfully! Please log in.")
                    st.session_state["login_username"] = new_username
                    st.rerun()


def show_setup_wizard():
    st.markdown("""
    <style>
    /* Styling setup wizard container specifically as centered glass card */
    div[data-testid="stVerticalBlock"] > div:has(input) {
        background: rgba(15, 23, 42, 0.7) !important;
        backdrop-filter: blur(25px) saturate(1.2) !important;
        -webkit-backdrop-filter: blur(25px) saturate(1.2) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 18px !important;
        padding: 30px !important;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4) !important;
        margin-top: 20px;
    }
    .setup-title-container {
        text-align: center;
        margin-bottom: 25px;
    }
    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.3, 1])

    with col2:
        st.markdown(
            """
            <div class="setup-title-container">
                <h1 style="margin-bottom: 0px;">🚀 First Time Setup</h1>
                <p style="color: #94A3B8; font-size: 0.95rem;">Create your admin account to initialize BizInsight AI</p>
            </div>
            """, 
            unsafe_allow_html=True
        )

        st.info("No accounts exist yet. Create your admin account to get started.")
        st.markdown("<br>", unsafe_allow_html=True)

        username = st.text_input(
            "Admin Username", placeholder="Choose an admin username")
        email = st.text_input(
            "Admin Email", placeholder="Enter an admin email")
        password = st.text_input(
            "Password", type="password", placeholder="Min. 6 characters")
        confirm = st.text_input(
            "Confirm Password", type="password", placeholder="Repeat your password")
        st.markdown("<br>", unsafe_allow_html=True)

        if st.button("Create Admin Account", use_container_width=True, type="primary"):
            if not username or not email or not password or not confirm:
                st.error("Please fill in all fields.")
            elif len(password) < 6:
                st.error("Password must be at least 6 characters.")
            elif password != confirm:
                st.error("Password confirmation does not match.")
            else:
                success = create_user(username, email, password, role="admin")
                if success:
                    st.success("Admin account created. You can now log in.")
                    st.rerun()
                else:
                    st.error("Something went wrong. Try again.")
