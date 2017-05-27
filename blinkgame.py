# imports
import tkinter as tk
import argparse
import math

import threading
import sys
import time

from pythonosc import dispatcher
from pythonosc import osc_server

# Variables to hold dimensions:
WIDTH = 300
HEIGHT = 500
D_ZONE_HEIGHT = 50

# Blink control parameters
DEL_P_PER = 200
blink_intensity_func = lambda blink_int, baseline_int : abs(blink_int - baseline_int) / baseline_int
DT = 0.1

# Mouse testing variables
TEST_MODE = True
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

# Methods for handling the blinking
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
        if baseline is not None and moving_avg < 0.975 * baseline:
            n_blinks += 1
            # print("Blink #{}. Avg = {:.2f}".format(n_blinks, moving_avg))
            if game is not None:
                # print("blink")
                game.onBlink(blink_intensity_func(moving_avg, baseline))
    
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

        server = osc_server.ThreadingOSCUDPServer(
            (args.ip, args.port), dispat)
        
        # Start collecting the staring data
        print("Serving on {}".format(server.server_address))
        server.serve_forever()

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
        
        # Make frame
        self.frame=tk.Frame(bg="black")
        self.frame.pack();
        
        # Pack canvas
        self.canvas=tk.Canvas(self.frame, bg="black",width=WIDTH,height=HEIGHT)
        
        # Draw the forbidden zone
        danger_zone =\
            self.canvas.create_rectangle(0, 0, WIDTH+5, D_ZONE_HEIGHT, fill='red')
        # self.d_zone_text = tk.Text(self.frame, bg='red', width=WIDTH, height=40)
        # self.d_zone_text.insert(tk.END, 'Danger')
        self.canvas.pack()
        self.ball=None # Initialize the ball
        
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
        
        self.x=150
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
        self.run()
        
    def paint(self):
        """
        Function to repaint the screen
        """
        
        self.canvas.delete(self.ball)

        if self.time//100 <= 120: # time is in ms
            if self.y <= D_ZONE_HEIGHT:
                self.lost()

            if self.y <= HEIGHT:
                self.ball=self.canvas.create_oval(self.x-10*self.size,
                                             self.y-10*self.size,self.x+10*self.size,
                                             self.y+10*self.size, fill="white")
            else:
                self.lost()
         
        else:
            self.clock['text']="Time's up"
            self.end()
            
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

# Start up the server
t = threading.Thread(target=start_server)
t.daemon = True
t.start()

# Start the game
print("Starting game")
KeepUpGame()
