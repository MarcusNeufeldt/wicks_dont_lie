import streamlit as st
import yaml
from yaml.loader import SafeLoader
import streamlit_authenticator as stauth
from db_utils import add_user
import os
import bcrypt

# Initialize session state
if 'authentication_status' not in st.session_state:
    st.session_state['authentication_status'] = None
if 'username' not in st.session_state:
    st.session_state['username'] = None

# Set page config
st.set_page_config(
    page_title="Unfilled Wick Analysis - Login",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS
st.markdown("""
<style>
    .main {
        padding: 0rem 1rem;
    }
    .stButton>button {
        width: 100%;
    }
    .css-1v3fvcr {
        padding: 1rem 1rem 1rem;
    }
    .auth-box {
        padding: 2rem;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-top: 2rem;
        background-color: #f8f9fa;
    }
</style>
""", unsafe_allow_html=True)

# Load config file
with open('.streamlit/config.yaml') as file:
    config = yaml.load(file, Loader=SafeLoader)

# Create the authenticator without pre-authorization
authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

# Main content
col1, col2, col3 = st.columns([1,2,1])

with col2:
    st.title("Unfilled Wick Analysis")
    
    st.markdown("""
    ### Discover High-Probability Trading Opportunities
    
    Our tool helps you identify unfilled candlestick wicks - a powerful pattern with a 
    **99% historical fill rate**. Perfect for long-term investment strategies using DCA.
    
    #### Key Features:
    - 🎯 Focus on high-probability upside wicks
    - 📊 Multi-timeframe analysis
    - 💹 Real-time market data
    - 📈 Interactive charts
    """)

    with st.expander("Why Unfilled Wicks?"):
        st.markdown("""
        Unfilled wicks, especially those pointing upward with small bodies, have shown 
        remarkable reliability in predicting future price movements. Our analysis shows 
        that approximately 99% of significant wicks eventually get filled.
        
        This tool is designed for:
        - Long-term investors
        - DCA strategy implementation
        - Patient traders willing to wait for setups to play out
        """)

    # Authentication
    st.markdown("### Login / Register")
    
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    with tab1:
        try:
            authenticator.login()  # No parameters needed for v0.4.1
            
            if st.session_state["authentication_status"] is False:
                st.error('Username/password is incorrect')
            elif st.session_state["authentication_status"] is True:
                st.success(f'Welcome back {st.session_state["name"]}!')
                
                # Add/update user in database
                add_user(
                    username=st.session_state["username"],
                    name=st.session_state["username"],  # Using username as name
                    email="not_required@example.com"  # Default email since we don't collect it
                )
                
                st.switch_page("pages/1_Main.py")
        except Exception as e:
            st.error(f'An error occurred: {str(e)}')

    with tab2:
        try:
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            repeat_password = st.text_input("Repeat Password", type="password")
            
            if st.button("Register"):
                if not username or not password:
                    st.error("Please fill in all fields")
                elif password != repeat_password:
                    st.error("Passwords do not match")
                else:
                    # Update config with new user
                    if username not in config['credentials']['usernames']:
                        # Hash password using bcrypt
                        hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
                        config['credentials']['usernames'][username] = {
                            'name': username,  # Using username as name
                            'email': 'not_required@example.com',  # Default email
                            'password': hashed_password
                        }
                        
                        # Save updated config
                        with open('.streamlit/config.yaml', 'w') as file:
                            yaml.dump(config, file, default_flow_style=False)
                            
                        # Add user to database
                        add_user(
                            username=username,
                            name=username,  # Using username as name
                            email="not_required@example.com"  # Default email
                        )
                        
                        st.success("Registration successful! Please login.")
                        st.experimental_rerun()
                    else:
                        st.error("Username already exists")
        except Exception as e:
            st.error(f'An error occurred: {str(e)}')
            
    st.markdown("""
    ---
    By logging in, you agree to our terms of service and privacy policy.
    """)
