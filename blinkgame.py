# imports
import tkinter as tk
import argparse
import math

import threading
import sys
import subprocess
import time
import random

from pythonosc import dispatcher
from pythonosc import osc_server

# Start the muse connection process
# subprocess.call('muse-io --osc osc.udp://localhost:5000, --device Muse-9F6A')

# Variables to hold dimensions:
WIDTH = 800
HEIGHT = 500
D_ZONE_HEIGHT = 50

# Blink control parameters
DEL_P_PER = 200
blink_intensity_func = lambda blink_int, baseline_int : abs(blink_int - baseline_int) / baseline_int
DT = 0.1
VX = 5

# Mouse testing variables
TEST_MODE = False
MOUSE_INTENSITY = .15

# Variables to hold blinking stuff
global n, moving_avg, N_REQ, app, is_baseline,\
    baseline_list, baseline, n_blinks, game
game = None
app = None
n_blinks = 0
baseline_list = None
is_baseline = False
baseline = 850. # default baseline
N_REQ = 35
n = 0
moving_avg = 0.

global n_jaw, jaw_list
n_jaw = 0
jaw_sum = 0
jaw_list = []
N_REQ_JAW = 5

# Methods for handling the blinking and jaw clenching
def eeg_handler(unused_addr, args, ch1, ch2, ch3, ch4):
    global n, moving_avg, N_REQ, is_baseline, baseline_list, n_blinks, game
    if is_baseline:
        baseline_list.append(ch1)
    elif n < N_REQ:
        moving_avg += ch1
        n += 1
    else:
        moving_avg /= n
        n = 0
        # print(moving_avg)
        if baseline is not None and game is not None:
            if moving_avg < 0.975 * baseline:
                # print("Blink #{}. Avg = {:.2f}".format(n_blinks, moving_avg))
                if game is not None and game.RUN:
                    game.onBlink(blink_intensity_func(moving_avg, baseline))
            elif game.PAUSED:
                if moving_avg > 1.1 * baseline:
                    game.destroy()
                
def jaw_handler(addr, args, is_clench):
    global game, n_jaw, jaw_sum, N_REQ_JAW
    if n_jaw < N_REQ_JAW:
        n_jaw += 1
        jaw_sum += int(is_clench)
    else:
        avg = jaw_sum / n_jaw
        print(avg)
        if avg > 0.6:
            game.pause()  
        n_jaw = 0
        jaw_sum = 0
    
def get_no_blink_baseline(start=False):
    """
    Method that gets the baseline intensity of no blinking
    """
    count_down_str = "\rStart staring in {} s"
    count_down = 5
    for i in range(count_down): 
        sys.stdout.write(count_down_str.format(count_down-i))
        sys.stdout.flush()
        time.sleep(1)    

    print("\nStare!\n")
    global is_baseline, baseline_list, baseline
    baseline_list = []
    is_baseline = True

    count_up  = 6
    count_up_str = "\rKeep staring for {:>2} s"
    for i in range(count_up): 
        sys.stdout.write(count_up_str.format(count_up-i))
        sys.stdout.flush()
        time.sleep(1)
    print("\nDone!")
    is_baseline = False
    if len(baseline_list) > 0:
        baseline = sum(baseline_list) / float(len(baseline_list))
        print("Baseline is {}".format(baseline))
    else:
        print("No baseline detected. Using previous baseline of {}".format(baseline))
        
def start_server():
    """
    Code that starts the server
    """
    if __name__ == "__main__":
        parser = argparse.ArgumentParser()
        parser.add_argument("--ip",
                            default="127.0.0.1",
                            help="The ip to listen on")
        parser.add_argument("--port",
                            type=int,
                            default=5000,
                            help="The port to listen on")
        args = parser.parse_args()

        dispat = dispatcher.Dispatcher()
        dispat.map("/debug", print)
        dispat.map("/muse/eeg", eeg_handler, "EEG")
        dispat.map("/muse/elements/jaw_clench", jaw_handler, "elem")

        server = osc_server.ThreadingOSCUDPServer(
            (args.ip, args.port), dispat)
        
        # Start collecting the staring data
        print("Serving on {}".format(server.server_address))
        server.serve_forever()
        
        
# Class for holding rectanges
class Rect:
    def __init__(self, x1, y1, x2, y2):
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2

