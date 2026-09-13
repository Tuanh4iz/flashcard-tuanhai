import pyautogui
import time

# Đợi vài giây để bạn chuyển sang cửa sổ game
time.sleep(5)

# Lặp lại việc gửi tin nhắn
for i in range(10):
    # 1. Click vào ô chat (bạn cần xác định tọa độ chính xác trên màn hình của mình)
    pyautogui.click(x=100, y=200)
    time.sleep(0.5)

    # 2. Nhập tin nhắn
    pyautogui.write(f"Tin nhắn tự động {i+1}")
    time.sleep(0.5)

    # 3. Nhấn Enter để gửi
    pyautogui.press('enter')
    time.sleep(1)