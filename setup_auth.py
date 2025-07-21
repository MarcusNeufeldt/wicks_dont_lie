import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import bcrypt

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

# Initialize credentials dict
credentials = {
    'usernames': {
        'testuser': {
            'email': 'test@example.com',
            'name': 'Test User',
            'password': hash_password('password123')
        }
    }
}

# Initialize cookie dict
cookie = {
    'expiry_days': 30,
    'key': 'some_signature_key',
    'name': 'wick_analysis_cookie'
}

# Combine into config
config = {
    'credentials': credentials,
    'cookie': cookie
}

# Save to config file
with open('.streamlit/config.yaml', 'w') as file:
    yaml.dump(config, file, default_flow_style=False)

print("Config file created successfully with test user:"
      "\nUsername: testuser"
      "\nPassword: password123")
