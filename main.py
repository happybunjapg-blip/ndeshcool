import flet as ft
from app import WaterStationApp


def main(page: ft.Page):
    WaterStationApp(page)


if __name__ == "__main__":
    ft.run(main, view=ft.AppView.WEB_BROWSER)
