from pynput import mouse, keyboard
from enum import Enum
from PIL import ImageGrab
import time, sys, csv


class Bot:

    class Color(Enum):
        Green = 1
        Yellow = 2
        Grey = 3


    def __init__(self, ostream=sys.stdout) -> None:
        # Variables for external communication
        self.output_stream = ostream
        self.word_bank = "word_bank.csv"
        self.calibration_data = "calibration_data.csv"

        # Calibration & Setup
        self.grid_pixels: list[list[tuple]] = []
        self.GREEN = tuple()
        self.YELLOW = tuple()
        self.GREY = tuple()

        # Variables for internal communication (shared rd/wt)
        self.found_chars = [False for i in range(0, 5)]
        self.attempt_result = [Bot.Color.Grey for i in range(0, 5)]
        self.word_bank = [] # Read in from the CSV file
        

    def calibrate(self) -> None:
        """
        This function allows the user to calibrate the bot so that it knows where on 
        the screen to look and what te RGB values for each type of hint are. It will 
        also write calibration values into a file so that they can be used in future 
        runs of the bot. So, it will also give the user the option to skip 
        calibration and load in previous calibration data.
        """

        print("Calibration starting up...", file=self.output_stream)
        self._calibrateColors()
        self._calibrateGrid()
        


    def _calibrateColors(self) -> None:
        """
        Helper function to handle color calibration. Encapsulating it as one function
        makes it easier to improve the color calibration process later on.
        """

        print("Calibrating: Colors\n"
              + "Click on the legend colors in the following order:\n"
              + "1) Green\n2) Yellow\n3) Grey"
              , file=self.output_stream)
        clickLog = self._getXClicks(3)
        screenshot = ImageGrab.grab().load()
        self.GREEN = screenshot[clickLog[0][0], clickLog[0][1]]
        self.YELLOW = screenshot[clickLog[1][0], clickLog[1][1]]
        self.GREY = screenshot[clickLog[2][0], clickLog[2][1]]


    def _calibrateGrid(self) -> None:
        """
        Helper function to handle grid calibration. Encapsulating it as one function
        makes it easier to improve the grid calibration process later on.
        """

        print("Calibrating: Grid\n"
              + "Click on the top left corner of each square in the following pattern:\n"
              + "1) Left to Right\n2) Top to Bottom"
              , file=self.output_stream)
        clickLog = self._getXClicks(30)
        # Set the global variable based on recorded data
        self.grid_pixels.clear()
        for i in range(0, 6):
            self.grid_pixels.append([])
            for j in range(0, 5):
                self.grid_pixels[i].append(clickLog.pop(0))

    
    def _loadCalibrationData(self) -> None:
        """
        This function pretty much does the opposite of `self._saveCalibrationData`. 
        If that function gets updated, then this should be updated as well to 
        follow the same encoding.
        """

        with open(self.calibration_data, newline='') as file:
            reader = csv.reader(file)
            # Get the colors
            row = next(reader)
            self.GREEN = tuple([int(elem) for elem in row])
            row = next(reader)
            self.YELLOW = tuple([int(elem) for elem in row])
            row = next(reader)
            self.GREY = tuple([int(elem) for elem in row])
            # Load the coordinates into a list
            temp = []
            for row in reader:
                coord = tuple([int(elem) for elem in row])
                temp.append(coord)
            # Reformat data into grid
            self.grid_pixels.clear()
            for i in range(0, 6):
                self.grid_pixels.append([])
                for j in range(0, 5):
                    self.grid_pixels[i].append(temp.pop(0))


    def _saveCalibrationData(self) -> None:
        """
        This function takes info from `self.grid_pixels`, and the calibration
        data for the colors and stores them into an external CSV file. The first 
        3 rows are the RGB codes for GREEN, YELLOW, GREY. Each of the following 
        30 rows represent the (x, y) coordinates stored in `self.grid_pixels` 
        from left to right, top to bottom.
        """

        with open(self.calibration_data, 'w', newline='') as file:
            writer = csv.writer(file)
            # write the color RGB Values
            writer.writerows([self.GREEN, 
                              self.YELLOW, 
                              self.GREY])
            # Write the pixel coordinates for the grid
            for row in self.grid_pixels:
                writer.writerows(row)


    def _getXClicks(self, numClicks: int = 1) -> list[tuple]:
        """
        The function handles getting mouse-input in an easy-to-use way. Simply press
        `ctrl` to reset and begin logging clicks, and press `alt` to finish. The 
        argument `numClicks` determines how many clicks it will force the user to 
        enter before it returns. Upon returning, it will return a list where each
        element is a tuple containing the `(x, y)` coordinates of each click made.
        """

        # Setup for kb + mouse monitoring
        clickLog: list[tuple] = []
        keepLooping: bool = True

        def on_click(x, y, button, pressed):
            nonlocal clickLog
            if (button == mouse.Button.left) and (not pressed):
                if len(clickLog) < numClicks:
                    clickLog.append((x, y))
                else:
                    print("Already recorded all", numClicks, "points", file=self.output_stream)

        ms_listener = mouse.Listener(on_click=on_click)
        
        def on_press(key):
            nonlocal keepLooping, ms_listener
            if key == keyboard.Key.ctrl_l:
                clickLog.clear()
                if not (ms_listener.is_alive()):
                    ms_listener.start()
            elif (key == keyboard.Key.alt_l):
                if len(clickLog) != numClicks:
                    print(numClicks, "points needed to finish calibration", file=self.output_stream)
                else:
                    ms_listener.stop()
                    keepLooping = False
                    return False
                
        kb_listener = keyboard.Listener(on_press=on_press)

        # Start the input monitors
        print("Waiting for", numClicks, "click(s). Press the 'ctrl' key to\n"
             + "start logging clicks or reset. Press the 'alt'\n"
             + "key to finish logging your clicks.", file=self.output_stream)
        kb_listener.start()

        # Stall so the other threads keep running
        while keepLooping:
            time.sleep(0.1) # make it work less

        return clickLog


    def solve(self) -> None:
        """
        This function chains together multiple helper function so that the end result
        is a bot that can submit guesses, read the results from the screen, and make
        a better guess the next time.
        """

        guess = "salet"
        
        # for attempt_num in range(0, 6):
        #     # do the algorithm
        #     pass

        self._sendKBInput(guess)
        time.sleep(2.5) # give enough time for animations to finish
        self._recordResults(0)
        print(self.attempt_result)
    

    def _sendKBInput(self, word: str) -> None:
        """
        Simple function that takes a single word as input and translates it into the 
        appropriate key-presses followed by `enter`. Will probably throw some kind
        of runtime error if the input string has any characters other than 
        lowercase letters.
        """

        kb = keyboard.Controller()
        for char in word:
            kb.press(char)
            kb.release(char)
        kb.press(keyboard.Key.enter)
        kb.release(keyboard.Key.enter)


    def _recordResults(self, rowNum: int) -> None:
        """
        Helper function that reads the RGB values from a row of pixels determined by
        `self.pixel_grid[rowNum]`. It will determine which color out of `GREEN`, `YELLOW`, 
        and `GREY` the displayed color is closest to. Based on that, it will update
        `self.attempt_result` to reflect the hint from each grid square. If any cells
        are found to be green, it will also set the corresponding cell in 
        `self.found_chars` to be `True`.
        """

        CLR_CODES = [self.GREEN, self.YELLOW, self.GREY]
        screenshot = ImageGrab.grab().load()

        for i in range(0, len(self.grid_pixels[rowNum])):
            coord = self.grid_pixels[rowNum][i]
            pix_color = screenshot[coord[0], coord[1]]
            # determine similarity to each color
            distances = []

            for color in CLR_CODES:
                distances.append((color[0] - pix_color[0])**2 + (color[1] 
                                 - pix_color[1])**2 + (color[2] - pix_color[2])**2)

            min_idx = distances.index(min(distances))

            if min_idx == 0:
                # Green
                self.attempt_result[i] = Bot.Color.Green
                self.found_chars[i] = True
            elif min_idx == 1:
                # yellow
                self.attempt_result[i] = Bot.Color.Yellow
            else:
                # grey
                self.attempt_result[i] = Bot.Color.Grey


    def _updateWordBank(self, guessed: str) -> None:
        """
        This function updates the word bank based on the last guess that was made
        (passed as `guessed`) and the state of `self.attempt_result`. It also uses
        `attempt.found_chars` to reduce the amount of work it has to do.
        """
        pass


    def run(self) -> None:
        """
        This is the only "public" function that any external thing should use. It 
        ensures that the bot is calibrated before it is run.
        """

        print("Bot starting up...", file=self.output_stream)
        self.calibrate()
        self.solve()
