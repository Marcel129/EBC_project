# Wizualizacja
#### Autor: Marcel Skrok, 05.01.2025

### O programie
Wizualizacja stworzona na potrzeby projektu EBC "InPort". Program napisany zostal z wykorzystaniem frameworka  [dearPyGUI](https://dearpygui.readthedocs.io/en/latest/). Wszystkie pliki nalezy uruchamiac bedac w folderze /source. Na potrzeby dzialania programu przyjeto, ze wozki poruszaja sie po torze zgodnie z ruchem wskazowek zegara. Pozycja startowa wozkow nie jest okreslona - nalezy ja okreslic pierwsza ramka danych wysnych do GUI.

### Wymagania wstepne
Biblioteki:
- dearpygui
- zmq

Poza instalacja powyzszych bibliotek, do pliku programu ktory ma komunikowac sie z GUI nalezy zaimportowac pliki:
- config.py (zmienne konfiguracyjne programu)
- port_data_pb2.py (handler ramki danych przyjmowany przez GUI).

### Zmienne konfiguracyjne
Zmienne konfiguracyjne programu (np. ilosc wozkow na placu), potrzebne zarowno w czesci logicznej, jak i GUI, umieszczone sa w pliku config.py. Jezeli w trakcie rozwoju projektu pojawia sie inne zmienne tego typu, powinny byc one umieszczone w tym pliku. 

### Lokalizacje na placu
Miejsca dostępne dla wózków pokazane są w data_structure_definitions/port - localizations.png. Miejsca, gdzie wózki oczekują na wjazd na pole załadunku/rozładunku:
- każdy transit point ma swoje oddzielne miejsce
- storage yard ma jedno wspólne miejsce oczekujące dla obu punktów z/r
- miejsca przy statku również mają jedno wspólne miejsce oczekujące dla wszystkich punktów z/r

### Przyjmowane dane
Program przyjmuje dane za posrednictwem handlera wygenerowanego z pliku .proto dla pythona. Wszystkie zmienne zdefiniowane w pliku .proto musza byc uzupelnione dla poprawnego dzialania GUI. 

Kompilacja pliku .proto (jezeli bedzie potrzeba jego zmiany):
```
cd ~/EBC_project

protoc --proto_path=./data_structure_definitions --python_out=./source/ ./data_structure_definitions/port_data.proto 
```

### Uruchomienie 
Z zalozenia GUI oraz backend sa 2 osobnymi programami, dlatego nalezy uruchomic je w 2 osobnych terminalach. GUI nalezy uruchmic bedac w folderze /source. 

```
cd ~/EBC_project/source

python3 visu.py
```

Do testow GUI napisano plik simpleSender.py. Mozna go wykorzystac jako demo backendu. 

