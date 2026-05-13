def test_package_imports():
    import first_run_wizard

    assert first_run_wizard.SetupStep is not None
    assert first_run_wizard.registry is not None


def test_appconfig_loads():
    from django.apps import apps

    config = apps.get_app_config("first_run_wizard")
    assert config.name == "first_run_wizard"


def test_builtin_admin_step_is_registered():
    from first_run_wizard.registry import registry

    step = registry.get("admin_user")
    assert step.name == "admin_user"
    assert step.order == 0
