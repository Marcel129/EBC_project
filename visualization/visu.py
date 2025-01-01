import asyncio
import dearpygui.dearpygui as dpg
from dearpygui_async import DearPyGuiAsync # import
import time

dpg.create_context()
dpg_async = DearPyGuiAsync() # initialize

width, height, channels, data = dpg.load_image("schemat_paint.png")
width2, height2, channels2, data2 = dpg.load_image("schemat_paint_copy.png")

def my_callback(sender, app_data):
    dpg.set_value("texture_tag", value = data2)

def my_callback2(sender, app_data):
    dpg.set_value("texture_tag", value = data)

async def my_callback3(sender, app_data):
    while True:
        print("Dupa")
        await asyncio.sleep(1)

with dpg.texture_registry(show=True):
    dpg.add_dynamic_texture(width=width, height=height, default_value=data, tag="texture_tag")

with dpg.window(label="Tutorial"):
    dpg.add_image("texture_tag", pos=[0,100])
    dpg.add_button(label="Frist image", callback=my_callback)
    dpg.add_button(label="Second image", callback=my_callback2)
    dpg.add_button(label="Printing", callback=my_callback3)


dpg.create_viewport(title='Custom Title', width=width, height=height)
dpg.setup_dearpygui()
dpg.show_viewport()

dpg_async.run() # run; replaces `dpg.start_dearpygui()`

dpg.destroy_context()