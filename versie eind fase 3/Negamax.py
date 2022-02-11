import time
import json
import chess
import random
import boardeval
import threading
import chess.syzygy
import chess.variant
import chess.polyglot

from UI import getUIVar

search_depth = 4

transpositionTable = {}
prinVariation = []
searchValue = 0
stopSearch = False

diepte = 0


def randomMove(board):
    legalMoves = list(board.legal_moves)
    return random.choice(legalMoves)

def orderMoves(board, layer):

    outputMoves = [];   captures = []
    pawnCaptures = [];  restMoves = []
    pawnMoves = []

    legalMoves = list(board.legal_moves)

    for move in legalMoves:

        if len(prinVariation) > layer:
            if move == prinVariation[layer]:
                outputMoves.append(move)
                continue

        if board.is_capture(move):
            if board.piece_type_at(move.from_square) == chess.PAWN:
                pawnCaptures.append(move)
            else:
                captures.append(move)

        else:

            if board.piece_type_at(move.from_square) == chess.PAWN:
                pawnMoves.append(move)
            else:
                restMoves.append(move)
    outputMoves = outputMoves + captures + pawnCaptures + restMoves + pawnMoves

    return outputMoves


def negamax(board, isWhite, layer, alpha, beta, current_search_depth):
    global transpositionTable
    global prinVariation
    global searchValue
    global stopSearch
    global top10

    orderedMoves = orderMoves(board, layer)
    #orderedMoves = list(board.legal_moves)

    bestMoves = []

    # sets the begin time for showing how long negamax took
    tmpTime = beginTime = time.perf_counter()

    # checks if game ends at this move
    if board.outcome() != None:
        if board.is_checkmate():
            return -1000000
        else:
            return 0

    if board.fen() in transpositionTable:
        return transpositionTable[board.fen()]

    # checks if search depth is reached
    elif layer >= current_search_depth:
        alpha = boardeval.evaluate(board.fen(), isWhite, layer)

        return alpha

    layer += 1
    # Loops over the ordered moves


    for x in orderedMoves:
        # calls negamax for every move
        board.push(x)

        oppositeValue = negamax(board, not isWhite, layer, -beta, -alpha, current_search_depth)

        if oppositeValue == "stopped": 
            break

        moveValue = -oppositeValue        
        transpositionTable[board.fen()] = -moveValue

        board.pop()

        if len(top10) == 10 and len(prinVariation) == diepte:
            zwaksteSchakel = sorted(top10.items(), key = lambda t: t[1], reverse = True)[9][0]
            if top10[zwaksteSchakel] < moveValue:
                top10[tuple(prinVariation)] = moveValue
                top10 = dict(sorted(top10.items(), key = lambda t: t[1], reverse = True)[:-1])
        elif len(prinVariation) == diepte:
            top10[tuple(prinVariation)] = moveValue

        # blocks a branch if the branch can't be better than a previous branch
        if moveValue >= beta:
            searchValue = moveValue + 1
            if layer == 1:
                return None, moveValue + 1
            return moveValue + 1

        # adds move to bestMoves if the move is equally good as the latest best move
        if moveValue == alpha and layer == 1:
            bestMoves.append(x)

        if moveValue > alpha:
            alpha = moveValue

            # deletes worse moves and adds newest best move to bestMoves
            bestMoves = [x]

        # checks if the move is better than the last best move
        if moveValue >= alpha:

            if len(prinVariation) == layer - 1 and not(x in prinVariation):
                prinVariation.append(x)
            elif len(prinVariation) >= layer and not(x in prinVariation):
                prinVariation[layer-1] = x
                prinVariation[-1] = x

            if layer == 1:
                # calculates the time used for this move, prints it and sets the timer for timing the next move
                moveTime = time.perf_counter() - tmpTime
                if current_search_depth >= diepte:

                    print(f"move: {str(board.lan(x))}; move value:   {moveValue:+}")
                    print(f" time it took:             {moveTime:.4f}s")

                    #print(dict(sorted(top10.items(), key = lambda t: t[1], reverse = True)))

                tmpTime = time.perf_counter()

    layer -= 1

    if stopSearch: return "stopped"

    # bepaal wat terug te geven
    if not layer == 0:
        return alpha

    # als het de eerste zet is
    else:
        endTime = time.perf_counter() - beginTime

        if len(bestMoves) != 0:

            print(f"{len(bestMoves)} possible moves:           {[board.lan(zet) for zet in bestMoves]}")
            print(f"negamax value:              {alpha:+}")
            print(f"negamax took:               {endTime:.4f}s")            
            bestMove = random.choice(bestMoves)
        
        else:
            bestMove = None

        searchValue = alpha

        return bestMove, alpha

