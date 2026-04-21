from __future__ import annotations

import base64
import hashlib
from typing import Optional

from sqlalchemy import Column, Integer, String, UniqueConstraint
from sqlalchemy import delete

from db import Base, SessionLocal
from settings import get_settings


class ApiCredential(Base):
    __tablename__ = "api_credentials"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    value_enc = Column(String, nullable=False)

    __table_args__ = (UniqueConstraint("name", name="uq_api_credentials_name"),)


def _xor_encrypt_to_b64(plaintext: str, secret: str) -> str:
    """
    Lightweight reversible obfuscation using a key-derived xor stream.
    This is not strong cryptography, but prevents plain-text storage.
    For stronger security, swap to Fernet (cryptography) later.
    """
    key = hashlib.sha256(secret.encode("utf-8")).digest()
    pt = plaintext.encode("utf-8")
    out = bytes([b ^ key[i % len(key)] for i, b in enumerate(pt)])
    return base64.urlsafe_b64encode(out).decode("ascii")


def _xor_decrypt_from_b64(ciphertext_b64: str, secret: str) -> str:
    key = hashlib.sha256(secret.encode("utf-8")).digest()
    ct = base64.urlsafe_b64decode(ciphertext_b64.encode("ascii"))
    out = bytes([b ^ key[i % len(key)] for i, b in enumerate(ct)])
    return out.decode("utf-8")


def _encryption_secret() -> Optional[str]:
    # Prefer an explicit secret; fall back to an AI key (not ideal but avoids hard failure).
    settings = get_settings()
    return (
        settings.secret_key
        or settings.openai_api_key
        or settings.gemini_api_key
        or settings.groq_api_key
    )


def set_credential(name: str, value: str) -> None:
    secret = _encryption_secret()
    if not secret:
        raise ValueError("No encryption secret available. Set at least one AI key first.")

    enc = _xor_encrypt_to_b64(value, secret)
    db = SessionLocal()
    try:
        existing = db.query(ApiCredential).filter(ApiCredential.name == name).first()
        if existing:
            existing.value_enc = enc
        else:
            db.add(ApiCredential(name=name, value_enc=enc))
        db.commit()
    finally:
        db.close()


def get_credential(name: str) -> Optional[str]:
    secret = _encryption_secret()
    if not secret:
        return None

    db = SessionLocal()
    try:
        row = db.query(ApiCredential).filter(ApiCredential.name == name).first()
        if not row:
            return None
        try:
            return _xor_decrypt_from_b64(row.value_enc, secret)
        except Exception:
            return None
    finally:
        db.close()


def credential_status(names: list[str]) -> dict[str, bool]:
    db = SessionLocal()
    try:
        present = {r.name for r in db.query(ApiCredential.name).all()}
    finally:
        db.close()
    return {n: (n in present) for n in names}


def delete_credentials(names: Optional[list[str]] = None) -> int:
    """
    Delete stored credentials.
    - names=None: delete all
    - names=[...]: delete only those keys
    Returns number of rows deleted.
    """
    db = SessionLocal()
    try:
        if not names:
            q = delete(ApiCredential)
        else:
            q = delete(ApiCredential).where(ApiCredential.name.in_(names))
        res = db.execute(q)
        db.commit()
        return int(res.rowcount or 0)
    finally:
        db.close()

