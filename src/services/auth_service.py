import re
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from sqlalchemy import func
from database.models import Owner, Property

_hasher = PasswordHasher()

def normalize_email(email: str) -> str:
    return email.strip().lower()

def validate_registration(full_name: str, email: str, password: str) -> str | None:
    if len(full_name.strip()) < 2: return "Enter your full name."
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", normalize_email(email)): return "Enter a valid email address."
    if len(password) < 10: return "Password must contain at least 10 characters."
    return None

def hash_password(password: str) -> str:
    return _hasher.hash(password)

def verify_password(password_hash: str, password: str) -> bool:
    try: return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError): return False

def register_owner(session, full_name: str, email: str, password: str) -> Owner:
    error = validate_registration(full_name, email, password)
    if error: raise ValueError(error)
    email = normalize_email(email)
    if session.query(Owner).filter(func.lower(Owner.email) == email).first(): raise ValueError("An owner account with this email already exists.")
    owner = Owner(full_name=full_name.strip(), email=email, password_hash=hash_password(password), is_active=True)
    session.add(owner); session.commit(); return owner

def authenticate_owner(session, email: str, password: str) -> Owner | None:
    owner = session.query(Owner).filter(func.lower(Owner.email) == normalize_email(email), Owner.is_active.is_(True)).first()
    return owner if owner and verify_password(owner.password_hash, password) else None

def owned_properties(session, owner_id: int):
    return session.query(Property).filter(Property.owner_id == owner_id).order_by(Property.id).all()
