import pickle
from collections import Counter
from timeit import default_timer as timer
from profilehooks import profile


def ExtractListFromText(textFile): # Read a fingerprint saved in a textfile to an array 
    numLines = sum(1 for line in textFile)
    textFile.seek(0)

    extractedList = [textFile.readline().rsplit() for i in range(0, numLines)]
    extractedList = [[float(item) for item in extractedList[i]] for i in range(0, len(extractedList))]
    return extractedList

def Encode(x, bitNumber): # Convert a decimal number to a binary number
    return format(x, '0' + str(bitNumber) + 'b')

def GenerateAddressCoupleDB(databaseFileName, songID): # Create an array of addresses and couples for a given database fingerprint
    databaseFile = open(databaseFileName, 'r')
    databaseFingerprint = ExtractListFromText(databaseFile)

    targetZoneSize = 5
    # Split the data into groups of 5 points
    targetZoneArray = [databaseFingerprint[i:i+targetZoneSize] for i in range(0, len(databaseFingerprint)-targetZoneSize)]

    # An 'Address' describes the index of a particular row of the database table
    addressArray = [[(round(databaseFingerprint[i-3][1]/10), round(targetZoneArray[i][j][1]/10), round((targetZoneArray[i][j][0]-databaseFingerprint[i-3][0])*1000)) for j in range(0, len(targetZoneArray[1]))] for i in range(3, len(databaseFingerprint)-targetZoneSize)]

    # 'Couples' are the data returned from matches between 'Addresses'. They are the values in the database table which has an index of the associated address
    coupleArray = [[(round(databaseFingerprint[i-3][0]*1000), songID)for j in range(0, len(targetZoneArray[1]))] for i in range(3, len(databaseFingerprint)-targetZoneSize)]

    # Here I convert each index of the two previous lists into binary and concatenate them all. This is the hashing function for the table
    encodedAddressArray = [[''.join((Encode(x[y][0], 9), Encode(x[y][1], 9), Encode(x[y][2], 14))) for y in range(0,5)] for x in addressArray]
    encodedCoupleArray = [[''.join((Encode(x[y][0], 32), Encode(x[y][1], 32))) for y in range(0,5)] for x in coupleArray]

    return encodedAddressArray, encodedCoupleArray

def GenerateAddressCoupleQUERY(queryFileName): # Create an array of addresses and couples for the live recorded sample. Same function as before
    queryFile = open(queryFileName, 'r')
    queryFingerprint = ExtractListFromText(queryFile)

    targetZoneSize = 5
    targetZoneArray = [queryFingerprint[i:i+targetZoneSize] for i in range(0, len(queryFingerprint)-targetZoneSize)]
    addressArray = [[(round(queryFingerprint[i-3][1]/10), round(targetZoneArray[i][j][1]/10), round((targetZoneArray[i][j][0]-queryFingerprint[i-3][0])*1000)) for j in range(0, len(targetZoneArray[1]))] for i in range(3, len(queryFingerprint)-targetZoneSize)]

    coupleArray = [[(round(queryFingerprint[i-3][0]*1000))for j in range(0, len(targetZoneArray[1]))] for i in range(3, len(queryFingerprint)-targetZoneSize)]

    encodedAddressArray = [[''.join((Encode(x[y][0], 9), Encode(x[y][1], 9), Encode(x[y][2], 14))) for y in range(0,5)] for x in addressArray]
    encodedCoupleArray = [[''.join((Encode(x[y], 32))) for y in range(0,5)] for x in coupleArray]

    return encodedAddressArray, encodedCoupleArray

def AddToFingerprintTable(keyArray, valueArray, fingerprintHashTable): # Add new song data (ie. new addresses and couples) to the existing database
    for i in range (0, len(keyArray)):
        for j in range(0, len(keyArray[1])):
            if keyArray[i][j] in fingerprintHashTable:
                fingerprintHashTable[keyArray[i][j]].append(valueArray[i][j])
            else:
                fingerprintHashTable[keyArray[i][j]] = [valueArray[i][j]]

def SaveHashTable(dictionary, textFile): # Save a hash table out to a file
    with open("/Users/account1/Documents/Visual Studio/Python/MusicID/" + str(textFile) + ".txt", "wb") as savefile:
        pickle.dump(dictionary, savefile)

def LoadHashTable(textFile): # Load a hash table from a given file
    with open("/Users/account1/Documents/Visual Studio/Python/MusicID/" + str(textFile) + ".txt", "rb") as savefile:
        pulledDictionary = pickle.load(savefile)
        return pulledDictionary



