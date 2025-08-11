def test_import_app():
    # Smoke test: ensure the application module can be imported
    import importlib
    mod = importlib.import_module('app.main')
    assert hasattr(mod, 'app')
