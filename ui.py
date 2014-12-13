#!/usr/bin/env python3

import tacui
import local
import threading
import traceback
from tacui import tk
import pyperclip

ui = tacui.SelectingTacUI()
ui.enabled = False

client = local.Client()

def _finish_setup():
    ui.input.enabled = False
    ui.input.decorate = lambda text: "Loading..."
    thread = threading.Thread(target=launch)
    thread.daemon = True
    thread.start()

def launch(first=True):
    def stop(evt):
        client.stop_server()
        print("sysexit")
        ui.exit()
    ui.input.bind("<Control-c>", stop)

    ui.input.text = ""
    ui.clear()
    if not client.is_logged_in():
        if not first:
            ui.add("Invalid Password")
        ui.may_show = lambda e: True
        ui.input.enabled = True
        ui.input.decorate = lambda text: "Password: " + ("*" * len(text))
        def login():
            password = ui.input.text
            try:
                client.log_in(password)
            except:
                traceback.print_exc()
            launch(False)
        ui.input.enter = login
        return

    ui.input.enabled = True
    ui.input.decorate = lambda text: "> " + text
    def may_show(text):
        text = text.lower()
        search = ui.input.text.lower()
        if len(search) > 0 and search[-1] == "~":
            search = search[:-1]
        terms = search.split(" ")
        for term in terms:
            if term not in text:
                return False
        return True
    ui.may_show = may_show
    for password in client.list_password_names():
        ui.add(password, True, "  " + password)
    ui.enabled = True
    ui._update_ui()
    def use():
        if len(ui.input.text) > 0 and ui.input.text[0] == "+":
            entry = ui.input.text[1:]
            password = ""
            edit = True
        else:
            entry = ui.selected_item
            password = client.get_password(entry)
            edit = len(ui.input.text) > 0 and ui.input.text[-1] == "~"
        if edit:
            ui.unfocus = lambda: ui.close()

            ctx = tk.Tk()
            ctx.configure(background=ui.bg)
            ctx.attributes("-type", "dialog") # WM hint to let window float
            ctx.minsize(width=500, height=400)
            ctx.maxsize(width=500, height=400)
            ctx.resizable(width=tk.FALSE, height=tk.FALSE)
            area = tk.Text(
                ctx,
                fg=ui.fg,
                bg=ui.bg,
                font=tacui.FONT,
                borderwidth=0,
                insertbackground=ui.fg,
                highlightthickness=0,
                padx=0,
                pady=0
            )
            area.pack()
            area.insert(tk.END, password)
            area.focus_set()
            def update_title():
                edited = area.get(1.0, tk.END).strip() != password.strip()
                ctx.title(entry + ("*" if edited else ""))
            update_title()
            def key_released(evt):
                update_title()
            area.bind("<KeyRelease>", key_released)
            def save(evt):
                print("Saving")
                nonlocal password
                txt = area.get(1.0, tk.END)
                client.add_password(entry, txt)
                password = txt
            area.bind("<Control-s>", save)
            ctx.mainloop()
        else:
            pyperclip.copy(password.split("\n")[0])
            ui.exit()
    ui.input.enter = use

ui.on_finish_setup(_finish_setup)

ui.open()
