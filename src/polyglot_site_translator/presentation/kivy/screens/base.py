"""Shared Kivy screen helpers."""

from __future__ import annotations

from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.dropdown import DropDown
from kivy.uix.gridlayout import GridLayout
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.uix.scrollview import ScrollView

from polyglot_site_translator.presentation.frontend_shell import FrontendShell
from polyglot_site_translator.presentation.kivy.design_tokens import (
    COMPONENT_SIZES,
    SPACING,
    TYPOGRAPHY,
)
from polyglot_site_translator.presentation.kivy.widgets.common import (
    AppButton,
    SurfaceBoxLayout,
    WrappedLabel,
    apply_theme_to_widget_tree,
)
from polyglot_site_translator.presentation.ui_localization import tr


class BaseShellScreen(Screen):  # type: ignore[misc]
    """Shared screen scaffold with a contextual application menu.

    Attributes:
        None: This type does not declare class-level attributes.
    """

    def __init__(
        self,
        *,
        screen_name: str,
        title: str,
        shell: FrontendShell,
        manager_ref: ScreenManager,
        subtitle: str = "",
    ) -> None:
        """Build the common scaffold shared by all shell-managed screens.

        Args:
            self:
                Value supplied to this callable.
            screen_name:
                Value supplied to this callable.
            title:
                Value supplied to this callable.
            shell:
                Value supplied to this callable.
            manager_ref:
                Value supplied to this callable.
            subtitle:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
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
            spacing=SPACING.lg,
            padding=SPACING.lg,
            size_hint_y=None,
            height=COMPONENT_SIZES.header_height,
            background_role="header_background",
        )
        self._title_block = BoxLayout(orientation="vertical", spacing=SPACING.xs)
        self._app_title = WrappedLabel(
            text=tr("Polyglot Site Translator"),
            font_size=TYPOGRAPHY.caption,
            color_role="text_muted",
        )
        self._title_msgid = title
        self._subtitle_msgid = subtitle
        self._screen_title = WrappedLabel(
            text=tr(title),
            font_size=TYPOGRAPHY.screen_title,
            bold=True,
        )
        self._screen_subtitle = WrappedLabel(
            text=tr(subtitle),
            font_size=TYPOGRAPHY.caption,
            color_role="text_muted",
        )
        self._title_block.add_widget(self._app_title)
        self._title_block.add_widget(self._screen_title)
        self._title_block.add_widget(self._screen_subtitle)
        self._menu_button = AppButton(
            text=tr("Application Menu"),
            primary=False,
            size_hint=(None, None),
            width=188,
        )
        self._menu_button.bind(on_release=self._open_application_menu)
        self._header.add_widget(self._title_block)
        self._header.add_widget(self._menu_button)

        self._scroll = ScrollView(scroll_type=["bars", "content"], bar_width=8)
        self._content = GridLayout(
            cols=1,
            spacing=SPACING.lg,
            padding=SPACING.xl,
            size_hint_y=None,
        )
        self._content.bind(minimum_height=self._content.setter("height"))
        self._scroll.add_widget(self._content)

        self._error_card = SurfaceBoxLayout(
            orientation="vertical",
            padding=SPACING.lg,
            size_hint_y=None,
            height=0,
            background_role="error_background",
            border_role="error_background",
        )
        self._error_label = WrappedLabel(
            text="",
            color_role="error_text",
            font_size=TYPOGRAPHY.caption,
        )
        self._error_card.add_widget(self._error_label)

        self._container.add_widget(self._header)
        self._container.add_widget(self._scroll)
        self._container.add_widget(self._error_card)
        self.add_widget(self._container)

    def set_screen_copy(self, *, title: str, subtitle: str) -> None:
        """Update the screen title and subtitle.

        Args:
            self:
                Value supplied to this callable.
            title:
                Value supplied to this callable.
            subtitle:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        self._screen_title.text = tr(title)
        self._screen_subtitle.text = tr(subtitle)
        self._title_msgid = title
        self._subtitle_msgid = subtitle

    def clear_content(self) -> None:
        """Remove widgets from the content area.

        Args:
            self:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        self._content.clear_widgets()

    def add_nav_button(
        self, text: str, callback: object, *, primary: bool = True
    ) -> AppButton:
        """Add a styled button to the content area.

        Args:
            self:
                Value supplied to this callable.
            text:
                Value supplied to this callable.
            callback:
                Value supplied to this callable.
            primary:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        button = AppButton(text=text, primary=primary)
        button.bind(on_release=callback)
        self._content.add_widget(button)
        return button

    def update_error_label(self) -> None:
        """Refresh the controlled error area.

        Args:
            self:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        message = self._shell.latest_error or ""
        self._error_label.text = message
        self._error_card.height = 0 if not message else self._error_label.height + 20
        self._error_card.opacity = 0 if not message else 1

    def refresh(self) -> None:
        """Refresh screen content when the route changes.

        Args:
            self:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """

    def on_pre_enter(self, *args: object) -> None:
        """Refresh content before the screen becomes visible.

        Args:
            self:
                Value supplied to this callable.
            *args:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        super().on_pre_enter(*args)
        self.refresh()

    def show_route(self, route_name: str) -> None:
        """Switch the ScreenManager to a given route.

        Args:
            self:
                Value supplied to this callable.
            route_name:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        if self._manager_ref.current == route_name:
            self.refresh()
            return
        self._manager_ref.current = route_name

    def apply_theme(self) -> None:
        """Apply the active theme to the static screen scaffold.

        Args:
            self:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        apply_theme_to_widget_tree(self._container)
        self._app_title.text = tr("Polyglot Site Translator")
        self._screen_title.text = tr(self._title_msgid)
        self._screen_subtitle.text = tr(self._subtitle_msgid)
        self._menu_button.text = tr("Application Menu")

    def _open_application_menu(self, *_args: object) -> None:
        """Open application menu.

        Args:
            self:
                Value supplied to this callable.
            *_args:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        self._shell.open_application_menu()
        dropdown = DropDown(
            auto_width=False,
            width=COMPONENT_SIZES.menu_width,
            max_height=max(Window.height - COMPONENT_SIZES.header_height, 240),
        )
        for section in self._shell.navigation_menu.sections:
            header = AppButton(
                text=section.title,
                primary=False,
                size_hint_y=None,
                height=COMPONENT_SIZES.compact_button_height,
                disabled=True,
            )
            dropdown.add_widget(header)
            for item in section.items:
                entry = AppButton(
                    text=f"{item.title}\n{item.description}",
                    primary=False,
                    size_hint_y=None,
                    height=COMPONENT_SIZES.button_height + 20,
                    disabled=not item.is_enabled,
                )
                entry.bind(
                    on_release=lambda _widget, key=item.key: self._open_menu_route(key)
                )
                dropdown.add_widget(entry)
        self._menu_dropdown = dropdown
        if self._menu_button.get_parent_window() is None:
            return
        dropdown.open(self._menu_button)

    def _open_menu_route(self, route_key: str) -> None:
        """Open menu route.

        Args:
            self:
                Value supplied to this callable.
            route_key:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        self._shell.open_route_from_menu(route_key)
        if self._menu_dropdown is not None:
            self._menu_dropdown.dismiss()
        self.show_route(_route_to_screen_name(route_key))


def _route_to_screen_name(route_key: str) -> str:
    """Map route keys into Kivy screen names.

    Args:
        route_key:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    return route_key.replace("-", "_")
