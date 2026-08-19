from app import db


def test_a_postgres_url_builds_an_engine_without_sqlite_args(monkeypatch):
    captured = {}

    def fake_create_engine(url, **kwargs):
        captured["url"] = url
        captured["kwargs"] = kwargs

        class NeverConnects:
            def connect(self):
                raise AssertionError("no PRAGMA on a non-sqlite engine")

        return NeverConnects()

    monkeypatch.setattr(db, "create_engine", fake_create_engine)
    db._build_engine("postgresql+psycopg://x/y")
    assert captured["url"] == "postgresql+psycopg://x/y"
    assert captured["kwargs"] == {}
