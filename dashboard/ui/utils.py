from nicegui import ui


def notify_for_client(client, message, **kwargs):
    with client:
        ui.notify(message, **kwargs)