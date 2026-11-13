from pathlib import Path

from steady.app_info import APP_DESCRIPTION, APP_VERSION, AUTHOR_NAME, CONTACT_EMAIL


def test_public_app_metadata_is_configured_and_versioned():
    assert APP_VERSION == "1.0.0"
    assert AUTHOR_NAME.strip()
    assert APP_DESCRIPTION.strip()
    assert isinstance(CONTACT_EMAIL, str)


def test_settings_page_exposes_clickable_contact_when_email_is_set():
    source = (
        Path(__file__).parents[1]
        / "src"
        / "steady"
        / "ui"
        / "pages"
        / "settings_page.py"
    ).read_text(encoding="utf-8")
    assert "About & contact" in source
    assert "CONTACT_EMAIL" in source
    assert 'href="mailto:{mailto}"' in source


def test_application_sets_version_and_window_icon():
    source = (Path(__file__).parents[1] / "src" / "steady" / "app.py").read_text(encoding="utf-8")
    assert "app.setApplicationVersion(APP_VERSION)" in source
    assert "steady_icon.png" in source


def test_package_version_is_derived_from_app_info():
    import tomllib

    project_file = Path(__file__).parents[1] / "pyproject.toml"
    project = tomllib.loads(project_file.read_text(encoding="utf-8"))
    assert "version" in project["project"]["dynamic"]
    assert project["tool"]["setuptools"]["dynamic"]["version"]["attr"] == "steady.app_info.APP_VERSION"


def test_public_contact_email_is_configured_for_release():
    from steady.app_info import CONTACT_EMAIL

    assert CONTACT_EMAIL == "kartikjbsky@gmail.com"
