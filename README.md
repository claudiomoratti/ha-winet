# WiNet Local for Home Assistant

Integrazione custom per le **API locali WiNet Stove**, preparata per HACS.
Versione iniziale **0.1.0**, sperimentale: test software su Home Assistant **2026.10.1**;
collaudo dei comandi su stufa reale ancora da effettuare.

## Entità native

- **Climate**: temperatura aria, setpoint, modalità `heat` / `off`, accensione e spegnimento.
- **Number**: potenza da 1 a 5, oppure fino a 9 se il modello lo supporta.
- **Sensor**: stato, descrizione originale, temperatura aria, fumi, giri estrattore.
- **Binary sensor**: allarme secondo la mappa stati convenzionale WiNet.
- **Idro opzionale**: temperatura acqua e setpoint acqua 40–80 °C.

Un unico dispositivo, identificato dal MAC, raggruppa tutte le entità. Più moduli
possono essere aggiunti senza collisioni. Interfaccia e opzioni in italiano e inglese.
Nessuna dashboard o integrazione frontend aggiuntiva è necessaria.

## Installazione con HACS

Repository: **https://github.com/claudiomoratti/ha-winet**

1. HACS → menu → **Repository personalizzati**.
2. Aggiungere l'URL di questo repository, categoria **Integrazione**.
3. Scaricare **WiNet Local** e riavviare Home Assistant.
4. Impostazioni → Dispositivi e servizi → Aggiungi integrazione → **WiNet Local**.

La compatibilità con i repository personalizzati HACS non implica inclusione
nell'elenco predefinito HACS o approvazione ufficiale Home Assistant.

### Installazione manuale

Copiare la cartella `custom_components/winet` in `/config/custom_components/winet`
e riavviare Home Assistant. Non copiare `tests`, `docs` o file di sviluppo in `/config`.

## Configurazione

| Opzione | Default | Significato |
| --- | --- | --- |
| Host | richiesto | IP o hostname del WiNet, anche con porta; senza `http://` |
| Divisore aria | 2 | `2`: API in mezzi gradi; `1`: API in °C |
| Potenza massima | 5 | Selezionare 9 solo per modelli compatibili |
| Idro | no | Crea sensore e setpoint acqua |
| Sola lettura | sì | Blocca tutte le scritture, incluse le azioni HA |
| Intervallo | 15 s | Un'unica richiesta `/api/global`, configurabile 10–300 s |

Le opzioni sono modificabili dall'integrazione; vengono applicate con un reload.
**Riconfigura** cambia l'indirizzo verificando che il MAC corrisponda allo stesso dispositivo.
Non serve un token Home Assistant: il componente comunica direttamente con WiNet in LAN.

### Verificare la scala delle temperature

La documentazione pubblica mostra °C diretti, mentre il pacchetto HASS_WINET usa
mezzi gradi. Il default `2` riproduce quest'ultimo comportamento, ma non è un
riconoscimento automatico del firmware. Confrontare sempre con il display:
`setAir=38` corrisponde a 19 °C con divisore 2, a 38 °C con divisore 1.
La conversione è applicata sia in lettura sia in scrittura, solo all'aria.
Il setpoint aria esposto è 5–40 °C, passo 0,5 °C; la compatibilità del passo con
ogni modello va verificata durante il collaudo. Acqua: passo 1 °C, nessuna divisione.

## Comportamento

Il componente nasce in sola lettura. I controlli restano visibili; le azioni di
scrittura danno un errore esplicito finché questa opzione è attiva.

- Polling condiviso asincrono; nessuna lettura di rete dalle proprietà delle entità.
- Timeout, HTTP non validi e risposte malformate rendono il dispositivo indisponibile.
- Valori `null` rimangono sconosciuti, senza convertirli in zero. I fumi a 0 °C sono
  conservati così come riportati: non costituiscono una misura validata del sensore.
- I comandi sono serializzati, non vengono ritentati automaticamente e sono seguiti
  da una lettura. `result=true` significa accettazione, non completamento del ciclo.
