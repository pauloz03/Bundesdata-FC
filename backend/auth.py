from sqlalchemy import text
from postgres import SessionLocal
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from pwdlib import PasswordHash
import jwt #for creating and verifying tokens
import secrets
import hashlib
from datetime import datetime, timedelta, timezone
#function to verify the access token, its in another file
from auth_guard import verify_access_token

import config
import logging


#setting up some tools
logging.basicConfig(level=logging.INFO)
logger= logging.getLogger(__name__)
#recommended() is a class method that creates/configures the PasswordHash object for you.
pwd_hashing_tool= PasswordHash.recommended()

#HELPER FUNCTIONS:
def helper_create_token(user_id: str) -> str:
    expire_time= datetime.now(timezone.utc) + timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload= {
        "user_id": str(user_id),
        "exp": expire_time
    }
    token= jwt.encode(payload, config.SECRET_JWT_KEY, algorithm= config.TOKEN_ALGORITHM)
    return token
    
def helper_create_refresh_token()-> tuple[str, str]:
    raw_token= secrets.token_urlsafe(32)
    hashed_token= hashlib.sha256(raw_token.encode()).hexdigest()
    return raw_token, hashed_token

def helper_hash_function(password: str) -> str:
    password_hash= pwd_hashing_tool.hash(password)
    return password_hash



def login(email: str, password: str) -> dict:
    db_session= SessionLocal()
    
    try:
        query= db_session.execute(text("SELECT * FROM users WHERE email = :email"), 
        {"email": email.strip().lower()}).mappings().first()
        if not query:
            raise HTTPException(status_code=401, detail="Invalid email or password")


        password_check= pwd_hashing_tool.verify(password, query["password_hash"])
        if not password_check:              #Im not checking for email but its to not reveal which one is wrong
            raise HTTPException(status_code= 401, detail="Invalid email or password")
        
        try:
            user_id= query["id"]
            access_token= helper_create_token(user_id)
            raw_refresh_token, hashed_refresh_token= helper_create_refresh_token()
            sessions_query= db_session.execute(text("SELECT * FROM auth_sessions WHERE user_id = :user_id"), {"user_id": user_id}).mappings().first()
            expire_time= datetime.now(timezone.utc) + timedelta(days=config.REFRESH_TOKEN_EXPIRE_DAYS)

            if sessions_query:
                db_session.execute(text("UPDATE auth_sessions SET refresh_token_hash = :hashed_refresh_token, expires_at = :expire_time WHERE user_id = :user_id"), 
                {"hashed_refresh_token": hashed_refresh_token, "user_id": user_id, "expire_time": expire_time})
            else:
                db_session.execute(text("INSERT into auth_sessions (user_id, refresh_token_hash, expires_at) VALUES (:user_id, :hashed_refresh_token, :expire_time)"),
                {"user_id": user_id, "hashed_refresh_token": hashed_refresh_token, "expire_time": expire_time})

            db_session.commit()
        except Exception as e:
            db_session.rollback()
            raise HTTPException(status_code=500, detail="Internal auth error")

        logger.info(f"User {email} logged in successfully")
        return {"message": "Login successful", "access_token": access_token, "token_type": "bearer", "refresh_token": raw_refresh_token}

    finally:
        db_session.close()



def signup(email: str, password: str) -> dict:
    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password are required")

    hashed_password= helper_hash_function(password)
    db_session= SessionLocal()

    try:
        query= db_session.execute(text("INSERT INTO users (email, password_hash, created_at) VALUES (:email, :password_hash, NOW()) RETURNING id"), 
        {"email": email.strip().lower(), "password_hash": hashed_password, "created_at": datetime.now(timezone.utc)}).mappings().first()

        db_session.commit()

        logger.info(f"User {email} created successfully")
        return {"message": "User created successfully"}

    #try the insert, if the db ejects it because of a constraint violation, rollback the transaction and raise an error
    except IntegrityError as e:
        db_session.rollback()
        raise HTTPException(status_code=400, detail="Email already exists")
    
    finally:
        db_session.close()



def logout(access_token: str, refresh_token: str) -> dict:
    db_session= SessionLocal()

    try:
        payload= verify_access_token(access_token)
        if not payload:
            raise HTTPException(status_code=401, detail="Invalid token")

        user_id= payload["user_id"]
        hashed_refresh_token= hashlib.sha256(refresh_token.encode()).hexdigest()
        query= db_session.execute(text("SELECT * FROM auth_sessions WHERE refresh_token_hash = :hashed_refresh_token"), {"hashed_refresh_token": hashed_refresh_token}).mappings().first()
        if not query:
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        db_session.execute(text("UPDATE auth_sessions SET revoked_at = NOW() WHERE user_id = :user_id"), {"user_id": user_id})
        db_session.execute(text("UPDATE users SET last_login_at = NOW() WHERE id = :user_id"), {"user_id": user_id})
        db_session.commit()
        
        logger.info(f"User {user_id} logged out successfully")
        return {"message": "Logout successful"}

    except Exception as e:
        db_session.rollback()
        raise HTTPException(status_code=500, detail="Internal logout error")
    
    finally:
        db_session.close()
            


def refresh_page(refresh_token: str) -> dict:
    db_session= SessionLocal()

    hashed_refresh_token= hashlib.sha256(refresh_token.encode()).hexdigest()
    try:
        query= db_session.execute(text("SELECT * FROM auth_sessions WHERE refresh_token_hash = :hashed_refresh_token"), {"hashed_refresh_token": hashed_refresh_token}).mappings().first()

        if not query:
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        if query["revoked_at"] is not None:
            logger.info(f"Refresh attempt with revoked token for user {query['user_id']}")
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        if query["expires_at"] < datetime.now(timezone.utc):
            logger.info(f"Refresh attempt with expired token for user {query['user_id']}")
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        try:
            user_id= query["user_id"]
            access_token= helper_create_token(user_id)
            raw_refresh_token, hashed_refresh_token= helper_create_refresh_token()
            sessions_query= db_session.execute(text("SELECT * FROM auth_sessions WHERE user_id = :user_id"), {"user_id": user_id}).mappings().first()
            expire_time= datetime.now(timezone.utc) + timedelta(days=config.REFRESH_TOKEN_EXPIRE_DAYS)

            if sessions_query:
                db_session.execute(text("UPDATE auth_sessions SET refresh_token_hash = :hashed_refresh_token, expires_at = :expire_time WHERE user_id = :user_id"), 
                {"hashed_refresh_token": hashed_refresh_token, "user_id": user_id, "expire_time": expire_time})
            else:
                db_session.execute(text("INSERT into auth_sessions (user_id, refresh_token_hash, expires_at) VALUES (:user_id, :hashed_refresh_token, :expire_time)"),
                {"user_id": user_id, "hashed_refresh_token": hashed_refresh_token, "expire_time": expire_time})

            db_session.commit()

        except Exception as e:
            db_session.rollback()
            raise HTTPException(status_code=500, detail="Internal refresh error")
        
        return {"message": "Refresh successful", "access_token": access_token, "token_type": "bearer", "refresh_token": raw_refresh_token}
    
    finally:
        db_session.close()



