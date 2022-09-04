import tkinter as tk
import GUIModule
import AudioModule 
import DBModule
import numpy
from timeit import default_timer as timer

# Create the tkinter parent class
root = tk.Tk()

# Load up the interface from the GUIModule
GUIModule.MainApplication(root, bg='navy').pack(side = tk.TOP, fill = tk.BOTH, expand = tk.YES)

# Loop the form so it stays open
root.mainloop()
