import os
import json
import threading
from time import sleep
from requests import post, get
from keep_alive import keep_alive
from datetime import datetime, timedelta

import negamax
from UI import openTkWindow, updateSettingsFromVar, updateSettingsListFromVar, resetSettingsList

authToken  = os.environ["Token"]
authHeader = {"Authorization" : "Bearer " + authToken}

keep_alive()
openTkWindow()

def liPost(link, data = None): #driewerf gebruikt
    return post(url = "https://lichess.org/api/" + link, headers = authHeader, data = data).json()


#gets json objects from stream 
def liGetStream(link, standaardUrl = True, data = None):
    
    #opent http stream
    if standaardUrl:
        response = get(url = "https://lichess.org/api/" + link, headers = authHeader, stream = True, data = data)
    else:
        response = get(link, headers = authHeader, stream = True, data = data)

    #behandelt 429 error
    if response.status_code == 429: 
        print("\033[31mAPI overloaded: 429; waiting for 10 seconds\033[0m")
        sleep(10)
        #probeert de functie nog een keer
        liGetStream(link)
    
    
    for line in response.iter_lines():
        
        if line:
            # wacht voor de volgende stream item en geeft het terug
            yield json.loads(line)


def playBestMove(useClock, startPositie, zettenLijst, isWhite, spelStatus, totalTime, ID):
    print("\n\33[91mEen zet wordt bedacht...")
                    
    timeLeft = None
    if useClock == True:
        ctime = "wtime" if isWhite else "btime" #wiens tijd
        timeLeft = spelStatus[ctime]/1000

    with open("log", "a") as file:
        file.write("Nagedacht om:" +  (datetime.now() + timedelta(hours=1)).strftime("%d/%m/%Y %H:%M:%S,%f") + " | ")

    # zet de bedachte zet
    zet = negamax.useEngine(startPositie, zettenLijst, isWhite, timeDict={"totalTime":totalTime,"timeLeft":timeLeft})

    with open("log", "a") as file:
        file.write("Gespeeld op:" + (datetime.now() + timedelta(hours=1)).strftime("%d/%m/%Y %H:%M:%S,%f") + "\n")
    
    print(liPost(f"bot/game/{ID}/move/{zet}"), "\33[0m")

