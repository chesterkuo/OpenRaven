import pytest


def test_derive_key_deterministic():
    from openraven.sync.crypto import derive_key
    salt = b"\x00" * 16
    key1 = derive_key("mypassphrase", salt)
    key2 = derive_key("mypassphrase", salt)
    assert key1 == key2
    assert len(key1) == 32


def test_derive_key_different_salt():
    from openraven.sync.crypto import derive_key
    key1 = derive_key("mypassphrase", b"\x00" * 16)
    key2 = derive_key("mypassphrase", b"\x01" * 16)
    assert key1 != key2


def test_encrypt_decrypt_roundtrip():
    from openraven.sync.crypto import encrypt_blob, decrypt_blob
    plaintext = b"Hello, this is secret knowledge base data!" * 100
    ciphertext, salt, iv = encrypt_blob(plaintext, "mypassphrase")
    assert ciphertext != plaintext
    assert len(salt) == 16
    assert len(iv) == 12
    result = decrypt_blob(ciphertext, "mypassphrase", salt, iv)
    assert result == plaintext


def test_decrypt_wrong_passphrase():
    from openraven.sync.crypto import encrypt_blob, decrypt_blob
    plaintext = b"Secret data"
    ciphertext, salt, iv = encrypt_blob(plaintext, "correct")
    with pytest.raises(ValueError, match="passphrase"):
        decrypt_blob(ciphertext, "wrong", salt, iv)


def test_encrypt_produces_different_output_each_time():
    from openraven.sync.crypto import encrypt_blob
    plaintext = b"Same data"
    ct1, salt1, iv1 = encrypt_blob(plaintext, "pass")
    ct2, salt2, iv2 = encrypt_blob(plaintext, "pass")
    assert salt1 != salt2 or iv1 != iv2
    assert ct1 != ct2
