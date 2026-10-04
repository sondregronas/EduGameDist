# Docker-installasjon

EduGameDist består av to Flask-apper som deler SQLite-database og fillager:

- **Frontend** viser spill og filer. Den har ingen endepunkter for å endre innhold.
- **Admin** lar deg redigere spill og laste opp filer. Den er ikke publisert på en vertsport; tilgang skal styres av Nginx Proxy Manager (NPM).

## Start

Kopier `docker-compose.yml` til en egen mappe og start tjenestene:

```bash
docker compose up -d
```

Frontend blir tilgjengelig på port 80. Docker Compose oppretter også nettverket `edugamedist_proxy_access`. Koble NPM-containeren til nettverket:

```bash
docker network connect edugamedist_proxy_access <NPM-container>
```

I NPM oppretter du en Proxy Host med:

- **Forward Hostname / IP:** `admin`
- **Forward Port:** `8081`
- **Scheme:** `http`
- **Access List:** velg en liste som bare gir tilgang til godkjente brukere eller nettverk

Ikke legg til en `ports:`-mapping for admin-tjenesten. Docker-nettverket og NPM skal være veien inn til administrasjonen. Begrens også den offentlige frontend-tjenesten med NPM eller brannmur hvis spillene ikke skal være tilgjengelige for alle.

For at store filer skal kunne lastes opp gjennom NPM, legg til følgende i NPM-vertens **Advanced**-felt:

```nginx
client_max_body_size 0;
proxy_request_buffering off;
proxy_read_timeout 3600s;
proxy_send_timeout 3600s;
```

Filer lastes opp i én strømmet forespørsel og lagres uendret. `client_max_body_size 0` fjerner proxyens størrelsesgrense, og `proxy_request_buffering off` hindrer at NPM mellomlagrer hele filen på disk først. Det finnes ingen samlet opplastingsgrense i appen; reell kapasitet bestemmes av ledig diskplass. SQLite-database og opplastede filer ligger i Docker-volumene `game_db` og `game_covers`.

## Eksisterende installasjoner

Den eksisterende `game_db`-volumstrukturen beholdes. Ved oppstart migreres spill, kategorier, butikklenker og plattformnedlastinger fra den gamle SQLite-tabellen automatisk til den nye strukturen. Behold sikkerhetskopi av begge volumene før oppgradering. NocoDB-tjenesten startes ikke lenger; slett ikke de gamle volumene før du har kontrollert at spill, omslag og nedlastinger er med.

## Konfigurasjon

Endre `TITLE` og `PUBLIC_URL` i `docker-compose.yml`. Spillfiler som var lagt inn manuelt kan fortsatt monteres fra `./games/<plattform>`. Konfigurasjonsfiler for CSS/favikon kan monteres fra `./cfg`.
