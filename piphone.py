# PiPhone - A DIY Cellphone based on Raspberry Pi
# This must run as root (sudo python lapse.py) due to framebuffer, etc.
#
# http://www.adafruit.com/products/998  (Raspberry Pi Model B)
# http://www.adafruit.com/products/1601 (PiTFT Mini Kit)
#
# Prerequisite tutorials: aside from the basic Rasplsbian setup and PiTFT setup
# http://learn.adafruit.com/adafruit-pitft-28-inch-resistive-touchscreen-display-raspberry-pi
#
# piphone.py by David Hunt (dave@davidhunt.ie)
# based on cam.py by Phil Burgess / Paint Your Dragon for Adafruit Industries.
# BSD license, all text above must be included in any redistribution.

import os
os.system("sudo screen -d -m wvdial")`
import atexit
import cPickle as pickle
import errno
import fnmatch
import io
import pygame
import threading
import sys
from pygame.locals import *
from subprocess import call
from time import sleep
import subprocess
from curses import ascii
import serial
import time
from TwitterBot import PyBot

# UI classes ---------------------------------------------------------------

# Icon is a very simple bitmap class, just associates a name and a pygame
# image (PNG loaded from icons directory) for each.
# There isn't a globally-declared fixed list of Icons.  Instead, the list
# is populated at runtime from the contents of the 'icons' directory.

class Icon:

    def __init__(self, name):
        self.name = name
        try:
            self.bitmap = pygame.image.load(iconPath + '/' + name + '.png')
        except:
            pass


# Reset Screen classes ---------------------------------------------------------------
def reset_screen(screen, img):
    print "loading background.."
    screen.fill((0, 0, 0))
    if img is None or img.get_height() < 320:  # Letterbox, clear background
        screen.fill(0)
    if img:
        screen.blit(img,
                    ((320 - img.get_width()) / 2,
                     (480 - img.get_height()) / 2))
    pygame.display.update()

# Button is a simple tappable screen region.  Each has:
#  - bounding rect ((X,Y,W,H) in pixels)
#  - optional background color and/or Icon (or None), always centered
#  - optional foreground Icon, always centered
#  - optional single callback function
#  - optional single value passed to callback
# Occasionally Buttons are used as a convenience for positioning Icons
# but the taps are ignored.  Stacking order is important; when Buttons
# overlap, lowest/first Button in list takes precedence when processing
# input, and highest/last Button is drawn atop prior Button(s).  This is
# used, for example, to center an Icon by creating a passive Button the
# width of the full screen, but with other buttons left or right that
# may take input precedence (e.g. the Effect labels & buttons).
# After Icons are loaded at runtime, a pass is made through the global
# buttons[] list to assign the Icon objects (from names) to each Button.

class Button:

    def __init__(self, rect, **kwargs):
        self.rect = rect  # Bounds
        self.color = None  # Background fill color, if any
        self.iconBg = None  # Background Icon (atop color fill)
        self.iconFg = None  # Foreground Icon (atop background)
        self.bg = None  # Background Icon name
        self.fg = None  # Foreground Icon name
        self.callback = None  # Callback function
        self.value = None  # Value passed to callback
        for key, value in kwargs.iteritems():
            if key == 'color':
                self.color = value
            elif key == 'bg':
                self.bg = value
            elif key == 'fg':
                self.fg = value
            elif key == 'cb':
                self.callback = value
            elif key == 'value':
                self.value = value

    def selected(self, pos):
        x1 = self.rect[0]
        y1 = self.rect[1]
        x2 = x1 + self.rect[2] - 1
        y2 = y1 + self.rect[3] - 1
        if ((pos[0] >= x1) and (pos[0] <= x2) and
                (pos[1] >= y1) and (pos[1] <= y2)):
            if self.callback:
                if self.value is None:
                    self.callback()
                else:
                    self.callback(self.value)
            return True
        return False

    def draw(self, screen):
        if self.color:
            screen.fill(self.color, self.rect)
        if self.iconBg:
            screen.blit(self.iconBg.bitmap,
                        (self.rect[0] + (self.rect[2] - self.iconBg.bitmap.get_width()) / 2,
                         self.rect[1] + (self.rect[3] - self.iconBg.bitmap.get_height()) / 2))
        if self.iconFg:
            screen.blit(self.iconFg.bitmap,
                        (self.rect[0] + (self.rect[2] - self.iconFg.bitmap.get_width()) / 2,
                         self.rect[1] + (self.rect[3] - self.iconFg.bitmap.get_height()) / 2))

    def setBg(self, name):
        if name is None:
            self.iconBg = None
        else:
            for i in icons:
                if name == i.name:
                    self.iconBg = i
                    break


# UI callbacks -------------------------------------------------------------
# These are defined before globals because they're referenced by items in
# the global buttons[] list.


def numericCallback(n):  # Pass 1 (next setting) or -1 (prev setting)
    global screenMode
    global numberstring
    global messagestring
    global phonecall
    global tweetstring

    if screenMode == 2 and n != 12:
        if n == 10:
            messagestring = ""
        else:
            messagestring = messagestring + str(n)
    elif n < 10 and screenMode == 0:
        numberstring = numberstring + str(n)
    elif n == 10 and screenMode == 0:
        # raise SystemExit()
        reset_screen(screen, img)
        screenMode = 4
    elif n == 11 and screenMode == 0:
        reset_screen(screen, img)
        screenMode = 2
    elif screenMode == 4:
        if n == 1:
            reset_screen(screen, img)
            screenMode = 0
        elif n == 2:
            reset_screen(screen, img)
            screenMode = 3
        elif n == 3:
            raise SystemExit()
        elif n == 4:
            tweetbot.work("T-Mobile", False)
    elif screenMode == 3:
        if n == 1:
            x = tweetbot.work(tweetstring, True)
            reset_screen(screen, img)
            myfont = pygame.font.SysFont("Arial", 20)
            label = myfont.render(x, 1, (255, 255, 255))
            screen.blit(label, (10, 2))
            time.sleep(10)
            reset_screen(screen, img)
            tweetstring = ""
        elif n == 0:
            tweetbot.stop_work()
        else:
            tweetstring = tweetstring + str(n)
    elif n == 12:

        if screenMode == 0:
            if len(numberstring) > 0:
                print("Calling " + numberstring);
                serialport.write("AT\r")
                response = serialport.readlines(None)
                serialport.write("ATD " + numberstring + ';\r')
                response = serialport.readlines(None)
                print response
                # phonecall = 1
                screenMode = 1
        elif screenMode == 2:
            if len(numberstring) > 0:
                print("Message " + messagestring);
                serialport.write("AT\r")
                response = serialport.readlines(None)
                serialport.write('AT+CMGS="%s"\r\n' % numberstring)
                response = serialport.readlines(None)
                serialport.write(messagestring)
                serialport.write(ascii.ctrl('z'))
                time.sleep(25)
                print serialport.readline()
                print serialport.readline()
                print serialport.readline()
                print serialport.readline()
                print
                if len(numberstring) > 0:
                    numeric = int(numberstring)
                    v[dict_idx] = numeric
                messagestring = ""
                numberstring = ""
                reset_screen(screen, img)
                screenMode = 0
        else:
            print("Hanging Up...")
            serialport.write("AT\r")
            response = serialport.readlines(None)
            serialport.write("ATH\r")
            response = serialport.readlines(None)
            print response
            screenMode = 0
            if len(numberstring) > 0:
                numeric = int(numberstring)
                v[dict_idx] = numeric
            numberstring = ""
            reset_screen(screen, img)


# Global stuff -------------------------------------------------------------

busy = False
threadExited = False
screenMode = 0  # Current screen mode; default = viewfinder
phonecall = 1
screenModePrior = -1  # Prior screen mode (for detecting changes)
iconPath = 'icons'  # Subdirectory containing UI bitmaps (PNG format)
numeric = 0  # number from numeric keypad
numberstring = ""
messagestring = ""
tweetstring = ""
tweetbot = PyBot()
motorRunning = 0
motorDirection = 0
returnScreen = 0
shutterpin = 17
motorpinA = 18
motorpinB = 27
motorpin = motorpinA
currentframe = 0
framecount = 100
settling_time = 0.2
shutter_length = 0.2
interval_delay = 0.2
dict_idx = "Interval"
v = {"Pulse": 100,
     "Interval": 3000,
     "Images": 200}

icons = []  # This list gets populated at startup

# buttons[] is a list of lists; each top-level list element corresponds
# to one screen mode (e.g. viewfinder, image playback, storage settings),
# and each element within those lists corresponds to one UI button.
# There's a little bit of repetition (e.g. prev/next buttons are
# declared for each settings screen, rather than a single reusable
# set); trying to reuse those few elements just made for an ugly
# tangle of code elsewhere.

buttons = [

    # Screen 0 for numeric input
    [Button((50, 0, 320, 60), bg='box'),
     Button((50, 80, 80, 80), bg='1', cb=numericCallback, value=1),
     Button((130, 80, 80, 80), bg='2', cb=numericCallback, value=2),
     Button((210, 80, 80, 80), bg='3', cb=numericCallback, value=3),
     Button((50, 160, 80, 80), bg='4', cb=numericCallback, value=4),
     Button((130, 160, 80, 80), bg='5', cb=numericCallback, value=5),
     Button((210, 160, 80, 80), bg='6', cb=numericCallback, value=6),
     Button((50, 240, 80, 80), bg='7', cb=numericCallback, value=7),
     Button((130, 240, 80, 80), bg='8', cb=numericCallback, value=8),
     Button((210, 240, 80, 80), bg='9', cb=numericCallback, value=9),
     Button((50, 320, 80, 80), bg='star', cb=numericCallback, value=0),
     Button((130, 320, 80, 80), bg='0', cb=numericCallback, value=0),
     Button((210, 320, 80, 80), bg='hash', cb=numericCallback, value=0),
     Button((50, 400, 80, 80), bg='message', cb=numericCallback, value=11),  # Testing MyCroft, or even messages.
     Button((130, 400, 80, 80), bg='call', cb=numericCallback, value=12),
     Button((210, 400, 80, 80), bg='right', cb=numericCallback, value=10)],
    # Screen 1 for numeric input
    [Button((50, 0, 320, 80), bg='box'),
     Button((130, 400, 80, 80), bg='hang', cb=numericCallback, value=12)],
    # Screen 2 for message
    [Button((50, 80, 80, 80), bg='1', cb=numericCallback, value="Hi"),
     Button((130, 80, 80, 80), bg='2', cb=numericCallback, value="Take Care"),
     Button((210, 80, 80, 80), bg='3', cb=numericCallback, value="Thank you"),
     Button((50, 160, 80, 80), bg='4', cb=numericCallback, value="Yes"),
     Button((130, 160, 80, 80), bg='5', cb=numericCallback, value="No"),
     Button((210, 160, 80, 80), bg='6', cb=numericCallback, value="I don't know"),
     Button((50, 240, 80, 80), bg='7', cb=numericCallback, value="."),
     Button((130, 240, 80, 80), bg='8', cb=numericCallback, value=","),
     Button((210, 240, 80, 80), bg='9', cb=numericCallback, value="!"),
     Button((50, 320, 80, 80), bg='star', cb=numericCallback, value=0),
     Button((130, 320, 80, 80), bg='0', cb=numericCallback, value=" "),
     Button((210, 320, 80, 80), bg='hash', cb=numericCallback, value=0),
     Button((130, 400, 80, 80), bg='message', cb=numericCallback, value=12),
     Button((210, 400, 80, 80), bg='del2', cb=numericCallback, value=10)],
    # Alphabet Screen 4.
    [Button((20, 100, 20, 20), bg='A', cb=numericCallback, value="a"),
     Button((60, 100, 20, 20), bg='B', cb=numericCallback, value="b"),
     Button((100, 100, 20, 20), bg='C', cb=numericCallback, value="c"),
     Button((140, 100, 20, 20), bg='D', cb=numericCallback, value="d"),
     Button((180, 100, 20, 20), bg='E', cb=numericCallback, value="e"),
     Button((220, 100, 20, 20), bg='F', cb=numericCallback, value="f"),
     Button((260, 100, 20, 20), bg='G', cb=numericCallback, value="g"),
     Button((300, 100, 20, 20), bg='H', cb=numericCallback, value="h"),
     Button((20, 200, 20, 20), bg='I', cb=numericCallback, value="i"),
     Button((60, 200, 20, 20), bg='J', cb=numericCallback, value="j"),
     Button((100, 200, 20, 20), bg='K', cb=numericCallback, value="k"),
     Button((140, 200, 20, 20), bg='L', cb=numericCallback, value="l"),
     Button((180, 200, 20, 20), bg='M', cb=numericCallback, value="m"),
     Button((220, 200, 20, 20), bg='N', cb=numericCallback, value="n"),
     Button((260, 200, 20, 20), bg='O', cb=numericCallback, value="o"),
     Button((300, 200, 20, 20), bg='P', cb=numericCallback, value="p"),
     Button((20, 300, 20, 20), bg='Q', cb=numericCallback, value="q"),
     Button((60, 300, 20, 20), bg='R', cb=numericCallback, value="r"),
     Button((100, 300, 20, 20), bg='S', cb=numericCallback, value="s"),
     Button((140, 300, 20, 20), bg='T', cb=numericCallback, value="t"),
     Button((180, 300, 20, 20), bg='U', cb=numericCallback, value="u"),
     Button((220, 300, 20, 20), bg='V', cb=numericCallback, value="v"),
     Button((260, 300, 20, 20), bg='W', cb=numericCallback, value="w"),
     Button((300, 300, 20, 20), bg='X', cb=numericCallback, value="x"),
     Button((0, 400, 60, 60), bg='start', cb=numericCallback, value=1),
     Button((140, 350, 20, 20), bg='Y', cb=numericCallback, value="y"),
     Button((180, 350, 20, 20), bg='Z', cb=numericCallback, value="z"),
     Button((240, 400, 60, 60), bg='stop', cb=numericCallback, value=0),

     ],
    [Button((50, 0, 320, 60), bg='box'),
     Button((50, 400, 80, 80), bg='left', cb=numericCallback, value=1),
     Button((130, 80, 80, 80), bg='twitter', cb=numericCallback, value=2),
     Button((130, 400, 80, 80), bg='cancel', cb=numericCallback, value=3),
     Button((130, 180, 80, 80), bg='TLogo', cb=numericCallback, value=4)



     ]
    ]


# Assorted utility functions -----------------------------------------------


def saveSettings():
    global v
    try:
        outfile = open('piphone.pkl', 'wb')
        # Use a dictionary (rather than pickling 'raw' values) so
        # the number & order of things can change without breaking.
        pickle.dump(v, outfile)
        outfile.close()
    except:
        pass


def loadSettings():
    global v
    try:
        infile = open('piphone.pkl', 'rb')
        v = pickle.load(infile)
        infile.close()
    except:
        pass


# Initialization -----------------------------------------------------------

# Init framebuffer/touchscreen environment variables
os.putenv('SDL_VIDEODRIVER', 'fbcon')
os.putenv('SDL_FBDEV', '/dev/fb1')
os.putenv('SDL_MOUSEDRV', 'TSLIB')
os.putenv('SDL_MOUSEDEV', '/dev/input/touchscreen')

# Init pygame and screen
print "Initting..."
pygame.init()
print "Setting Mouse invisible..."
pygame.mouse.set_visible(False)
print "Setting fullscreen..."
modes = pygame.display.list_modes(16)
screen = pygame.display.set_mode(modes[0], FULLSCREEN, 16)



print "Loading Icons..."
# Load all icons at startup.
for file in os.listdir(iconPath):
    if fnmatch.fnmatch(file, '*.png'):
        icons.append(Icon(file.split('.')[0]))
# Assign Icons to Buttons, now that they're loaded
print"Assigning Buttons"
for s in buttons:  # For each screenful of buttons...
    for b in s:  # For each button on screen...
        for i in icons:  # For each icon...
            if b.bg == i.name:  # Compare names; match?
                b.iconBg = i  # Assign Icon to Button
                b.bg = None  # Name no longer used; allow garbage collection
            if b.fg == i.name:
                b.iconFg = i
                b.fg = None

print"Load Settings"
loadSettings()  # Must come last; fiddles with Button/Icon states

img = pygame.image.load("icons/rough1.png")

reset_screen(screen, img)

print "Initialising Modem.."
serialport = serial.Serial("/dev/ttyUSB0", 115200, timeout=0.5)
serialport.write("AT\r")
response = serialport.readlines(None)
serialport.write("ATE0\r")
response = serialport.readlines(None)
serialport.write("AT\r")
response = serialport.readlines(None)
serialport.write("AT+CMGF=1\r\n")
response = serialport.readlines(None)
print response

# Main loop ----------------------------------------------------------------


print "mainloop.."
while True:

    # Process touchscreen input
    while True:
        screen_change = 0
        for event in pygame.event.get():
            if event.type is MOUSEBUTTONDOWN:
                pos = pygame.mouse.get_pos()
                for b in buttons[screenMode]:
                    f = open("PiPhoneLogs.txt", "a+")
                    f.write(str(pos))
                    f.write("\n")
                    f.write(str(b.callback))
                    f.write("\n")
                    f.close()
                    if b.selected(pos):
                        break;
                screen_change = 1
            # if screenMode >= 1 or screenMode != screenModePrior: break
        if screen_change == 1 or screenMode != screenModePrior: break
    if img is None or img.get_height() < 320:
        screen.fill(0)
    if img:
        screen.blit(img,
                    ((320 - img.get_width()) / 2,
                     (480 - img.get_height()) / 2))

    # Overlay buttons on display and update
    for i, b in enumerate(buttons[screenMode]):
        b.draw(screen)
    if screenMode == 0:
        myfont = pygame.font.SysFont("Arial", 20)
        label = myfont.render(numberstring, 1, (255, 255, 255))
        screen.blit(label, (10, 2))
    elif screenMode == 1:
        myfont = pygame.font.SysFont("Arial", 20)
        label = myfont.render("Calling", 1, (255, 255, 255))
        screen.blit(label, (10, 80))
        myfont = pygame.font.SysFont("Arial", 20)
        label = myfont.render(numberstring + "...", 1, (255, 255, 255))
        screen.blit(label, (10, 120))
    elif screenMode == 2:
        myfont = pygame.font.SysFont("Arial", 20)
        label = myfont.render(messagestring, 1, (255, 255, 255))
        screen.blit(label, (10, 2))
        label = myfont.render("Messaging", 1, (255, 255, 255))
        screen.blit(label, (10, 80))
        myfont = pygame.font.SysFont("Arial", 20)
        label = myfont.render(numberstring + "...", 1, (255, 255, 255))
        screen.blit(label, (10, 120))
    elif screenMode == 3:
        myfont = pygame.font.SysFont("Arial", 20)
        label = myfont.render(tweetstring, 1, (255, 255, 255))
        screen.blit(label, (10, 2))
    else:
        print "hi"
    pygame.display.update()

    screenModePrior = screenMode
