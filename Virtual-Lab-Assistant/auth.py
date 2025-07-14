from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime, timedelta
import jwt
import mysql.connector
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv
import os
import requests
import time


# Load environment variables
load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")  # Default for testing
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "mysql"),
    "port": int(os.getenv("DB_PORT", 3306)),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASS", ""),
    "database": os.getenv("DB_NAME", "Virtual_Lab_Assistant")
}

app = FastAPI()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Database connection function

def get_db_connection():
    max_retries = 5
    for i in range(max_retries):
        try:
            print(f"Trying to connect with: host={DB_CONFIG['host']}, user={DB_CONFIG['user']}, password=****, database={DB_CONFIG['database']}, port={DB_CONFIG['port']}")
            return mysql.connector.connect(**DB_CONFIG)
        except mysql.connector.Error as e:
            print(f"Connection failed: {e}, retry {i+1}/{max_retries}")
            if i == max_retries - 1:
                raise
            time.sleep(5)

# Pydantic Models
class TokenRequest(BaseModel):
    grant_type: str
    username: str  # Now represents email
    password: str

class RefreshRequest(BaseModel):
    grant_type: str
    refresh_token: str

# Generate JWT Token
def generate_token(email: str):
    access_token = jwt.encode(
        {"email": email, "exp": datetime.utcnow() + timedelta(hours=1)},
        SECRET_KEY,
        algorithm="HS256"
    )
    refresh_token = jwt.encode(
        {"email": email, "exp": datetime.utcnow() + timedelta(days=7)},
        SECRET_KEY,
        algorithm="HS256"
    )
    return access_token, refresh_token

# Validate Token
async def get_current_user(token: str = Depends(oauth2_scheme)):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        cursor.execute("SELECT * FROM user_tokens WHERE email = %s AND token = %s AND is_active = TRUE", (payload["email"], token))
        if not cursor.fetchone():
            raise HTTPException(status_code=401, detail="Invalid token")
        return payload["email"]
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    finally:
        cursor.close()
        conn.close()

@app.post("/token")
async def issue_token(request: TokenRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT password FROM users WHERE email = %s", (request.username,))
        stored_password = cursor.fetchone()
        if not stored_password or request.password != stored_password[0]:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        access_token, refresh_token = generate_token(request.username)
        current_time = datetime.utcnow()
        expires_at = current_time + timedelta(hours=1)
        refresh_expires_at = current_time + timedelta(days=7)
        
        cursor.execute("UPDATE user_tokens SET is_active = FALSE WHERE email = %s", (request.username,))
        conn.commit()
        
        try:
            cursor.execute(
                "INSERT INTO user_tokens (email, token, expires_at, refresh_token, refresh_expires_at, is_active) VALUES (%s, %s, %s, %s, %s, %s)",
                (request.username, access_token, expires_at, refresh_token, refresh_expires_at, True)
            )
            conn.commit()
        except mysql.connector.IntegrityError as e:
            print(f"Integrity error: {e}")
            cursor.execute(
                "UPDATE user_tokens SET token = %s, expires_at = %s, refresh_token = %s, refresh_expires_at = %s, is_active = TRUE WHERE email = %s",
                (access_token, expires_at, refresh_token, refresh_expires_at, request.username)
            )
            if cursor.rowcount == 0:
                cursor.execute(
                    "INSERT INTO user_tokens (email, token, expires_at, refresh_token, refresh_expires_at, is_active) VALUES (%s, %s, %s, %s, %s, %s)",
                    (request.username, access_token, expires_at, refresh_token, refresh_expires_at, True)
                )
            conn.commit()
        except mysql.connector.Error as e:
            print(f"Database error: {e}")
            raise HTTPException(status_code=500, detail=f"Token insertion failed: {e}")
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": 3600
        }
    finally:
        cursor.close()
        conn.close()

@app.post("/refresh")
async def refresh_token(request: RefreshRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        payload = jwt.decode(request.refresh_token, SECRET_KEY, algorithms=["HS256"])
        cursor.execute("SELECT * FROM user_tokens WHERE email = %s AND refresh_token = %s AND is_active = TRUE AND refresh_expires_at > %s",
                       (payload["email"], request.refresh_token, datetime.utcnow()))
        if not cursor.fetchone():
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        
        new_access_token, _ = generate_token(payload["email"])
        current_time = datetime.utcnow()
        new_expires_at = current_time + timedelta(hours=1)
        
        cursor.execute("UPDATE user_tokens SET is_active = FALSE WHERE email = %s", (payload["email"],))
        conn.commit()
        
        try:
            cursor.execute(
                "INSERT INTO user_tokens (email, token, expires_at, refresh_token, refresh_expires_at, is_active) VALUES (%s, %s, %s, %s, %s, %s)",
                (payload["email"], new_access_token, new_expires_at, request.refresh_token, current_time + timedelta(days=7), True)
            )
            conn.commit()
        except mysql.connector.IntegrityError as e:
            print(f"Integrity error: {e}")
            cursor.execute(
                "UPDATE user_tokens SET token = %s, expires_at = %s, refresh_token = %s, refresh_expires_at = %s, is_active = TRUE WHERE email = %s",
                (new_access_token, new_expires_at, request.refresh_token, current_time + timedelta(days=7), payload["email"])
            )
            if cursor.rowcount == 0:
                cursor.execute(
                    "INSERT INTO user_tokens (email, token, expires_at, refresh_token, refresh_expires_at, is_active) VALUES (%s, %s, %s, %s, %s, %s)",
                    (payload["email"], new_access_token, new_expires_at, request.refresh_token, current_time + timedelta(days=7), True)
                )
            conn.commit()
        except mysql.connector.Error as e:
            print(f"Database error: {e}")
            raise HTTPException(status_code=500, detail=f"Token insertion failed: {e}")
        
        return {
            "access_token": new_access_token,
            "token_type": "bearer",
            "expires_in": 3600
        }
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    finally:
        cursor.close()
        conn.close()

@app.post("/rasa/webhook")
async def chatbot_webhook(message: dict, email: str = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        rasa_url = os.getenv("RASA_URL", "http://rasa:5005/webhooks/rest/webhook")
        response = requests.post(
            rasa_url,
            json={"sender": email, "message": message.get("message")}
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Error connecting to Rasa: {str(e)}")
    finally:
        cursor.close()
        conn.close()