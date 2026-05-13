# -*- coding: utf-8 -*-
"""
保持系統活躍腳本
功能：每5分鐘隨機移動滑鼠，防止系統進入休眠
"""
import random
import time
import ctypes

# Define ctypes structures
class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

def move_mouse():
    """隨機移動滑鼠"""
    # Get current cursor position
    pt = POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    
    # Calculate random offset (-100 to +100 pixels)
    dx = random.randint(-100, 100)
    dy = random.randint(-100, 100)
    
    # Move mouse to new position
    new_x = pt.x + dx
    new_y = pt.y + dy
    
    ctypes.windll.user32.SetCursorPos(new_x, new_y)
    
    print(f"Mouse moved: ({pt.x},{pt.y}) -> ({new_x},{new_y})")

if __name__ == '__main__':
    move_mouse()