def egtb(board):

    movesEval = {}
        
    orderedMoves = orderMoves(board, 1)
    
    for x in orderedMoves:
        with chess.syzygy.open_tablebase("3-4-5")  as tablebase:
            result = tablebase.probe_wdl(board)
            board.push(x)

            if -tablebase.probe_wdl(board) >= result: #Zetten die sowieso niet beter zijn

                # Probeert een pion altijd naar een dame te promoveren als die optie er is
                if "q" in x.uci() or "Q" in x.uci(): 
                    return x
                
                xmoveValue = -tablebase.probe_dtz(board)
                if board.piece_type_at(x.to_square) == 1: #pionzetten krijgen voorrang. Pion is stuk 1
                    xmoveValue -= 0.5

                movesEval[x] = xmoveValue 

            board.pop()

    print("movesEval:", movesEval)
    
    move = random.choice([key for key in movesEval if movesEval[key] == min(movesEval.values()) ])
    
    print("Beste zet volgens eindspel tablebase:", move)

    return move

def iterToBestMove(board, isWhite, timeDict = None, firstLoop = True):
    global transpositionTable
    global prinVariation
    global stopSearch
    global searchValue
    global diepte
    global top10

    transpositionTable = {}
    prinVariation = []
    searchValue = boardeval.evaluate(board.fen(), isWhite, 0)

    beginTime = time.perf_counter()

    usableTime = 0
    diepte = 0

    hoevStukken = len(board.piece_map())

    if hoevStukken <= 5:
        return egtb(board)

    if timeDict["timeLeft"] != None:
        #usableTime = 0.05*timeLeft/1000
        if board.ply()/2 < 60:
            skew = 10*((60-board.ply()/2)/60)
        else:
            skew = 0

        usedTime = timeDict["totalTime"]-timeDict["timeLeft"]
        usableTime =  (0.15*usedTime + 20) * ((timeDict["totalTime"]-usedTime)/timeDict["totalTime"]) - skew
        #print( usableTime, ": ", usedTime )
        
        
    elif firstLoop:
        #krijg diepte setting van settings.json
        try:
            with open("settings.json") as settingsFile:
                settings = json.load(settingsFile)
            diepte = int(settings["Diepte"])
        except Exception:
            diepte = search_depth

    else:
        diepte = 2

    searchDepth = 0
    while searchDepth < diepte or time.perf_counter() - beginTime < usableTime:
    
        if searchValue == 1000000:

            endTime = time.perf_counter() - beginTime

            print(f"Iteration value:              {searchValue:+}")
            print(f"Iteration took:               {endTime:.1f}s")
            return prinVariation[0]

        searchDepth += 1
        print("new iteration: searching to depth ", searchDepth)
        
        checkValue = searchValue
        lowerWindow = -25
        upperWindow = 25

        while True:
            stopSearch = False
            top10 = {}

            argList = (board, isWhite, 0, searchValue + lowerWindow, searchValue + upperWindow, searchDepth)
            searchThread = threading.Thread(target = negamax, args = argList)

            searchThread.start()
            if timeDict["timeLeft"] != None:
                while searchThread.is_alive() and time.perf_counter() - beginTime < usableTime:
                    time.sleep(0.2)
                    print(f"{(time.perf_counter() - beginTime)/usableTime*100:.3f}%, of {usableTime}s", end="\r")
                print("                    ")
                stopSearch = True
            searchThread.join()

            
            transpositionTable = {}
            if searchValue > checkValue + upperWindow:

                searchValue = checkValue
                upperWindow += round(0.5 * upperWindow * abs(1 - (upperWindow / 1000)) + 70)
                print(f"fail-high; widening upper window to: {upperWindow} (max value of: {searchValue+upperWindow})")

            elif searchValue == checkValue + lowerWindow:

                searchValue = checkValue
                lowerWindow += round(0.5 * lowerWindow * abs(1 - (lowerWindow / 1000)) - 70)
                print(f"fail-low; widening lower window to: {lowerWindow} (min value of: {searchValue+lowerWindow})")

            else:
                print("no fails          ", prinVariation)
                if searchDepth == diepte:
                    bestMove = prinVariation[0]
                break


    if len(prinVariation) > 0:
        bestMove = prinVariation[0]
    else: 
        bestMove = randomMove(board)

    "Dubbelchekcen staat uit"
    if False: #firstLoop and searchDepth == diepte and False:

        print("____________________Controle;", board.lan(prinVariation[0])," ____________________")

        #Oorspronkelijke waarden
        zoekWaarde = searchValue 

        #Maakt een kopiebord naar het einde van de optimale variatie
        cboard = board.copy()

        try:
            for move in prinVariation:
                cboard.push(move) 
        except Exception as e:
            print(e)
        
        if diepte % 2 == 0:
            continuation = iterToBestMove(cboard, isWhite, timeDict, False)
        else:
            continuation = iterToBestMove(cboard, not isWhite, timeDict, False)

        continuation = negamax(cboard, not isWhite, 0, -1000000, 1000000, 3)
        del cboard

        input(prinVariation)
        print(f"Vervolgevaluatie {str(prinVariation)}:           {zoekWaarde:+} --> {-continuation:+}")
        verschil = -continuation - zoekWaarde
        print("Verschil:", "+"*int(verschil > 0) + str(verschil))
        if verschil < -150:
            print("Andere zet wordt overwogen")
            input("")


    endTime = time.perf_counter() - beginTime
    print(f"Iteration value:              {searchValue}")
    print(f"Iteration took:               {endTime:.1f}s")

    if firstLoop:
        return bestMove
    else:
        return searchValue