# Class to actually hold the game
class KeepUpGame:
    """
    Class to hold an instance of the game
    """
    def __init__(self):
        """
        Initializes game frame and such
        """
        
        # make self global
        global game
        game = self
    
        # Make root
        self.root=tk.Tk()
        self.RUN=False
        self.PAUSED = False
        
        # Make frame
        self.frame=tk.Frame(bg="black")
        self.frame.pack();
        
        # Pack canvas
        self.canvas=tk.Canvas(self.frame, bg="black",width=WIDTH,height=HEIGHT)
        self.canvas.pack()
        self.ball=None # Initialize the ball
        
        # Sample rectangles
        # self.canvas.create_rectangle(WIDTH/2, 0, 20, 100, fill='yellow')
        
        # Put infor buttons
        self.clock=tk.Label(self.frame, bg="black", fg="white")
        self.clock.pack()
        self.h_box=tk.Label(self.frame, bg="black", fg="white")
        self.h_box.pack()
        self.score_box = tk.Label(self.frame, bg="black", fg="white")
        self.score_box.pack()
        self.button=tk.Button(self.frame, bg="black", fg="white", text="Click to start",command=self.start)
        self.button.pack()
        self.blink_calib=tk.Button(self.frame, bg="black", fg="white", text="Blink baseline",command=get_no_blink_baseline)
        self.blink_calib.pack()
        
        # Paint screen
        # self.paint()
        
        # Run the main loop
        self.root.mainloop()
        
    def start(self):
        """
        Function to start the game
        """       
        self.time=0
        self.RUN=True
        self.PAUSED = False
        
        self.x=0
        self.y=HEIGHT / 2
        self.tempx=self.x
        self.tempy=self.y
        
        self.g = 4. # level of gravity. Positive direction is up
        self.m = 1. # mass of ball
        self.v = 0.

        # not sure what this does
        self.size = 3 # track the current size
        if TEST_MODE:
            print('test mode')
            self.canvas.bind("<ButtonPress-1>", self.onMClick)
            
        # Set rectangles
        self.rects = []
        self.run()
        
    def paint(self):
        """
        Function to repaint the screen
        """
        
        self.canvas.delete(tk.ALL)
        
        # Draw rectangles
        lost = False
        # print("Self: {}, {}".format(self.x, self.y))
        for rect in self.rects:
            x_draw = rect.x1-self.x+WIDTH/2 
            self.canvas.create_rectangle(x_draw, rect.y1,
                                         rect.x2-rect.x1+x_draw, rect.y2, fill='red')
            # Check if it was in the rectange
            # print("Rect: ({}, {}), ({}, {})".format(rect.x1, rect.y1, rect.x2, rect.y2))
            if self.x <= rect.x2 and self.x >= rect.x1 and\
                self.y >= rect.y1 and self.y <= rect.y2:
                    print("LOST!!")
                    lost = True
                                        


        self.ball=self.canvas.create_oval(WIDTH/2-10*self.size,
                                     self.y-10*self.size,WIDTH/2+10*self.size,
                                     self.y+10*self.size, fill="white")
        if self.y >= HEIGHT or lost:
            self.lost()         
            
    def onBlink(self, intensity):
        """
        Event to handle mouse clicks
        
        Will be overridden for the blinking
        """
        if self.RUN:
            # Gives a momentum burst proportional 
            del_p = -DEL_P_PER*intensity # kg m/s
            self.v += del_p / self.m
            
    def onMClick(self, event):
        """
        Dummy method for using the mouse instead of the MUSE
        """
        self.onBlink(MOUSE_INTENSITY)   
        
    def move(self, dt):
        """
        Moves the ball
        """
        self.y += self.v * dt
        self.v += self.g * dt
        if self.y < 0:
            self.y = 0
            self.v = 0
        self.x += VX
        self.update_rects()
        
    def update_rects(self):
        new_rects = []
        for rec in self.rects:
            if rec.x2 > self.x - WIDTH/2:
                new_rects.append(rec)
        
        rand = random.random()
        new = False
        if self.x % 500 == 0 and rand > 0.2:
            new = True
        elif self.x % 200 == 0 and rand > 0.5:
            new = True
        if new:
            x1 = self.x+WIDTH
            y1 = random.random()*HEIGHT
            new_rects.append(Rect(x1, y1, x1+WIDTH/8, y1+200))
                                      
        self.rects = new_rects
    
    def run(self):
        """
        Runs the game
        """
        if self.RUN is True:
            self.time += 1
            self.clock['text']="TIME:" + str(self.time//100)
            self.h_box['text'] = "Height: {:0>4.0f}".format(HEIGHT - self.y)
            self.update_score()
            self.move(DT)
            self.paint()
            self.root.after(10, self.run)
            
    def update_score(self):
        """
        Method to update score_box
        """
        self.score_box['text'] = "Score: {:0>4}".format(self.time // 10)
            
    def lost(self):
        """
        Method meant to handle loss of the game
        """
        self.clock['text']="You lost"
        self.end()
            
    def end(self):
        """
        Ends the game
        """
        self.RUN=False
        self.update_score()
        if TEST_MODE:
            self.canvas.unbind("<ButtonPress-1>")
            
    def destroy(self):
        if not self.RUN and self.PAUSED:
            self.rects = []
            self.paint()
            
    def pause(self):
        if not self.PAUSED and self.RUN:
            self.PAUSED = True
            self.RUN = False
        else:
            self.PAUSED = False
            self.RUN = True

# Start up the server
t = threading.Thread(target=start_server)
t.daemon = True
t.start()

# Start the game
print("Starting game")
KeepUpGame()
