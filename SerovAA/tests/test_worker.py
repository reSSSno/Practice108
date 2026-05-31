import pytest
from worker.worker import generate_password

def test_generate_password_default():
    pwd = generate_password(12, True, True)
    assert len(pwd) == 12
    # должна содержать хотя бы одну букву и одну цифру (если digits true)
    assert any(c.isalpha() for c in pwd)
    assert any(c.isdigit() for c in pwd)

def test_generate_password_no_digits():
    pwd = generate_password(8, use_digits=False, use_special=False)
    assert len(pwd) == 8
    assert not any(c.isdigit() for c in pwd)
    assert not any(c in '!@#$%^&*()' for c in pwd)

def test_generate_password_only_letters():
    pwd = generate_password(10, use_digits=False, use_special=False)
    assert pwd.isalpha()

def test_generate_password_with_special():
    pwd = generate_password(15, use_digits=False, use_special=True)
    specials = set('!@#$%^&*()')
    assert any(c in specials for c in pwd)
