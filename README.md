# Event based control - project

## Informacje podstawowe
Dokumentacja w overleaf: https://www.overleaf.com/project/672277fcee9f988699b13d9e
#### Temat projektu: Sterowanie rozładunkiem statków w porcie w Rotterdamie

#### Skład grupy:

- ✨Mateusz Strembicki✨ (_lider_)
- Marcel Skrok
- Radosław Tomzik
- Józef Sendor
- Grzegorz Pióro
- Mikołaj Sęk
- Sebastian Olejnik

#### Zarządzanie projektem:
- Prace całej grupy koordynuje lider
- Grupa podzielona jest na 2 podgrupy; jedna odpowiada za wizualizację systemu (GUI), druga za część logiczną kodu
- Harmonogram pracy określa wykres Gantta stworzony przez lidera grupy po konsultacji z zespołem
- Dokumentacja projektu prowadzona jest w serwisie Overleaf z wykorzystanie składu tekstu LaTeX
- Program realizujący zadanie projektowe prowadzony jest w serwisie Github z wykorzystaniem systemu kontroli wersji git
- Spotkania grupy odbywają się zdalnie co 2 tygodnie w terminie ustalonym podczas spotkania wstępnego
- Poszczególne części programu będą komunikować się za pośrednictwem protokołu zeroMQ i globalnie zdefiniowanych struktur danych 

## Założenia projektowe

W porcie znajdują się:
- statek dostarczający kontenery
- punkt tranzytowy, do którego kontenery te są przewożone ze statku
- plac magazynowy, na którym składowane są kontenery, jeżeli punkt tranzytowy jest zapełniony
- punkty załadunku/rozładunku (z/r)
- dźwigi 
- tor będący trasą dla wózków

![image](https://github.com/user-attachments/assets/4f020bac-e328-40bf-ab25-4ea0c737f486)


Założenia:
- wózki przewożą kontenery ze statku do punktu tranzytowego  
- jeżeli punkt tranzytowy jest zapełniony kontenery odstawiane są na plac magazynowy
- jeżeli punkt tranzytowy i plac magazynowy są zapełnione rozładunek zostaje wstrzymany
- wózki poruszają się po torze będącym zamkniętą pętlą
- statek dostarcza N kontenerów. Po jego opróżnieniu odpływa, nadpłynięcie kolejnego następuje w losowym czasie ts
- w punkcie tranzytowym znajdują się 4 sloty, każdy o pojemności S
- z każdego slotu odbierane jest S kontenerów w losowych odstępach czasu to
- w ruchu znajduje się n wózków
- aby wózek mógł zostać załadowany musi on wjechać na punkt załadunkowy (analogicznie z rozładowaniem). Wjazd na miejsce zajmuje tp
- załadunek/rozładunek kontenera na wózek zajmuje tz
- załadunek/rozładunek może nastąpić jeżeli dostępny jest wolny dźwig
- liczba dźwigów jest zawsze mniejsza niż liczba punktów z/r
- każdy kontener posiada unikalne ID mówiące w którym slocie w punktcie tranzytowym ma zostać umieszczony
- jeżeli punkt z/r przy slocie docelowym jest zajęty, wózek czeka, co skutkuje zablokowaniem trasy (albo jedzie na plac magazynowy, do przemyślenia)

Opcjonalne rozszerzenia, jeżeli Roszkowska powie że za mało:
- jeż na trasie: dodajemy losowe zdarzenie w postaci zablokowanej trasy. W takim przypadku pojazd musi się przed nim zatrzymać i poczekać, aż zdarzenie zniknie
- przebita opona: dodajemy punkt serwisowy dla wózków. Może zdarzyć się, że wózek będzie musiał zjechać do warsztatu, co wyklucza go na pewien czas z pracy
- nielegalni imigranci w kontenerze: kontener bez ładunku zostaje umieszczony na stałe na placu odstawczym, zmniejszając jego pojemność
- nietrzeźwy pracownik na placu: pracownik zasnął na punkcie z/r, przez co zostaje on zablokowany na losowy czas ta