def playGame(spelId):
    # opent de game stream voor deze partij
    gameEvents = liGetStream(f"bot/game/stream/{spelId}")
    print("Game stream geopent")

    # zet game variabelen klaar (eerste game event is altijd een gameFull met alle info)
    gameStatus = next(gameEvents)

    print("\033[94m\nStatus:", gameStatus["state"]["status"] + ";", "id:", gameStatus["id"] + ";", "link:", "lichess.org/" +  gameStatus["id"])
    updateSettingsListFromVar("Link", "lichess.org/" +  gameStatus["id"], adding=True)
    print("Witte speler:", gameStatus["white"]["title"], gameStatus["white"]["name"])
    print("Zwarte speler:", gameStatus["black"]["title"], gameStatus["black"]["name"], "\n")
    #print("Zetten:", gameStatus["state"]["moves"], "\n")

    # bereid partij variabelen voor
    status = gameStatus["state"]["status"]
    startPositie = (gameStatus["initialFen"], gameStatus["variant"]["key"])
    zettenLijst = gameStatus["state"]["moves"].split(" ")
    if zettenLijst[0] == "": zettenLijst.remove("")

    eersteLoop = True

    # gaat door met game loop als de partij nog niet is afgelopen
    while status == "started":
        
        if not eersteLoop:
            # wacht voor een nieuwe game state
            
            gameStatus = next(gameEvents)
            print(f"\nGame event aangekomen: {gameStatus['type']}")
            
        else:
            eersteLoop = False

        # mogelijkheid 1: een volle info over de partij
        if gameStatus["type"] == "gameFull":
            print(gameStatus, "\033[0m")

            # update de partij variabelen
            status = gameStatus["state"]["status"]
            isWhite = gameStatus["white"]["name"] == "PWS-bot"
            totalTime = None
            if gameStatus["clock"] != None:    
                
                useClock = True
                totalTime = gameStatus["clock"]["initial"]/1000
            else:
                useClock = False
             

            # check of de partij nog bezig is
            if gameStatus["state"]["status"] != "started":
                print("Game over")
                break


            # bereid de nieuwe en oude zettenlijsten voor op vergelijking
            nieuweZetten = gameStatus["state"]["moves"].split(" ")
            if nieuweZetten[0] == "": nieuweZetten.remove("")

            # checkt of de zettenlijst veranderd is
            if zettenLijst != nieuweZetten: 
                
                # update de zetten lijst
                zettenLijst = nieuweZetten
                

            # kijkt of er een zet gedaan moet worden
            if isWhite == (len(zettenLijst) % 2 == 0):
                playBestMove(useClock, startPositie, zettenLijst, isWhite, gameStatus["state"], totalTime, spelId)
                
        # mogelijkheid 2: een verandering in de partij
        if gameStatus["type"] == "gameState":
            print(gameStatus)

            # update de partij variabelen
            status = gameStatus["status"]
            
            
            # bereid de nieuwe en oude zettenlijsten voor op vergelijking
            nieuweZetten = gameStatus["moves"].split(" ")
            if nieuweZetten[0] == "": nieuweZetten.remove("")
            
            # check of de partij nog bezig is
            if gameStatus["status"] != "started":
                print("Game over")

                updateSettingsListFromVar("Link", "lichess.org/" +  spelId, adding=False)

                break

            # checkt of de zettenlijst veranderd is
            if zettenLijst != nieuweZetten: 
                
                # update de zetten lijst
                zettenLijst = nieuweZetten
                
            # kijkt of er een zet gedaan moet worden
            if isWhite == (len(zettenLijst) % 2 == 0):
                playBestMove(useClock, startPositie, zettenLijst, isWhite, gameStatus, totalTime, spelId)

        # mogelijkheid 3: een chat bericht
        if gameStatus["type"] == "chatLine":
            bericht = gameStatus["text"]
            print("De tegenstander zegt: " + bericht)
        
            with open("settings.json") as settingsFile:
                settings = json.load(settingsFile)
            if settings["DiepteVariabelVanuitChat"] == True:
                if bericht.isnumeric():
                    bericht = int(bericht)
                    if bericht > 0 and bericht <7:
                        updateSettingsFromVar("Diepte", bericht)
                    

# opent de algemene events stream
events = liGetStream("stream/event")
print("Event stream geopent")

threads = []
resetSettingsList("Link")

while True:
    
    # wacht op een nieuw event
    event = next(events)
    print(f"\nEvent aangekomen: {event['type']}")
    
    # mogelijkheid 1: een uitdaging
    if event["type"] == "challenge":
        print(f"Challenger name: {event['challenge']['challenger']['name']}")
        print(f"Challenger rating: {event['challenge']['challenger']['rating']}")


        # kijkt of de geaccepteerde variant is gekozen
        if event["challenge"]["variant"]["key"] in ("standard", "fromPosition", "horde", "chess960"):

            # accepteert de uitdaging
            challengeId = event["challenge"]["id"]
            liPost(f"challenge/{challengeId}/accept")
            print("Challenge geaccepteerd")
        
        else:
            print(f"Uitdaging geweigerd vanwege verkeerde schaakvariant: {event['challenge']['variant']['key']}")

    # mogelijkheid 2: een partij
    elif event["type"] == "gameStart":
        gameId = event["game"]["id"]


        try:
            threads.append(threading.Thread(target = playGame, args = (gameId,)))
            # 
            # threads.append(Process(target = playGame, args = (gameId,)))
            threads[len(threads)-1].start()
        except:
            print("ERROR: unable to open thread")
            
            print("opening game on main thread")

            playGame(gameId)
