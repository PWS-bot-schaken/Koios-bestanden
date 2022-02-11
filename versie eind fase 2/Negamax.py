import time
import json
import chess
import chess.syzygy
import chess.polyglot
import random
import boardeval

import threading

from UI import getUIVar
from Verborgen._Controlepaneel import *

currentMoves = None

transpositionTable = {}
prinVariation = []
searchValue = 0
stopSearch = False

diepte = 0


def randomMove(board):
    legalMoves = list(board.legal_moves)
    return random.choice(legalMoves)


# def orderMoves(legalMoves, board, layer):
#     outputMoves = legalMoves
#     for i in range(len(legalMoves)):

#         if len(prinVariation) > layer:
#             if legalMoves[i] == prinVariation[layer]:
#                 outputMoves.insert(0, outputMoves[i])
#                 continue

#         if board.piece_type_at(legalMoves[i].from_square) == chess.PAWN:
#             outputMoves.append(outputMoves[outputMoves.index(legalMoves[i])])

#         if board.is_capture(legalMoves[i]):

#             outputMoves.insert(0, outputMoves.pop(i))
#     return outputMoves


def orderMoves(legalMoves, board, layer):

    outputMoves = []
    captures = []
    pawnCaptures = []
    restMoves = []
    pawnMoves = []

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

    #hoevStukken = len(board.piece_map())

    legalMoves = list(board.legal_moves)
    
    orderedMoves = orderMoves(legalMoves, board, layer)

    bestMoves = []

    # sets the begin time for showing how long negamax took
    beginTime = time.perf_counter()
    tmpTime = beginTime

    # checks if game ends at this move
    if board.outcome() != None:
        if board.is_stalemate():
            return 0
        else:
            return -1000000

    if board.fen() in transpositionTable:
        return transpositionTable[board.fen()]

    # checks if search depth is reached
    elif layer >= current_search_depth:
        alpha = boardeval.evaluate(board.board_fen(), isWhite, layer)
        
        return alpha

    layer += 1
    # Loops over the ordered moves

    movesEval = {}
    """ Lijkt niet te werken: directory Tablebase bestaat niet
    if hoevStukken <= 5:
        for x in orderedMoves:
            with chess.syzygy.open_tablebase("Tablebase")  as tablebase:
                tablebase2 = open(chess.syzygy.open_tablebase("files p2"))
                tablebase = tablebase + tablebase2
                board.push(x)
                moveValue = -tablebase.probe_dtz(board)
                if moveValue < 0:
                    moveValue = abs(moveValue) + 5000
                elif moveValue == 0:
                    moveValue = 1000
                #moveValue += 100 * -tablebase.probe_wdl(board)

                board.pop()

                movesEval[x] = moveValue 
        print(movesEval)
        print([key for key in movesEval if movesEval[key] == min(movesEval.values()) ])
        #input()
        return  [key for key in movesEval if movesEval[key] == min(movesEval.values()) ]
    """

    for x in orderedMoves:

        # calls negamax for every move
        board.push(x)

        oppositeValue = negamax(board, not isWhite, layer, -beta, -alpha,
                             current_search_depth)
        if oppositeValue != "stopped": 
            moveValue = -oppositeValue
        else:
            break
        
        

        transpositionTable[board.fen()] = -moveValue

        board.pop()
        
        

        # blocks a branch if the branch can't be better than a previous branch
        if moveValue >= beta:
            searchValue = moveValue+1
            if layer == 1:
                return None, moveValue + 1
            return moveValue + 1

        # adds move to bestMoves if the move is equally good as the latest best move
        if moveValue == alpha and layer == 1:
            bestMoves.append(x)

        if moveValue == alpha:
            if len(prinVariation) == layer - 1:
                prinVariation.append(x)
            elif len(prinVariation) >= layer:
                prinVariation[layer-1] = x

        # checks if the move is better than the last best move
        if moveValue > alpha:
            
            if len(prinVariation) == layer - 1:
                prinVariation.append(x)
            elif len(prinVariation) >= layer:
                prinVariation[layer-1] = x

            # if len(prinVariation) == layer - 1:
            #     for i in range(1,layer):
            #         prinVariation[-i] = board.pop()
            #     for move in prinVariation:
            #         board.push(move)
            #     prinVariation.append(x)
                
                

            # elif len(prinVariation) == layer:
            #     for i in range(2,layer+1):
            #         prinVariation[-i] = board.pop()
            #     for i in range(len(prinVariation)-1):
            #         board.push(prinVariation[i])
                
                
                prinVariation[-1] = x

            alpha = moveValue

            if layer == 1:
                # calculates the time used for this move, prints it and sets the timer for timing the next move
                moveTime = time.perf_counter() - tmpTime
                if current_search_depth >= diepte:
                    print(
                        f"move: {str(board.lan(x))}; move value:   {str(moveValue)}"
                    )
                    print(f" time it took:             {moveTime:.4f}s")
                tmpTime = time.perf_counter()

                # deletes worse moves and adds newest best move to bestMoves
                bestMoves = []
                bestMoves.append(x)
    #input("")
    layer -= 1

    if stopSearch: return "stopped"

    # bepaal wat terug te geven
    if not layer == 0:
        return alpha

    # als het de eerste zet is
    else:
        endTime = time.perf_counter() - beginTime

        if len(bestMoves) > 0:
            print(f"{len(bestMoves)} possible moves:           {bestMoves}")
            print(f"negamax value:              {alpha}")
            print(f"negamax took:               {endTime:.4f}s")

        if len(bestMoves) != 0:
            bestMove = random.choice(bestMoves)
        else:
            bestMove = None

        searchValue = alpha
        return bestMove, alpha


