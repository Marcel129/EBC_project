# Event based control - project

## Informacje podstawowe
#### Temat projektu: Sterowanie rozładunkiem statków w porcie w Rotterdamie

#### Skład grupy:

- ✨Mateusz Strembicki✨ (_lider_)
- Marcel Skrok
- Radosław Tomzik
- Józef Sendor
- Grzegorz Pióro
- Mikołaj Sęk
- Sebastian Olejnik

## Założenia projektowe

W porcie znajdują się:
- statek dostarczający kontenery
- punkt tranzytowy, do którego kontenery te są przewożone ze statku
- plac magazynowy, na którym składowane są kontenery, jeżeli punkt tranzytowy jest zapełniony
- punkty załadunku/rozładunku (z/r)
- dźwigi 
- tor będący trasą dla wózków

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
