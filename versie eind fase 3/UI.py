import json
from time import sleep
from PIL import ImageTk, Image
import tkinter as tk
import tkinter.ttk as ttk
from threading import Thread

settings = {}

diepteOpties = ("*", 1,2,3,4,5,6)

DiepteVanuitChat = False
OpeningboekAan = True

def place(soort, tk_argument_list, grid_argument_list, var = "widget"):
    
    order1 = f"{var} = tk.{soort}(root, " + ', '.join(tk_argument_list) + ")"
    order2 = f"{var}.grid(" + ', '.join(grid_argument_list) + ")"

    exec("global " + var + ";" + order1)
    exec("global " + var + ";" + order2)

def updateVarsFromJson():
    global settings, link, diepte, DiepteVanuitChat

    with open("settings.json") as settingsFile:
        settings = json.load(settingsFile)

    try:
        link.set(" ".join(settings["Link"]).replace(" ", "\n"))
        diepte.set(settings["Diepte"])
        DiepteVanuitChat = settings["DiepteVariabelVanuitChat"]

    except Exception as e:
        print(e)
    
def updateSettingsFromVar(key, var):
    settings[key] = var
    settingsJson = json.dumps(settings)
    with open("settings.json","w") as settingsFile:
        settingsFile.write(settingsJson)

    #DIT HOORT HIER NIET MAAR IK VOND GEEN BETERE PLEK ERVOOR.
    if DiepteVanuitChat: diepteSchakelaar.config(text = "Zet diepe vanuit chat uit")
    else:                diepteSchakelaar.config(text = "Zet diepe vanuit chat aan")

    if OpeningboekAan: openingSchakelaar.config(text = "Zet openingboek uit")
    else:                openingSchakelaar.config(text = "Zet openingboek aan")

def updateSettingsListFromVar(key, var, adding):
    assert isinstance(settings[key],list)

    if adding:
        settings[key].append(var)
        settingsJson = json.dumps(settings)
        with open("settings.json","w") as settingsFile:
            settingsFile.write(settingsJson)
    else:
        try: settings[key].remove(var)
        except Exception as e: 
            print(e)
            print("link not fount in setting:", var)
        settingsJson = json.dumps(settings)
        with open("settings.json","w") as settingsFile:
            settingsFile.write(settingsJson)

def resetSettingsList(key):
    global settings
    with open("settings.json") as settingsFile:
        settings = json.load(settingsFile)
    
    settings[key] = []
    settingsJson = json.dumps(settings)
    with open("settings.json","w") as settingsFile:
        settingsFile.write(settingsJson)


def getUIVar(varName):
    var = root.getvar(name=varName)
    return var

"_________________________________"

def openTkWindow():
    windowThread = Thread(target = window)
    windowThread.start()

def tickUpdate():
    while True:
        sleep(1)
        updateVarsFromJson()

def window():
    global opening, root, diepte, link
    root = tk.Tk()

    Thread(target = tickUpdate).start()

    if "Diepte" in settings: diepte = tk.IntVar(root, settings["Diepte"], name ="diepte")
    else: diepte = None
    diepteSetting = ttk.Combobox(   root, textvariable=diepte, values=diepteOpties,
                                    width="1", state="readonly")

    #if "Openzet" in settings: openzet = tk.IntVar(root, settings["Openzet"], name ="Openzet")
    #else: Openzet = None

    link = tk.StringVar()
    link.set(" ".join(settings["Link"]).replace(" ", "\n"))

    opening = tk.StringVar()
    opening.set(settings["Openzet"])

    place("Label", ("text = 'Diepte:'",), ("column = 0", "row = 0", "padx = 20", "pady = 20"))
    place("Label", ("text = 'Openingszet:'",), ("column = 0", "row = 2"))
    place("Entry", ("width = 3", "textvariable = opening"), ("column = 14", "row = 2"), var = "open_zet")
    place("Button", ("bg = 'lightblue'", "command = lambda: schakelaar('DiepteVanuitChat', 'DiepteVariabelVanuitChat')"), ("column = 8", "row = 9", "pady = 5"), var = "diepteSchakelaar")
    place("Button", ("bg = 'lightblue'", "command = lambda: schakelaar('OpeningboekAan', 'OpeningboekVariabel')"), ("column = 8", "row = 10", "pady = 5"), var = "openingSchakelaar")
    place("Label", ("text = 'Huidige partijen:'", "bg = 'lightgreen'"), ("column = 8", "row = 11"))
    place("Label", ("textvariable = link", "bg = 'lightgreen'",), ("column = 8", "row = 12",))  

    if DiepteVanuitChat: diepteSchakelaar.config(text = "Zet diepe vanuit chat uit")
    else:                diepteSchakelaar.config(text = "Zet diepe vanuit chat aan")

    if OpeningboekAan: openingSchakelaar.config(text = "Zet openingboek uit")
    else:                openingSchakelaar.config(text = "Zet openingboek aan")


    diepteSetting.grid(column = 14, row = 0) #padx = 5, pady = 5)

    diepteSetting.bind( "<<ComboboxSelected>>", 
            lambda var : updateSettingsFromVar("Diepte", diepteSetting.get()))

    open_zet.bind("<Return>", 
            lambda var : updateSettingsFromVar("Openzet", open_zet.get()))

    root.title('Schaakbot')
    root.geometry("400x300+20+10") #was 700x400+20+10"
    root.mainloop()
    
def schakelaar(var, naam):
    if isinstance(eval(var), bool): 
        exec(f"global {var}; {var} = not(eval('{var}'))")
        updateSettingsFromVar(naam, eval(var))
