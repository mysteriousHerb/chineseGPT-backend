import os

from dotenv import load_dotenv
from pymongo import ASCENDING
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from passlib.context import CryptContext
from parameters import ATLAS_URL
from typing import Optional
from datetime import datetime, timedelta
from parameters import ACCESS_TOKEN_EXPIRE_MINUTES, ENCODING_ALGORITHM
import jwt


load_dotenv()
if os.path.exists(".env.local"):
    load_dotenv(".env.local")
if os.path.exists(".env.production") and os.getenv("ENVIRONMENT") == "production":
    print("GETTING PRODUCTION ENVIRONMENT VARIABLES")
    load_dotenv(".env.production")

ENCODING_KEY = os.getenv("ENCODING_KEY")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# Send a ping to confirm a successful connection
def get_client():
    mongoDB_username = os.getenv("MONGODB_USERNAME")
    mongoDB_password = os.getenv("MONGODB_PASSWORD")
    uri = f"mongodb+srv://{mongoDB_username}:{mongoDB_password}@{ATLAS_URL}"

    # Create a new client and connect to the server
    client = MongoClient(uri, server_api=ServerApi("1"))
    return client


def check_connection(client):
    try:
        client.admin.command("ping")
        print("Pinged your deployment. You successfully connected to MongoDB!")
    except Exception as e:
        print(e)


def create_users_collection(client):
    # Create a new client and connect to the server
    db = client["GPTian"]
    users_collection = db["users"]
    # Create unique index on the 'username' field
    users_collection.create_index([("username", ASCENDING)], unique=True)
    return users_collection


def get_users_collection(client):
    # Create a new client and connect to the server
    db = client["GPTian"]
    users_collection = db["users"]

    return users_collection


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    access_token = jwt.encode(to_encode, ENCODING_KEY, algorithm=ENCODING_ALGORITHM)
    return access_token


def decoding_token(token: str):
    return jwt.decode(token, ENCODING_KEY, algorithms=[ENCODING_ALGORITHM])


def authenticate_user(users_collection, username: str, password: str):
    user = users_collection.find_one({"username": username})
    if not user:
        return None
    if not verify_password(password, user["password"]):
        return None
    return user


if __name__ == "__main__":
    mongo_client = get_client()
    users_collection = get_users_collection(mongo_client)
    # users_collection.drop()
    # creaet_users_collection(mongo_client)
