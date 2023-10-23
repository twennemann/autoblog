import tkinter as tk
import voice_recognition as vr

window = tk.Tk()
window.title("Speech Recognition")

window.label = tk.Label(window, text="Press the button to start recording")
window.label.pack(pady=20)

window.record_button = tk.Button(window, text="⬤", 
                                 command=vr.start_stop_recording(window),
                                 bg="gray", font=("Arial", 20))
window.record_button.pack(pady=20)

window.mainloop()