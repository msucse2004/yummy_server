"""Smoke tests - API 기본 동작 확인"""
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    """헬스체크"""
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_login_fail():
    """잘못된 로그인"""
    r = client.post("/api/auth/login", json={"username": "x", "password": "y"})
    assert r.status_code == 401


def test_me_unauth():
    """인증 없이 /me"""
    r = client.get("/api/auth/me")
    assert r.status_code == 401


def test_customers_unauth():
    """인증 없이 거래처 목록"""
    r = client.get("/api/customers")
    assert r.status_code == 401
