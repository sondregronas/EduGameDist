# Administrasjon

Administrasjonsappen er en egen Flask-tjeneste på port 8081 inne i Docker-nettverket `edugamedist_proxy_access`. Den publiserer ikke porten direkte på vertsmaskinen, og kan beskyttes med et passord i `ADMIN_PASSWORD` (se [Begrense tilgang](Access.md)). **Nginx Proxy Manager bør i tillegg bestemme hvem som får tilgang.**

Koble NPM-containeren til Docker-nettverket, og opprett en proxy host til `http://admin:8081`. Velg en NPM Access List med ønsket tilgangsregel. Ikke proxy admin uten en slik tilgangsregel, og ikke legg til en offentlig `ports:`-mapping.

Åpne admin-adressen for å legge til eller redigere spill. Endringer i metadata blir synlige på den offentlige nettsiden når du lagrer. Filer kan lastes opp flere ganger per spill og plattform. Se [Docker-installasjon](docker.md) for innstillinger for store opplastinger.
