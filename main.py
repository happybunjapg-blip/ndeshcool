import flet as ft
from app import WaterStationApp


def main(page: ft.Page):
    page.window_width = 390
    page.window_height = 844
    page.window_resizable = False
    page.update()
    WaterStationApp(page)


if __name__ == "__main__":
    ft.run(main, view=ft.AppView.FLET_APP)
