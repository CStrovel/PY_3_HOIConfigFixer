# Python 3.7
# Written by Charles Strovel
# This program updates hearts of iron configuration files from version 1.6 to 
# version 1.7. 
import re
import os 

# Regular Expressions
polRegEx = r"((?!\n)\s)*set_politics\s*=\s*{"
partRegEx = r"(((?!\n)\s)*)parties\s*=\s*{"
popRegEx = r"\s*((?!parties)\b\w+\b)\s*=\s*{.*?popularity\s*=\s*(\d?\d?\d)"
altStartRegEx = r"\d{4}\.\d?\d\.\d?\d\s*=\s*{"

# globals
searchDir = "."
newPath = os.path.join(searchDir, "newCountryFiles")
enc = "utf-8"

def main():
    # get list of .txt files in current directory
    fileList = getFiles(searchDir, ".txt")
    fileList = parseFiles(fileList)

    # loop through file list
    for file in fileList:
        # load file
        oldSettings = loadFile(file)

        # edit core HOI popularity list
        newSettings = hoiEditPop(oldSettings)

        # get the first alternate start index
        altIdx = findCodeChunk(newSettings, altStartRegEx)
    
        # keep going as long as theres a valid index
        while altIdx:
            # Check if the alternate date contains party settings 
            if findCodeChunk(newSettings[altIdx[0]:altIdx[1]], partRegEx):
                newSettings = hoiEditPop(newSettings, altIdx[0], alts = True)

            # look for the next alternate index
            altIdx = findCodeChunk(newSettings, altStartRegEx, altIdx[1])

        # write result to new file. Ensure new directory exists
        outToFile(newSettings, file, newPath)

def getFiles(fpath, fext):
    """ finds files in the specified directory of specified file extension"""
    fileList = []

    # Get the list of files in current working directory
    for root, _, files in os.walk(searchDir, followlinks = False):
        for file in files:
            # Only take files in the current directory, not sub directories 
            if root == searchDir: 
                # get files of the specified extension 
                (_, fileExt) = os.path.splitext(file)
                if fileExt in fext:
                    fileList.append(file)
    
    return fileList 

def parseFiles(fileList):
    rtrnLst = []
    for file in fileList:
        cfgTxt =loadFile(file)
        polIdx = findCodeChunk(cfgTxt, polRegEx, offset = 0)

        if not polIdx:
            print("Section set_politics = {0} not found in {1}. Skipping file.".format(r"{}", file))

        elif not findCodeChunk(cfgTxt, partRegEx, offset = polIdx[0]):
            print("Section parties = {0} not found in {1}. Skipping file.".format(r"{}", file))
        else:
            rtrnLst.append(file)

    return rtrnLst

def loadFile(fileName): 
    """opens a file, moves its contents into an array, and closes it"""
    # Try opening the file
    try:
        fHandle = open(fileName, "r", encoding = enc)

    except FileNotFoundError:
        # return negative 1 if the file can not be opened
        print("File {0} does not exist.".format(fileName))
        return None

    except: 
        # return negative 1 if the file has errored in some other way
        print("Unknown error attempting to open file {0}".format(fileName))
        return None

    # Read in, close, return
    rtrnStr = fHandle.read()
    fHandle.close()
    return rtrnStr

def findCodeChunk(code, regEx, offset = 0, delOpen = "{", delClose = "}"):
    """Finds a code block in an list, returns the start and end index"""
    # Search for the regex in code. If not found return None
    try: 
        startIdx = re.search(regEx, code[offset:]).start() + offset 
    except AttributeError:
        return None

    blkCount = 0 # number of open code blocks (nested) at current location
    currentIdx = startIdx # tracks index through string
    firstDel = True # marks finding the first opening delimeter (first open block)

    # move through each charater in the list item 
    while blkCount > 0 or firstDel:
        # tally opening and closing brackets
        if code[currentIdx] == delOpen:
            blkCount += 1
            # we have found the first opening for this code block
            firstDel = False
        if code[currentIdx] == delClose:
            blkCount -= 1 
        # move to the next index 
        currentIdx += 1

    return startIdx, currentIdx

def hoiEditPop(cfgTxt, startAt = 0, alts = False):
    """Function that finds and modifys the popularity 
    
    section in hearts of iron Configuration files. Primarly
    controls work flow of other functions"""
    # determine padding for output 
    tabSpace =""
    if alts:
        tabSpace = "\t"

    # get the index for politics and popularity code chunks
    polIdx = findCodeChunk(cfgTxt, polRegEx, offset = startAt)
    partIdx = findCodeChunk(cfgTxt, partRegEx, offset = polIdx[0])

    # Get popularity values
    popValues = re.findall(popRegEx, cfgTxt[partIdx[0]:partIdx[1]], re.S)

    # Splice in new popularity values
    cfgTxt = spliceIn(cfgTxt, hoiGetPolitics(cfgTxt, popValues, tabSpace), polIdx[1])
    
    # remove old party popularity section
    cfgTxt = cutCodePos(cfgTxt, partIdx[0], partIdx[1], True)
    return cfgTxt

def hoiGetPolitics(cfgTxt, popValues, tabSpace = ""):
    """ Writes a politics table into a string

    file at the specified location. Accepts a list of custom tuples"""
    # Sample dictionary of political parties 
    partyPop = {"anarchism" : 0, "syndicalism" : 0, "vanguardism" : 0, "progressivism" : 0,\
    "liberalism" : 0, "conservatism" : 0, "integralism" : 0, "social_nationalism" : 0,\
    "radical_nationalism" : 0}

    # match custom values with existing parties
    for party in popValues:
        try:
            partyPop[party[0].lower()] = party[1]
        except:
            print("Party {0} not found in offical list. Discarding value {1}.".format(party[0],party[1]))

    # Create a party string
    partyStr = "\n\n" + tabSpace + "set_popularities = {\n"
    for party, value in partyPop.items():
        partyStr += "\t" + tabSpace + party + " = " + str(value) + "\n"
    partyStr += tabSpace + "}"
    
    return partyStr

def spliceIn(splitString, insertString, position):
    """Splits splitString at the designated position. Inserts insert

    String between the two halves and reconcantinates them together"""
    firstPart = splitString[:position]
    secondPart = splitString[position:]

    return firstPart + insertString + secondPart

def cutCodePos(code, startIdx, endIdx, killWhiteSpace = False):
    """Removes a segment from a string based on position"""
    
    # Move index 
    firstPart = code[:startIdx]
    secondPart = code[endIdx:]

    # trims all new lines from both ends, adding one back in to maintain line consistancy
    if(killWhiteSpace):
        # capture tabs closest to the beginning of the next line
        cap = re.match(r"\s*", secondPart).group(0)
        cap = re.match(r"\t*", cap[::-1]).group(0)
        
        # strip all white space from both sides of the slice
        firstPart = firstPart.rstrip()
        secondPart = secondPart.lstrip()
        
        # add in a new line and the captured tab arangement 
        firstPart += "\n" + cap 

    return firstPart + secondPart

def outToFile(contents, fName, path = None):
    """ Writes a string to a named file """
    # make sure os is imported
    import os

    # directory handling. Create if it does not already exist 
    if path and not os.path.isdir(path):
        os.mkdir(path)

    # write to file
    fHandle = open(os.path.join(path, fName),"w", encoding = enc)
    fHandle.write(contents)
    fHandle.close()

main()