- Un timeout di scrittura ha esito incerto: verificare lo stato prima di riprovare.
- Prima di accendere si rilegge lo stato: l'avvio è consentito soltanto da `0`;
  da `1` non viene inviato un altro comando. Pulizia, allarmi e stati ignoti bloccano l'avvio.
- Lo spegnimento resta richiedibile con connessione disponibile anche durante un allarme.
- Setup, reload e riavvio non inviano comandi e non ripristinano vecchi setpoint.
- Le modifiche dal display o dall'app WiNet vengono recepite al polling successivo.

### Mappa stati: compatibilità da verificare

La mappa deriva dal pacchetto HASS_WINET, non da una specifica completa del costruttore:

| Codice | Sensore stato | Modalità climate | Allarme |
| --- | --- | --- | --- |
| 0 | Spenta | off | no |
| 1 | Accesa | heat | no |
| 2 | Pulizia finale | off | no |
| 3 | Allarme | sconosciuta | sì |
| 4 | Non gestita | sconosciuta | sconosciuto |
| altro | Non riconosciuto | sconosciuta | sconosciuto |

La modalità `off` durante pulizia non significa che ventole e combustione siano
immediatamente ferme. Il sensore di stato mantiene visibile la fase reale.
`hvac_action` è deliberatamente assente: con i dati disponibili non si distingue
in modo universale accensione, combustione, modulazione e standby. Non si deducono
queste fasi da temperature, RPM o parole nella descrizione.

L'integrazione lascia la regolazione alla centralina della stufa. Non implementa
un termostato esterno con cicli accendi/spegni o una programmazione interna.
Le automazioni HA possono chiamare i servizi standard `climate` e `number`, dopo
il collaudo e considerando i tempi previsti dal produttore.

## Ventole e Blower Cube

Nel repository di riferimento le API `/api/fan/...` appartengono al **WiNet Blower Cube**,
configurato con un proprio host. Non sono una prova che il modulo **WiNET Gen.Stove**
esponga il controllo delle ventole della stufa. Questa versione supporta solo Stove:
non crea entità `fan`, non prova endpoint di scrittura e non scambia i giri
estrattore fumi per una velocità regolabile. Vedere [analisi del protocollo](docs/protocol.md).

## Primo collaudo e migrazione

Seguire [la procedura di test](docs/testing.md). La prima verifica avviene in sola
lettura; prima dei test di comando individuare e sospendere le automazioni del
vecchio pacchetto che possono comandare la stufa. Il componente non rimuove il
pacchetto precedente né migra automaticamente gli entity ID.

## Diagnostica e privacy

`/api/id` può contenere la password Wi-Fi dell'access point: il client conserva
soltanto modello e MAC. La diagnostica esporta opzioni e valori numerici noti,
escludendo host, MAC, SSID, password e descrizioni libere. Nessun token, snapshot
personale o dato della rete domestica è incluso in questo repository.

## Sviluppo

Python 3.14, Home Assistant 2026.10.1:

```sh
python -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
ruff check .
ruff format --check .
pytest --cov=custom_components.winet
```

I test usano le fixture Home Assistant e HTTP simulato, con socket esterni disabilitati.
La CI comprende test, Ruff, hassfest e validazione HACS.
Vedere [risultati della validazione locale](docs/validation.md); i workflow remoti
sono verifiche aggiuntive eseguite sul repository pubblicato.

## Riferimenti

Implementazione originale, senza riuso del codice o delle immagini del pacchetto:

- [API locali StufaSmart](https://stufasmart.it/documentazione-tecnica/api-in-locale/)
- [HASS_WINET di morenonew2](https://github.com/morenonew2/HASS_WINET), riferimento di compatibilità
- [Entità Climate HA](https://developers.home-assistant.io/docs/core/entity/climate/)
- [Requisiti integrazioni HACS](https://www.hacs.xyz/docs/publish/integration/)

Progetto indipendente, non affiliato a WiNet, StufaSmart o Home Assistant.
Licenza MIT.
