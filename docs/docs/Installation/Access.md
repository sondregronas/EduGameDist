# Begrense tilgang

**Admin kan beskyttes med et passord (`ADMIN_PASSWORD`), men bør i tillegg begrenses av Nginx Proxy Manager (NPM). Ikke gjør admin-tjenesten offentlig tilgjengelig uten passord, en NPM Access List eller en tilsvarende regel.**

Admin-tjenesten er bare koblet til Docker-nettverket `edugamedist_proxy_access`; Compose publiserer ingen vertsport for den. Koble NPM-containeren til nettverket og send trafikken til `admin:8081`.

## Innlogging med passord

Sett miljøvariabelen `ADMIN_PASSWORD` for admin-tjenesten (i `docker-compose.yml` eller en `.env`-fil ved siden av den):

```
ADMIN_PASSWORD=et-langt-og-unikt-passord
```

Alle sider og API-kall i admin krever da innlogging via en egen innloggingsside, og det vises en **Logg ut**-knapp i menyen. Innloggingen varer i 7 dager, og etter fem feil passord blir innloggingen sperret i fem minutter. Er variabelen tom eller ikke satt, er innlogging slått av.

Bruk HTTPS i NPM slik at passordet ikke sendes ukryptert. Økter signeres med en nøkkel som lagres i `secret.key` i datavolumet; sett `SECRET_KEY` hvis du heller vil styre den selv. Skift passord eller nøkkel for å logge ut alle.

## Offentlig side

Spill og filer på den offentlige siden kan lastes ned av alle som når tjenesten. Bruk NPM eller brannmur for å begrense frontend dersom den bare skal brukes på skolens nettverk.

## Nginx Proxy Manager

Bruk [Nginx Proxy Manager](https://nginxproxymanager.com/) for proxy-adresser og tilgangsregler. Proxy admin til `http://admin:8081` og velg en Access List som passer organisasjonens behov. Test regelen både fra et nettverk med og uten tilgang.

Hvis du bruker IP-regler, er de vanlige private IPv4-områdene:

```
192.168.0.0/16
172.16.0.0/12
10.0.0.0/8
```

## Filtilgang

Spill kan lastes opp gjennom admin-appen eller legges i en administrert mappe. For direkte filtilgang kan du bruke nettverksdeling, ekstern disk eller en beskyttet SFTP-tjeneste. Ikke eksponer fillageret eller admin-porten direkte på internett.
