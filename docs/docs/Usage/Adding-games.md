# Legge til spill

Åpne administrasjonsappen via adressen som er konfigurert i Nginx Proxy Manager. Velg **Legg til spill** på forsiden, skriv inn Steam-lenke, app-ID eller spillnavn og trykk **Hent fra Steam**, og velg **Opprett og legg til filer**. Spillet åpnes i redigeringsmodus og vises umiddelbart på den offentlige nettsiden.

## Hente informasjon fra Steam

Tittel, kort beskrivelse, omslagsbilde, utvikler og Steam-lenke fylles inn når Steam har disse opplysningene. Omslagsbildet lastes ned og lagres på serveren. Appen leter også etter spillet hos GOG, itch.io og Humble Bundle og legger til lenker ved eksakt treff (Humble er best-effort). Kontroller og rediger feltene før du lagrer.

## Spillinformasjon

- **Tittel** og **beskrivelse** vises på oversikten og spillsiden.
- **Lærernotat** vises som ren tekst på spillsiden.
- **Omslagsbilde** kan hentes fra Steam, oppgis som en URL eller lastes opp under plattformen «Omslagsbilde».
- **Antall spillere**, **spilletid**, **utvikler** og **utviklerens nettsted** er valgfrie.
- **Kategorier** legges til med **+ Ny kategori** og fjernes med minus-knappen på hver kategori.
- **Butikklenker** legges til med **+ Ny lenke**; butikken gjenkjennes automatisk fra adressen.
- **Lenke til nettleserspill** brukes når spillet kan startes direkte i nettleseren.

Kategorier og butikklenker lagres som egne, ordnede poster knyttet til spillet, ikke som faste `Category1`-/`Store1`-kolonner.

## Laste opp filer

Trykk **Rediger** på spillsiden, og slipp filer i området for riktig plattform (eller trykk i området for å velge filer). Gjenta for å legge til flere filer på samme plattform eller filer til en annen plattform. Eksisterende filer kan fjernes i administrasjonen.

Hver fil sendes i én strømmet forespørsel og lagres uendret. Appen har ingen størrelsesgrense, så filer på over 20 GB kan lastes opp, men opplastingen kan ikke gjenopptas hvis den brytes, og siden må stå åpen til den er ferdig. Proxyen må tillate store forespørsler (`client_max_body_size 0`). Se [Docker-installasjon](../Installation/docker.md) for NPM-konfigurasjon.

## Lisenser og distribusjon

Sørg for at du har rett til å distribuere spillene. Se [anskaffelse av spill](Acquiring-games.md) og prosjektets [vilkår](Terms-and-Conditions.md).
