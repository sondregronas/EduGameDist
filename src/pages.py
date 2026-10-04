"""Default content for the pages admins can rewrite under Settings (installation guide and terms).

The content uses the same small HTML subset as the editor: every <h2> starts a card (optionally with
an icon, e.g. <h2 data-icon="windows">), <blockquote> becomes a highlighted note and anything after
<hr> is shown as a footnote.
"""

PAGES = {
    "install": {
        "route": "/install",
        "title": "Installasjon",
        "icon": "book",
        "default": """<h1>Slik får du spillene på maskinen din</h1>
<p>Velg enheten din, så får du en steg-for-steg-guide. Er det flere filer for samme plattform, bruker du den læreren eller administratoren har anbefalt.</p>
<blockquote>Sørg for nok ledig plass og la nedlastingen bli ferdig før du åpner filen.</blockquote>

<h2 data-icon="windows">Windows</h2>
<p>Mange spill kommer som et ZIP-arkiv. Innholdet må pakkes ut før du kan starte installasjonsprogrammet eller spillet.</p>
<ol>
  <li>Last ned Windows-filen og vent til nedlastingen er ferdig.</li>
  <li>Høyreklikk ZIP-filen og velg <strong>Pakk ut alle…</strong>. Vises ikke valget, prøv <strong>Vis flere alternativer</strong>.</li>
  <li>Velg hvor filene skal pakkes ut, og trykk <strong>Pakk ut</strong>.</li>
  <li>Åpne den utpakkede mappen og finn installasjonsprogrammet eller spillet. Følg instruksjonene som følger med.</li>
</ol>

<h2 data-icon="mac">Mac</h2>
<ol>
  <li>Last ned Mac-filen. Er den en ZIP-fil, dobbeltklikker du på den for å pakke den ut.</li>
  <li>Er den en DMG-fil, åpner du den og drar appen til <strong>Programmer</strong>.</li>
  <li>Åpne appen. Blokkerer macOS den fordi utvikleren ikke er bekreftet, åpner du <strong>Systeminnstillinger → Personvern og sikkerhet</strong> og trykker <strong>Åpne likevel</strong>. Knappen vises først etter at du har forsøkt å åpne appen. Bekreft med passord eller Touch ID.</li>
</ol>
<p><small>Åpne bare apper som skolen har godkjent.</small></p>

<hr>
<p>Fungerer ikke nedlastingen eller installasjonen? Kontakt den som administrerer samlingen.</p>
""",
    },
    "terms": {
        "route": "/vilkar",
        "title": "Vilkår og betingelser",
        "icon": "shield",
        "default": """<h1>Vilkår for spill på denne siden</h1>
<p>Vilkårene gjelder alt nedlastbart innhold som er tilgjengelig her.</p>

<h2 data-icon="shield">Spillene er kun til privat bruk</h2>
<p>Innholdet på siden er reservert til privat bruk. Elever og lærere i samme klasserom, hvor spillene er tilgjengelige, defineres som privat bruk. Det er ikke tillatt å laste ned spill for bruk i andre sammenhenger eller distribuere dem videre. Hvis du ønsker å bruke spillene i andre sammenhenger, må du kjøpe dem selv.</p>

<h2 data-icon="info">Ansvar</h2>
<p>Vi forventer at du bruker siden på en forsvarlig måte. Målet er å tilby spill som supplement til undervisning og læring. Tilgang kan trekkes tilbake dersom siden misbrukes eller bruken går ut over læringen. Misbruk omfatter blant annet å laste ned spill for bruk i andre sammenhenger eller distribuere dem videre.</p>

<h2 data-icon="clock">Hvor lenge kan jeg bruke spillene?</h2>
<p>Spillene kan brukes så lenge du har tilgang til siden. Hvis du ønsker å bruke dem senere, må du kjøpe dem selv.</p>

<h2 data-icon="book">Bruk av spill i skolen</h2>
<p>Spillene på siden tilbys som støtte til skoleundervisning. Følg skolens regler for bruk av programvare og digitale læremidler.</p>

<h2 data-icon="gamepad">Hvor kommer spillene fra?</h2>
<p>Spillene kan komme fra ulike kilder og ha ulike distribusjonsvilkår. Sjekk vilkårene for hvert enkelt spill og sørg for at du har rett til å bruke det. Eksempler på spillbutikker er <a href="https://www.spillpedagogbanken.no/?faq=hva-er-steam-epic-itch-io-gog-og-humblebundle">GOG, Humble Bundle, itch.io og lignende tjenester</a>.</p>
""",
    },
}