def useEngine(startpos, moveList, isWhite, timeDict=None):
    global board

    #resets board with given move list
    try:
        if startpos[1] == "chess960" :
            board = chess.Board(startpos[0], True)
        
        elif startpos[1] == "horde":
            board = chess.variant.HordeBoard()

        else:
            board = chess.Board(startpos[0])

    except Exception as e:
        board = chess.Board()

    for x in moveList:
        if not x == "":
            move = chess.Move.from_uci(x)
            board.push(move)

    if timeDict["timeLeft"] != None:
        if timeDict["timeLeft"] <= 5: return randomMove(board)

    legalMoves = list(board.legal_moves)
    if len(legalMoves) == 1:
        return legalMoves[0]

    with open("settings.json") as settingsFile:
        settings = json.load(settingsFile)
        openingboekAan = settings["OpeningboekVariabel"]

    if openingboekAan:
        with chess.polyglot.open_reader("baronbook30.zip/baron30.bin") as reader:    
            entryList = list(reader.find_all(board, minimum_weight=30))
            if len(entryList) > 0:
                nextMove = random.choices([entry.move for entry in entryList], weights=[entry.weight for entry in entryList], k=1)[0]
                print(f"Zet volgens openingenboek: {chosenMove.uci()}")
    else:
        nextMove = iterToBestMove(board, isWhite, timeDict)
        
    print("negamax move: " + nextMove.uci())
        
    with open("log", "a") as file:
        file.write(" " + str(diepte) + " | ")


    return nextMove.uci()
