import pytest

from doobielogic.user_management import UserStore, hash_password, verify_password


def test_password_policy_and_hash_verification():
    with pytest.raises(ValueError):
        hash_password("short")
    hashed = hash_password("long-enough-password")
    assert verify_password("long-enough-password", hashed)
    assert not verify_password("wrong-password", hashed)


def test_admin_can_create_authenticate_disable_and_reset_user(tmp_path):
    store = UserStore(sqlite_path=tmp_path / "users.db")
    user = store.create_user(
        username="Buyer.One",
        display_name="Buyer One",
        email="BUYER@EXAMPLE.COM",
        password_hash=hash_password("temporary-password"),
        role="buyer",
        created_by="admin",
    )
    assert user.normalized_username == "buyer.one"
    assert user.email == "buyer@example.com"
    assert store.authenticate("buyer.one", "temporary-password") is not None

    assert store.set_active(user.id, False, "admin")
    assert store.authenticate("Buyer.One", "temporary-password") is None
    assert store.set_active(user.id, True, "admin")
    assert store.reset_password(user.id, hash_password("replacement-password"), "admin")
    reset_user = store.get_user("buyer.one")
    assert reset_user is not None and reset_user.must_change_password
    assert store.authenticate("buyer.one", "replacement-password") is not None


def test_usernames_are_case_insensitive_and_roles_are_validated(tmp_path):
    store = UserStore(sqlite_path=tmp_path / "users.db")
    store.create_user(
        username="Operator",
        password_hash=hash_password("temporary-password"),
        role="operations",
        created_by="admin",
    )
    with pytest.raises(ValueError):
        store.create_user(
            username="operator",
            password_hash=hash_password("another-password"),
            role="operations",
            created_by="admin",
        )
    with pytest.raises(ValueError):
        store.create_user(
            username="new.user",
            password_hash=hash_password("another-password"),
            role="missing-role",
            created_by="admin",
        )


def test_custom_role_permissions_and_password_change(tmp_path):
    store = UserStore(sqlite_path=tmp_path / "users.db")
    role = store.create_role(
        name="cultivation_manager",
        display_name="Cultivation Manager",
        permissions=["chat", "upload_data"],
    )
    assert role.allows("chat")
    with pytest.raises(ValueError):
        store.create_role(name="bad_role", display_name="Bad", permissions=["manage_users"])

    user = store.create_user(
        username="grow.manager",
        password_hash=hash_password("temporary-password"),
        role=role.name,
        created_by="admin",
    )
    assert store.change_password(user.id, hash_password("permanent-password"))
    changed = store.get_user("grow.manager")
    assert changed is not None and not changed.must_change_password
    assert store.authenticate("grow.manager", "permanent-password") is not None
    assert store.set_role(user.id, "buyer", "admin")
    assert store.get_user("grow.manager").role == "buyer"
    with pytest.raises(ValueError):
        store.set_role(user.id, "missing-role", "admin")


def test_bootstrap_admin_is_idempotent(tmp_path):
    store = UserStore(sqlite_path=tmp_path / "users.db")
    password_hash = hash_password("bootstrap-password")
    first = store.ensure_bootstrap_admin("owner", password_hash)
    second = store.ensure_bootstrap_admin("OWNER", password_hash)
    assert first is not None
    assert second is not None
    assert first.id == second.id
    assert first.role == "admin"
