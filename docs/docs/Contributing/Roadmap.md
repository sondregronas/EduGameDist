# Roadmap
Dette er en levende oversikt over hva som er gjort og hva som kan komme. Forslag mottas gjerne som issue eller pull request.

## Ferdig
- Python/Flask/SQLAlchemy erstatter Node/Pug/NocoDB. Offentlig (skrivebeskyttet) og admin kjører som to separate apper mot samme SQLite-database.
- Nytt, moderne og mobilvennlig design med innebygde ikoner (ingen frontend-rammeverk eller byggesteg).
- Redigering direkte på spillsiden, med opprettelse av spill via skjema.
- Flere filer per plattform, opplasting uten størrelsesgrense og passordbeskyttet admin.
- Henting av metadata fra Steam (beskrivelse, omslag, utvikler og nettsted) og automatisk søk etter GOG-, itch.io- og Humble Bundle-lenker.
- Omslagsbilder lagres lokalt, og eldre NocoDB-data (inkludert omslag) migreres automatisk.
- Lærernotat med lenker og enkel HTML.

## Mulige forbedringer
- **Brukere og roller:** flere administratorer, og eventuelt tilgang til enkelte spill for enkelte brukere. Admin er i dag beskyttet av ett felles passord og/eller proxyen foran.
- **Gjenopptakbare opplastinger:** store filer sendes i én forespørsel, så en brutt opplasting må startes på nytt.
- **Flere metadatakilder:** for eksempel [TheGamesDB](https://thegamesdb.net/) for spill som ikke finnes på Steam.
- **Bedre støtte for store spill:** for eksempel sjekksummer og nedlastingsvalg per fil.
