"""Shared Kivy screen helpers."""

from __future__ import annotations

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.dropdown import DropDown
from kivy.uix.gridlayout import GridLayout
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.uix.scrollview import ScrollView

from polyglot_site_translator.presentation.frontend_shell import FrontendShell
from polyglot_site_translator.presentation.kivy.widgets.common import (
    AppButton,
    SurfaceBoxLayout,
    WrappedLabel,
    apply_theme_to_widget_tree,
)


class BaseShellScreen(Screen):  # type: ignore[misc]
    """Shared screen scaffold with a contextual application menu."""

    def __init__(
        self,
        *,
        screen_name: str,
        title: str,
        shell: FrontendShell,
        manager_ref: ScreenManager,
        subtitle: str = "",
    ) -> None:
        super().__init__(name=screen_name)
        self._shell = shell
        self._manager_ref = manager_ref
        self._menu_dropdown: DropDown | None = None

        self._container = SurfaceBoxLayout(
            orientation="vertical",
            spacing=0,
            padding=0,
            background_role="app_background",
        )
        self._header = SurfaceBoxLayout(
            orientation="horizontal",
            spacing=16,
            padding=16,
            size_hint_y=None,
            height=88,
            background_role="header_background",
        )
        self._title_block = BoxLayout(orientation="vertical", spacing=2)
        self._app_title = WrappedLabel(
            text="Polyglot Site Translator",
            font_size=14,
            color_role="text_muted",
        )
        self._screen_title = WrappedLabel(text=title, font_size=24, bold=True)
        self._screen_subtitle = WrappedLabel(
            text=subtitle,
            font_size=14,
            color_role="text_muted",
        )
        self._title_block.add_widget(self._app_title)
        self._title_block.add_widget(self._screen_title)
        self._title_block.add_widget(self._screen_subtitle)
        self._menu_button = AppButton(
            text="Application Menu",
            primary=False,
            size_hint=(None, None),
            width=188,
        )
        self._menu_button.bind(on_release=self._open_application_menu)
        self._header.add_widget(self._title_block)
        self._header.add_widget(self._menu_button)

        self._scroll = ScrollView(scroll_type=["bars", "content"], bar_width=8)
        self._content = GridLayout(cols=1, spacing=16, padding=20, size_hint_y=None)
        self._content.bind(minimum_height=self._content.setter("height"))
        self._scroll.add_widget(self._content)

        self._error_card = SurfaceBoxLayout(
            orientation="vertical",
            padding=14,
            size_hint_y=None,
            height=0,
            background_role="error_background",
            border_role="error_background",
        )
        self._error_label = WrappedLabel(text="", color_role="error_text", font_size=14)
        self._error_card.add_widget(self._error_label)

        self._container.add_widget(self._header)
        self._container.add_widget(self._scroll)
        self._container.add_widget(self._error_card)
        self.add_widget(self._container)

    def set_screen_copy(self, *, title: str, subtitle: str) -> None:
        """Update the screen title and subtitle."""
        self._screen_title.text = title
        self._screen_subtitle.text = subtitle

    def clear_content(self) -> None:
        """Remove widgets from the content area."""
        self._content.clear_widgets()

    def add_nav_button(self, text: str, callback: object, *, primary: bool = True) -> AppButton:
        """Add a styled button to the content area."""
        button = AppButton(text=text, primary=primary)
        button.bind(on_release=callback)
        self._content.add_widget(button)
        return button

    def update_error_label(self) -> None:
        """Refresh the controlled error area."""
        message = self._shell.latest_error or ""
        self._error_label.text = message
        self._error_card.height = 0 if not message else self._error_label.height + 20
        self._error_card.opacity = 0 if not message else 1

    def refresh(self) -> None:
        """Refresh screen content when the route changes."""

    def on_pre_enter(self, *args: object) -> None:
        """Refresh content before the screen becomes visible."""
        super().on_pre_enter(*args)
        self.refresh()

    def show_route(self, route_name: str) -> None:
        """Switch the ScreenManager to a given route."""
        if self._manager_ref.current == route_name:
            self.refresh()
            return
        self._manager_ref.current = route_name

    def apply_theme(self) -> None:
        """Apply the active theme to the static screen scaffold."""
        apply_theme_to_widget_tree(self._container)

    def _open_application_menu(self, *_args: object) -> None:
        self._shell.open_application_menu()
        dropdown = DropDown(auto_width=False, width=340)
        for section in self._shell.navigation_menu.sections:
            header = AppButton(
                text=section.title,
                primary=False,
                size_hint_y=None,
                height=40,
                disabled=True,
            )
            dropdown.add_widget(header)
            for item in section.items:
                entry = AppButton(
                    text=f"{item.title}\n{item.description}",
                    primary=False,
                    size_hint_y=None,
                    height=64,
                    disabled=not item.is_enabled,
                )
                entry.bind(on_release=lambda _widget, key=item.key: self._open_menu_route(key))
                dropdown.add_widget(entry)
        self._menu_dropdown = dropdown
        dropdown.open(self._menu_button)

    def _open_menu_route(self, route_key: str) -> None:
        self._shell.open_route_from_menu(route_key)
        if self._menu_dropdown is not None:
            self._menu_dropdown.dismiss()
        self.show_route(_route_to_screen_name(route_key))


def _route_to_screen_name(route_key: str) -> str:
    """Map route keys into Kivy screen names."""
    return route_key.replace("-", "_")