def TakeDataFromFingerprintLibrary(indexes, couples, fingerprintDictionary): # Search the database for records matching the query
    # Create lists
    dbCouples = []
    timepairs = []

    # Loop through the fingerprint library and find the relevant results
    for i in range(0, len(indexes)):
        for j in range(0, 5):
            if indexes[i][j] in fingerprintDictionary:
                dbCouples.append(fingerprintDictionary[indexes[i][j]])
                currentList = []
                for k in range(0, len(fingerprintDictionary[indexes[i][j]])):
                    currentList.append([fingerprintDictionary[indexes[i][j]][k], int(fingerprintDictionary[indexes[i][j]][k][:32], 2) - int(couples[i][j], 2)])
                timepairs.append(currentList)
    return dbCouples, timepairs

def CompareNumberOfMatchingTargetZones(returnedCouples, seconds): # Work out how many target zones match between the query and a particular song in the database
    # Remove the 2D nature of the returned couples so that they are easier to loop through
    flattenedCouples = [y for x in returnedCouples for y in x]
    
    # Count the number of matching couples returned for each song in a hash table where the key is the songID and the value is the number of times a couple associated 
    # with that song is returned
    couplesHash = {}
    for i in range(0, len(flattenedCouples)):
        if flattenedCouples[i] in couplesHash:
            couplesHash[flattenedCouples[i]] += 1
        else:
            couplesHash[flattenedCouples[i]] = 1
    
    # Filter out any songs which have fewer than 4 matching couples (since the target zones are made up of 5 couples and 4 would not make a target zone)
    for k, v in list(couplesHash.items()):
        if v < 4:
            del couplesHash[k]
    songIDHash = {}

    # Count the number of matching target zones for each song
    for key in couplesHash:
        songID = key[-32:]
        if songID in songIDHash:
            songIDHash[songID] += 1
        else:
            songIDHash[songID] = 1

    # Choose the songs with a number of matches greater than a threshold value
    noiseTolerance = 0.1
    for k, v in list(songIDHash.items()):
        if v < seconds * 50 * noiseTolerance:
            del songIDHash[k]
    return songIDHash

def CheckTimeCoherency(songIDHash, timepairs): # For the matching notes found, work out whether they occur in the correct order in a given song
    # Sort the delta time between matching couples in the query and database record into groups of what song they belong to
    songBinHash = {}
    for i in range(0, len(timepairs)):
        for j in range(0, len(timepairs[i])):
            songID = timepairs[i][j][0][-32:]
            if songID in songBinHash:
                songBinHash[songID].append(timepairs[i][j][1])
            else:
                songBinHash[songID] = [timepairs[i][j][1]]

    # Find the song which produces the greatest number of matching notes for a given delta time (ie find the dictionary key with the most items associated with it)
    greatestDeltaHash = {}
    for key in songIDHash:
        mostCommon, frequency = Counter(songBinHash[key]).most_common(1)[0]
        greatestDeltaHash[key] = frequency
    
    coeff = 0.08
    highestValue=1
    # If the song has a number of matching notes over a certain threshold then choose it as the users song
    for key in greatestDeltaHash:
        if highestValue < greatestDeltaHash[key]:
            highestValue = greatestDeltaHash[key]
            if highestValue > 39:
                highestKey = key

    if 'highestKey' in locals():
        return highestKey
    else:
        return 0

def SearchDatabase(seconds, fingerprintDictionary): # Combining the above functions to search the database, find a match and return the results
    query = '/Users/account1/Documents/Visual Studio/Python/MusicID/SampleFingerprint.txt'
    indexesQ, couplesQ = GenerateAddressCoupleQUERY(query)
    songMappingTable = LoadHashTable('songMap')

    # Returns couples from the database
    returnedCouples, timepairs = TakeDataFromFingerprintLibrary(indexesQ, couplesQ, fingerprintDictionary)

    # Check how many target zones match between the query and the database record
    songIDHash = CompareNumberOfMatchingTargetZones(returnedCouples, seconds)

    # Check time coherency 
    highestKey = CheckTimeCoherency(songIDHash, timepairs)

    # Display the results
    if highestKey != 0:
        songMetaData = songMappingTable[highestKey]
        if songMetaData[2] == 'Single':
            print("The song is '" + songMetaData[0] + "' by " + songMetaData[1] + '. It was released as a single on ' + songMetaData[3])
        else:
            print("The song is '" + songMetaData[0] + "' by " + songMetaData[1] + " from the album '" + songMetaData[2] + "'. It was released " + songMetaData[3])
    else:
        songMetaData = 0
        print('The song could not be found')
    
    return songMetaData