def iterToBestMove(board, isWhite, timeDict = None):
    global transpositionTable
    global prinVariation
    global diepte
    global stopSearch
    global searchValue
    transpositionTable = {}
    prinVariation = []
    searchValue = boardeval.evaluate(board.fen(), isWhite, 0)

    beginTime = time.perf_counter()

    usableTime = 0
    diepte = 0

    if timeDict["timeLeft"] != None:
        #usableTime = 0.05*timeLeft/1000
        if board.ply()/2 < 60:
            skew = 10*((60-board.ply()/2)/60)
        else:
            skew = 0

        usedTime = timeDict["totalTime"]-timeDict["timeLeft"]
        usableTime =  (0.15*usedTime + 20) * ((timeDict["totalTime"]-usedTime)/timeDict["totalTime"]) - skew
        #print( usableTime, ": ", usedTime )
        
        
    else:
        # krijg diepte setting van settings.json
        try:
            with open("settings.json") as settingsFile:
                settings = json.load(settingsFile)
            diepte = int(settings["Diepte"])
        except:
            diepte = search_depth

    

    searchDepth = 0
    while searchDepth < diepte or time.perf_counter() - beginTime < usableTime:
    
        if searchValue == 1000000:

            endTime = time.perf_counter() - beginTime

            print(f"Iteration value:              {searchValue}")

            print(f"Iteration took:               {endTime:.1f}s")
            return prinVariation[0]

        searchDepth += 1
        print("new iteration: searching to depth ", searchDepth)
        
        checkValue = searchValue
        lowerWindow = -25
        upperWindow = 25
        while True:
            stopSearch = False

            #negamax(board, isWhite, 0,
            #                        searchValue + lowerWindow,
            #                        searchValue + upperWindow, searchDepth)
            searchThread = threading.Thread(target = negamax, args=(board, 
                                            isWhite, 0, searchValue + lowerWindow, 
                                            searchValue + upperWindow, searchDepth))
            
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
                upperWindow += round(0.5 * upperWindow *
                                    abs(1 - (upperWindow / 1000)) + 70)
                print(
                    f"fail-high; widening upper window to: {upperWindow} (max value of: {searchValue+upperWindow})"
                )

            elif searchValue == checkValue + lowerWindow:

                searchValue = checkValue
                lowerWindow += round(0.5 * lowerWindow *
                                    abs(1 - (lowerWindow / 1000)) - 70)
                print(
                    f"fail-low; widening lower window to: {lowerWindow} (min value of: {searchValue+lowerWindow})"
                )

            else:
                print("no fails          ", prinVariation)
                if searchDepth == diepte:
                    bestMove = prinVariation[0]
                
                break
    

        


    endTime = time.perf_counter() - beginTime

    print(f"Iteration value:              {searchValue}")

    print(f"Iteration took:               {endTime:.1f}s")

    

    
    bestMove = prinVariation[0]
    return bestMove


#returns best chosen move in chess.Move format
def getBestMove(
    board,
    isWhite,
):
    global transpositionTable
    global prinVariation
    global diepte
    transpositionTable = {}
    prinVariation = []

    # krijg diepte setting van settings.json
    try:
        with open("settings.json") as settingsFile:
            settings = json.load(settingsFile)
        diepte = int(settings["Diepte"])
    except:
        diepte = search_depth

    bestMove = negamax(board, isWhite, 0, -3000000, 3000000, diepte)[0]

    # randomly picks a move out of the best moves list

    

    return bestMove


def useEngine(startpos, moveList, isWhite, timeDict=None):
    global currentMoves
    global board

    if not moveList == currentMoves:
        currentMoves = moveList

        #resets board with given move list
        try:
            board = chess.Board(startpos)
        except:
            board = chess.Board()

        for x in moveList:
            if not x == "":
                move = chess.Move.from_uci(x)
                board.push(move)

        if timeDict["timeLeft"] != None:
            if timeDict["timeLeft"] <= 5: return randomMove(board)

        if len(moveList) < 20:
            with chess.polyglot.open_reader("Verborgen/Elo2400.bin") as reader:
                entryList = list(reader.find_all(board, minimum_weight=30))
                if len(entryList) > 0:
                    chosenMove = random.choices([entry.move for entry in entryList], 
                                                weights=[entry.weight for entry in entryList], k=1)[0]
                    return chosenMove.uci()

        #nextMove = getBestMove(board, isWhite)
        nextMove = iterToBestMove(board, isWhite, timeDict)
        print("negamax move: " + nextMove.uci())
        
        return nextMove.uci()

    else:
        print('no new moves')
        return ""
