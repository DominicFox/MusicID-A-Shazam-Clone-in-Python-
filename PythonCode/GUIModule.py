import tkinter as tk
import time
import threading
import AudioModule
import DBModule
from collections import Counter, deque
from timeit import default_timer as timer
import pickle


class MainApplication(tk.Frame): # Class for the main GUI of the application. Inherits methods from tk.Frame
    def __init__(self, parent, *args, **kwargs):
        # Initialise the applications main frame
        tk.Frame.__init__(self, parent, *args, **kwargs)
        self.parent = parent

        # Setup window size and name 
        self.parent.geometry("400x600")
        self.parent.title("MusicID")

        # Specify some conditions at launch and load the fingerprint database
        self.fingerprintDictionary = DBModule.LoadHashTable('fingerprintDatabase')
        self.pointerInAudio = 0

        # Call method to place buttons and labels
        self.AddWidgets(True)
    
    def recordButtonClick(self): # Method to handle record button pressing
        self.pointerInAudio = 0

        # Change the background colours to be red, reflecting the fact that the program is now recording
        self.lastSongsButton.place_forget()
        tk.Frame.config(self, bg='red')
        self.recordButton.config(text = "Listening")
        self.titleLabel.config(bg='red')
        tk.Frame.update(self)
        self.recordButton.update()
        self.titleLabel.update()

        # Create and start three different threads which will run at the same time. One will record audio, one will process that recorded audio in parallel, one will 
        # time how long the program has been searching
        # This thread is begun first and starts recording audio and saving it to a file every second
        self.recordAudioThread = threading.Thread(target=AudioModule.RecordAudio, args=(15, "/Users/account1/Documents/Visual Studio/Python/MusicID/RecordedAudio.wav", 1))
        self.recordAudioThread.start()

        # This thread counts the number of seconds passed since beginning the search
        self.counterThread = threading.Thread(target=self.CountSeconds)
        self.counterThread.start()
        self.start=timer()
        time.sleep(2)

        # After sleeping for two seconds (to allow time for some audio to be recorded which can be processed), begin to process the data and look for matches
        self.identifySongThread = threading.Thread(target=self.IDSong, args=("/Users/account1/Documents/Visual Studio/Python/MusicID/RecordedAudio.wav", self.fingerprintDictionary))
        self.identifySongThread.start()
        
    def CountSeconds(self):
        # Simply count seconds passed
        for i in range(1, (11)):
            time.sleep(1)
            self.secondsPassed = i
    
    def AddWidgets(self, firstLaunch): # Method to place widgets on the frame
        if firstLaunch == True:
            # Initialise and place the title label at the top of the screen
            labelFont = ("Helvetica", 40, "bold")
            self.titleLabel = tk.Label(self, text = "MusicID")
            self.titleLabel.config(font = labelFont)
            self.titleLabel.config(bg = "navy", fg = "yellow")
            self.titleLabel.pack(side = tk.TOP)

        # Initialise and place the record button in the centre of the screen
        buttonFont = ("Helvetica", 20)
        self.recordButton = tk.Button(self, text = "Record", height = 10, width = 20, command = self.recordButtonClick)
        self.recordButton.config(font=buttonFont)
        self.recordButton.config(bg = "blue")
        self.recordButton.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        # Initialise and place the previous song button
        self.lastSongsButton = tk.Button(self, text = 'Previous Matches', height = 2, width = 15, command = self.ShowLastMatches)
        self.lastSongsButton.config(font=buttonFont)
        self.lastSongsButton.place(relx = 0.5, rely = 0.9, anchor = tk.CENTER)

        # Load the queue for storing the last 5 matches
        with open("/Users/account1/Documents/Visual Studio/Python/MusicID/lastSongsMatched.txt", "rb") as savefile:
            self.lastSongsMatched = pickle.load(savefile)

    def AllChildren(self, window):
        # NOTE: I DIDN'T WRITE THIS FUNCTION
        _list = window.winfo_children()

        for item in _list :
            if item.winfo_children() :
                _list.extend(item.winfo_children())

        return _list

    def ResetWidgets(self):
        # Remove all the widgets currently on the screen, except the title
        for i in range(0, len(self.AllChildren(self.parent))):
            self.AllChildren(self.parent)[i].place_forget()

        # Add back the initial widgets, returning the user to the 'main menu', so that they can record again
        self.AddWidgets(False)    

    def ShowResults(self, name, artist, album, releaseDate, searchTime):
        # Remove record button
        self.recordButton.place_forget()
        self.lastSongsButton.place_forget()

        # Setup some fonts in advance
        songTitleFont = ("Helvetica", 25, 'bold')
        otherFont = ("Helvetica", 16)
        buttonFont = ("Helvetica", 20)

        # If the search has found a result, display that result, else just fill each text field with an empty string
        if name == 0:
            self.songTitle = tk.Label(self, text = 'Song Not Found', font=songTitleFont, bg='navy', fg='green')
            self.artistName = tk.Label(self, text = '', font=otherFont, bg='navy', fg='yellow')
            self.albumName = tk.Label(self, text='', font=otherFont, bg='navy', fg='yellow')
            self.releaseDate = tk.Label(self, text = '', font=otherFont, bg='navy', fg='yellow')
            self.searchTime = tk.Label(self, text = 'Search Time: ' + str(searchTime) + ' seconds', font=otherFont, bg='navy', fg='grey')
            self.backButton = tk.Button(self, text='Back', font=buttonFont, command = self.ResetWidgets)
        else:
            self.songTitle = tk.Label(self, text = 'Song: ' + str(name), font=songTitleFont, bg='navy', fg='green')
            self.artistName = tk.Label(self, text = 'Artist: ' + str(artist), font=otherFont, bg='navy', fg='yellow')
            self.albumName = tk.Label(self, text='', font=otherFont, bg='navy', fg='yellow')
            self.releaseDate = tk.Label(self, text = 'Release Date: ' + str(releaseDate), font=otherFont, bg='navy', fg='yellow')
            self.searchTime = tk.Label(self, text = 'Search Time: ' + str(searchTime) + ' seconds', font=otherFont, bg='navy', fg='grey')
            self.backButton = tk.Button(self, text='Back', font=buttonFont, command = self.ResetWidgets)

        # Special case to deal with the possibility of the song not belonging to any album
        if album == 'Single':
            self.albumName.config(text='Released as a single')
        elif album != 0:
            self.albumName.config(text = 'Album: ' + str(album))

        # Place all the text fields, centre-aligned, down the middle of the screen
        self.songTitle.place(relx=0.5, rely = 0.25, anchor = tk.CENTER)
        self.artistName.place(relx=0.5, rely = 0.32, anchor = tk.CENTER)
        self.albumName.place(relx=0.5, rely = 0.37, anchor = tk.CENTER)
        self.releaseDate.place(relx=0.5, rely=0.42, anchor=tk.CENTER)
        self.backButton.place(relx=0.5,rely=0.75, anchor=tk.CENTER)
        self.searchTime.place(relx=0.5, rely=0.85, anchor=tk.CENTER)

        # Save the stack of last matched songs to the file
        if name != 0:
            with open("/Users/account1/Documents/Visual Studio/Python/MusicID/lastSongsMatched.txt", "wb") as savefile:
                pickle.dump(self.lastSongsMatched, savefile)
        

    def ShowLastMatches(self):
        # Remove record button
        self.recordButton.place_forget()
        self.lastSongsButton.place_forget()

        buttonFont = ("Helvetica", 20)
        self.backButton = tk.Button(self, text='Back', font=buttonFont, command = self.ResetWidgets)
        self.backButton.place(relx=0.5,rely=0.8, anchor=tk.CENTER)
        if len(self.lastSongsMatched) > 0:
            self.clearButton = tk.Button(self, text='Clear', font=buttonFont, command = self.ClearPreviousMatches)
            self.clearButton.place(relx=0.5,rely=0.9, anchor=tk.CENTER)
        else:
            label = tk.Label(self, text='No Previous Matches', font=buttonFont, bg='navy', fg='yellow')
            label.place(relx=0.5, rely=0.35, anchor=tk.CENTER)

        labelFont = ("Helvetica", 16)

        yCoords = [0.16 + i*0.06 for i in range(0, 10)]
        self.arrayOfLabels = []
        for i in range(0,len(self.lastSongsMatched)):
            currentLabel = tk.Label(self, text = str(i+1) + '. ' + self.lastSongsMatched.pop(), font=labelFont, bg='navy', fg='yellow')
            currentLabel.place(relx=0.1, rely=yCoords[i], anchor=tk.W)
            self.arrayOfLabels.append(currentLabel)
        
    def ClearPreviousMatches(self):
        self.lastSongsMatched.clear()
        with open("/Users/account1/Documents/Visual Studio/Python/MusicID/lastSongsMatched.txt", "wb") as savefile:
                pickle.dump(self.lastSongsMatched, savefile)
        for i in range(0, len(self.arrayOfLabels)):
            self.arrayOfLabels[i].place_forget()
        self.clearButton.place_forget()

        buttonFont = ("Helvetica", 20)
        label = tk.Label(self, text='No Previous Matches', font=buttonFont, bg='navy', fg='yellow')
        label.place(relx=0.5, rely=0.35, anchor=tk.CENTER)


    def IDSong(self, filepath, fingerprintDictionary): # Function to call all the functions from other modules which handle processing and searching
        seconds = self.secondsPassed

        # This function handles the fingerprint generation of the audio recorded.
        # The pointer which is returned by the function specifies where the processing of the audio got to before more audio was recorded. 
        # Hence when we want to process the newly added audio, we just have to process the new stuff rather than processing all the old audio again
        self.pointerInAudio = AudioModule.GenerateConstellationMap(filepath, 1, self.pointerInAudio)

        # Here we try to find database matches to the fingerprint we just recorded. The returned value is the metadata associated with the song that it finds.
        # If no song is found then the metadata is all zeros
        self.songMetaData = DBModule.SearchDatabase(seconds, fingerprintDictionary)

        self.finish = timer()-self.start
        print('Total search time: ' + str(round(self.finish, 3)) + ' seconds')

        # Recursively call the function to continue searching for a match until it finds one, provided that we are still recording
        if self.songMetaData == 0 and self.recordAudioThread.isAlive():
            self.IDSong("/Users/account1/Documents/Visual Studio/Python/MusicID/RecordedAudio.wav", fingerprintDictionary)
        # If the recording has stopped and a song has still not been found then admit that there was no match
        elif self.songMetaData == 0 and not(self.recordAudioThread.isAlive()):
            AudioModule.stopCondition = True
            tk.Frame.config(self, bg='navy')
            tk.Frame.update(self)
            self.titleLabel.config(bg='navy')
            self.titleLabel.update()
            self.ShowResults(0,0,0,0,str(round(self.finish, 3)))
        # If we have found a match at any point, stop the recording and display the results of the search
        else:
            AudioModule.stopCondition = True
            tk.Frame.config(self, bg='navy')
            tk.Frame.update(self)
            self.titleLabel.config(bg='navy')
            self.titleLabel.update()
            self.lastSongsMatched.append(self.songMetaData[0] + ' by ' + self.songMetaData[1])
            self.ShowResults(self.songMetaData[0], self.songMetaData[1], self.songMetaData[2], self.songMetaData[3], str(round(self.finish, 3)))
