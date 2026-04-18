from doobielogic.admin_auth import verify_admin_password


def test_verify_admin_password_bcrypt():
    admins = {
        "God": "$2b$12$I9nkXct74SUatWQTBRqPcOZ8SQppWtwpZqAVoUukKPDw0/GnhaW6C"
    }
    assert verify_admin_password("God", "Major420", admins) is True
    assert verify_admin_password("God", "wrong", admins) is False


def test_verify_admin_password_plaintext_fallback():
    admins = {"localadmin": "devpass"}
    assert verify_admin_password("localadmin", "devpass", admins) is True
    assert verify_admin_password("localadmin", "nope", admins) is False
