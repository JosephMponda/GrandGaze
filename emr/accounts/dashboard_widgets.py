"""
Dashboard widget registry (Engineer A spec §4).

Each engineer's app registers widgets here instead of Engineer A hardcoding
knowledge of every other app. A widget is a dict:
    {"title": str, "url_name": str, "roles": [group names], "icon": str}

Other apps do, at import time (e.g. in their apps.py `ready()`):

    from accounts.dashboard_widgets import register_widget
    register_widget(title="Today's Lab Orders", url_name="laboratory:queue",
                     roles=["LabTech"], icon="flask")
"""
_WIDGETS = []


def register_widget(*, title: str, url_name: str, roles: list[str], icon: str = ""):
    _WIDGETS.append({"title": title, "url_name": url_name, "roles": roles, "icon": icon})


def widgets_for_user(user) -> list[dict]:
    if user.is_superuser:
        return list(_WIDGETS)
    user_groups = set(user.groups.values_list("name", flat=True))
    return [w for w in _WIDGETS if user_groups.intersection(w["roles"])]
